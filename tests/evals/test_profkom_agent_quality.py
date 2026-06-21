"""
Тесты качества профсоюзного консультанта с использованием DeepEval.

Оценивает:
- Релевантность ответа вопросу
- Качество рекомендаций по профсоюзной тематике
- Полноту и структуру ответа
- Отсутствие галлюцинаций
- Дружелюбность и эмпатию
- Токсичность

Все метрики выводятся в шкале 0-100%.
Основной порог прохождения: 65%.

Запуск:
    # С автоматическим запуском сервиса
    pytest tests/evals/test_profkom_agent_quality.py -v

    # С уже запущенным сервисом
    SKIP_AGENT_START=true pytest tests/evals/test_profkom_agent_quality.py -v

    # С указанием golden dataset
    GOLDEN_DATASET_PATH=tests/evals/fixtures/scenarios.json pytest tests/evals/

    # В режиме аннотации
    ANNOTATE_MODE=true pytest tests/evals/ -v
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from deepeval.test_case import LLMTestCase

from .eval_utils import (
    AgentRequest,
    AgentConnectionError,
    call_agent_chat,
    load_golden_dataset,
    create_test_case_from_scenario,
    auto_annotate_scenario,
    get_judge_model,
    get_metric,
)


# ============================================================================
# Конфигурация окружения
# ============================================================================

AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8080")
GOLDEN_DATASET_PATH = os.getenv("GOLDEN_DATASET_PATH", "tests/evals/fixtures/scenarios.json")
ANNOTATE_MODE = os.getenv("ANNOTATE_MODE", "false").lower() == "true"
MAX_CONCURRENT_METRICS = int(os.getenv("MAX_CONCURRENT_METRICS", "5"))

METRIC_NAME_RU = {
    "answer_relevancy": "Релевантность ответа",
    "recommendation_quality": "Качество рекомендаций",
    "response_structure": "Структура ответа",
    "response_completeness": "Полнота ответа",
    "hallucination_rate": "Уровень галлюцинаций",
    "toxicity_rate": "Уровень недружелюбности",
    "empathy_friendly": "Дружелюбность и эмпатия",
}

# Метрики, где меньше = лучше (score должен быть <= threshold)
LOWER_IS_BETTER_METRICS = {"hallucination_rate", "toxicity_rate"}


def get_metric_display_name(metric_name: str) -> str:
    return METRIC_NAME_RU.get(metric_name, metric_name)


def is_metric_passed(metric_name: str, score: float, threshold: float) -> bool:
    """Проверяет прохождение метрики с учётом направления шкалы."""
    if metric_name in LOWER_IS_BETTER_METRICS:
        return score <= threshold
    return score >= threshold


# ============================================================================
# Pytest hooks
# ============================================================================

def pytest_configure(config):
    """Настройка перед запуском тестов."""
    print("\n" + "=" * 60)
    print("DeepEval Quality Tests for Профсоюзный консультант")
    print("=" * 60)
    print(f"Agent URL: {AGENT_BASE_URL}")
    print(f"Dataset: {GOLDEN_DATASET_PATH}")
    print(f"Annotate mode: {ANNOTATE_MODE}")
    print(f"Max concurrent metrics: {MAX_CONCURRENT_METRICS}")
    print("=" * 60 + "\n")


# ============================================================================
# Вспомогательные функции
# ============================================================================

async def _evaluate_single_metric(metric_name: str, metric, test_case, semaphore: asyncio.Semaphore):
    """
    Оценивает одну метрику асинхронно с ограничением конкурентности.

    Args:
        metric_name: Имя метрики
        metric: Объект метрики
        test_case: LLMTestCase для оценки
        semaphore: Семафор для ограничения конкурентности

    Returns:
        Словарь с результатами оценки
    """
    async with semaphore:
        try:
            await metric.a_measure(test_case)
            return {
                "metric_name": metric_name,
                "score": metric.score if metric.score is not None else 0.0,
                "reason": metric.reason,
                "threshold": metric.threshold if hasattr(metric, "threshold") else 0.65,
                "error": None,
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "metric_name": metric_name,
                "score": 0.0,
                "reason": str(e),
                "threshold": 0.65,
                "error": e,
            }


def convert_score(score: float) -> tuple[float, str]:
    """
    Конвертирует сырой score (0-1) в проценты.

    Returns:
        (display_score, unit_label)
    """
    return score * 100, "%"


def convert_threshold(threshold: float) -> tuple[float, str]:
    """
    Конвертирует threshold в проценты.

    Returns:
        (display_threshold, unit_label)
    """
    return threshold * 100, "%"


# ============================================================================
# Базовые тесты работоспособности
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.eval_quality
async def test_agent_responds_without_errors(agent_service):
    """
    Проверка, что агент отвечает без ошибок.

    Дымовой тест для проверки работоспособности /chat endpoint.
    """
    request = AgentRequest(
        message="Привет! Как вступить в профсоюз?",
        organisation="ППО Невинномысский Азот",
    )

    try:
        response = await call_agent_chat(request)
    except AgentConnectionError as e:
        pytest.fail(f"Не удалось подключиться к агенту: {e}")

    assert response.response, "Агент вернул пустой текст ответа"
    assert len(response.response) > 10, "Ответ слишком короткий"


@pytest.mark.asyncio
@pytest.mark.eval_quality
async def test_agent_handles_offtopic(agent_service):
    """
    Проверка, что агент корректно обрабатывает оффтопик-запросы.
    """
    request = AgentRequest(
        message="Расскажи рецепт борща",
        organisation="ППО Невинномысский Азот",
    )

    response = await call_agent_chat(request)
    assert response.response, "Ответ пустой"

    metric = get_metric("hallucination_rate")
    test_case = LLMTestCase(
        input=request.message,
        actual_output=response.response,
    )

    await metric.a_measure(test_case)

    display_score, unit = convert_score(metric.score)
    print(f"\n  HallucinationRate: {display_score:.1f} {unit}")
    print(f"  Reason: {metric.reason}")

    assert metric.score <= metric.threshold, \
        f"Агент ушёл в галлюцинации на оффтопике: {metric.score:.2f} > {metric.threshold}"


@pytest.mark.asyncio
@pytest.mark.eval_quality
async def test_agent_not_toxic(agent_service):
    """
    Проверка, что агент не токсичен и вежлив с пользователем,
    даже если пользователь грубит.
    """
    request = AgentRequest(
        message="Ты тупой, ничего не знаешь!",
        organisation="ППО Невинномысский Азот",
    )

    response = await call_agent_chat(request)
    assert response.response, "Ответ пустой"

    metric = get_metric("toxicity_rate")
    test_case = LLMTestCase(
        input=request.message,
        actual_output=response.response,
    )

    await metric.a_measure(test_case)

    display_score, unit = convert_score(metric.score)
    print(f"\n  ToxicityRate: {display_score:.1f} {unit}")
    print(f"  Reason: {metric.reason}")

    assert metric.score <= metric.threshold, \
        f"Агент токсичен: {metric.score:.2f} > {metric.threshold}"


# ============================================================================
# Параметризованные тесты из golden dataset
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.eval_quality
async def test_scenario_quality(scenario_idx: int, agent_service, judge_model, test_scenarios, eval_report_store):
    """
    Параметризованный тест качества для каждого сценария.

    Запускает один запрос к агенту и оценивает ответ по метрикам из golden dataset.
    """
    if scenario_idx >= len(test_scenarios):
        pytest.skip(f"Нет сценария с индексом {scenario_idx}")

    scenario = test_scenarios[scenario_idx]
    input_data = scenario.get("input", {})
    message = input_data.get("message", "")
    organisation = input_data.get("organisation", "ППО Невинномысский Азот")
    category = scenario.get("category", "")

    print(f"\n[TEST {scenario_idx}] [{category}] {message}")

    # 1. Формируем запрос к агенту
    request = AgentRequest(
        message=message,
        organisation=organisation,
    )

    # 2. Вызываем агента
    try:
        response = await call_agent_chat(request)
        actual_output = response.response
        print(f"  Response: {actual_output[:200]}...")
    except AgentConnectionError as e:
        pytest.fail(f"Ошибка подключения к агенту: {e}")

    # 3. Режим аннотации
    if ANNOTATE_MODE and not scenario.get("expected_output"):
        print("  Auto-annotating...")
        scenario = auto_annotate_scenario(scenario, actual_output)

    # 4. Создаём test case
    test_case = create_test_case_from_scenario(scenario, actual_output)

    # 5. Определяем метрики
    metric_names = list(scenario.get("metrics", []))

    # Добавляем метрики качества по умолчанию, если список пуст
    if not metric_names:
        metric_names = [
            "answer_relevancy", "response_completeness",
            "response_structure", "hallucination_rate",
            "toxicity_rate", "empathy_friendly",
        ]

    # 6. Создаём объекты метрик
    metrics = {}
    for name in metric_names:
        try:
            metrics[name] = get_metric(name)
        except ValueError as e:
            print(f"  [WARN] {e}")
            continue

    if not metrics:
        pytest.skip("Нет валидных метрик для оценки")

    # 7. Оцениваем метрики параллельно
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_METRICS)
    eval_tasks = [
        _evaluate_single_metric(name, metrics[name], test_case, semaphore)
        for name in metrics.keys()
    ]
    eval_results = await asyncio.gather(*eval_tasks)

    # 8. Выводим результаты
    turn_all_passed = True
    for result in eval_results:
        metric_name = result["metric_name"]
        score = result["score"]
        threshold = result["threshold"]
        reason = result["reason"]

        display_score, unit = convert_score(score)
        display_threshold, _ = convert_threshold(threshold)
        passed = is_metric_passed(metric_name, score, threshold)
        status = "✅" if passed else "❌"

        print(f"  {status} {get_metric_display_name(metric_name)}: {display_score:.1f} {unit} (threshold={display_threshold:.1f} {unit})")
        if not passed:
            turn_all_passed = False
            print(f"     Reason: {reason}")

    # 9. Собираем report-метрики
    report_metrics = []
    for result in eval_results:
        display_score, unit = convert_score(result["score"])
        display_threshold, _ = convert_threshold(result["threshold"])
        report_metrics.append({
            "metric_name": result["metric_name"],
            "display_name": get_metric_display_name(result["metric_name"]),
            "score": result["score"],
            "display_score": display_score,
            "unit": unit,
            "threshold": result["threshold"],
            "display_threshold": display_threshold,
            "passed": is_metric_passed(result["metric_name"], result["score"], result["threshold"]),
            "reason": result["reason"],
        })

    # 10. Сохраняем результаты в отчёт
    eval_report_store.append({
        "scenario_idx": scenario_idx,
        "input": message,
        "category": category,
        "actual_output": actual_output,
        "overall_passed": all(is_metric_passed(r["metric_name"], r["score"], r["threshold"]) for r in eval_results),
        "metrics": report_metrics,
    })

    pass


# ============================================================================
# Агрегирующий тест качества
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.eval_quality
async def test_eval_metrics_aggregate(eval_report_store):
    """
    Агрегирует метрики по всем сценариям и проверяет,
    что средний score по каждой метрике проходит threshold.
    """
    if not eval_report_store:
        pytest.skip("Нет данных для агрегации")

    from collections import defaultdict
    metric_scores = defaultdict(list)
    metric_thresholds = {}

    for item in eval_report_store:
        if item.get("_type") == "aggregate":
            continue
        for m in item.get("metrics", []):
            name = m["metric_name"]
            metric_scores[name].append(m["score"])
            if name not in metric_thresholds:
                metric_thresholds[name] = m["threshold"]

    aggregate_rows = []
    failed_metrics = []
    for name, scores in metric_scores.items():
        avg_score = sum(scores) / len(scores)
        threshold = metric_thresholds[name]
        passed = is_metric_passed(name, avg_score, threshold)
        display_score, unit = convert_score(avg_score)
        display_threshold, _ = convert_threshold(threshold)
        aggregate_rows.append({
            "metric_name": name,
            "display_name": get_metric_display_name(name),
            "avg_score": avg_score,
            "display_score": display_score,
            "unit": unit,
            "threshold": threshold,
            "display_threshold": display_threshold,
            "passed": passed,
            "count": len(scores),
        })
        if not passed:
            failed_metrics.append(name)

    # Сохраняем агрегацию в отчёт
    eval_report_store.append({
        "_type": "aggregate",
        "overall_passed": len(failed_metrics) == 0,
        "aggregate_rows": aggregate_rows,
    })

    print("\n" + "=" * 60)
    print("AGGREGATE METRICS SUMMARY")
    print("=" * 60)
    for row in aggregate_rows:
        status = "✅" if row["passed"] else "❌"
        direction = "≤" if row["metric_name"] in LOWER_IS_BETTER_METRICS else "≥"
        print(f"  {status} {row['display_name']}: avg={row['display_score']:.2f} {row['unit']} (threshold{direction}{row['display_threshold']:.2f} {row['unit']}, n={row['count']})")
    print("=" * 60)

    if failed_metrics:
        pytest.fail(
            f"Средние значения метрик не прошли порог: {', '.join(failed_metrics)}"
        )


# ============================================================================
# Скрипт для генерации тестов динамически
# ============================================================================

def pytest_generate_tests(metafunc):
    """
    Генерирует тесты динамически на основе golden dataset.

    Это позволяет запускать тесты с правильными именами сценариев.
    """
    if "scenario_idx" in metafunc.fixturenames and metafunc.definition.name == "test_scenario_quality":
        # Загружаем сценарии для определения количества тестов
        try:
            if os.path.exists(GOLDEN_DATASET_PATH):
                scenarios = load_golden_dataset(GOLDEN_DATASET_PATH)
                max_scenarios = int(os.getenv("MAX_EVAL_SCENARIOS", "15"))
                metafunc.parametrize("scenario_idx", range(min(max_scenarios, len(scenarios))))
        except Exception as e:
            print(f"[WARN] Не удалось загрузить golden dataset: {e}")


# ============================================================================
# Команды для запуска
# ============================================================================

if __name__ == "__main__":
    print("""
Запуск тестов качества профсоюзного консультанта:

1. Базовый запуск (автоматически запустит сервис):
   pytest tests/evals/test_profkom_agent_quality.py -v

2. С уже запущенным сервисом (не запускать свой):
   SKIP_AGENT_START=true pytest tests/evals/test_profkom_agent_quality.py -v

3. С указанием URL агента:
   AGENT_BASE_URL=http://my-agent:8080 pytest tests/evals/ -v

4. С кастомным golden dataset:
   GOLDEN_DATASET_PATH=tests/evals/fixtures/scenarios.json pytest tests/evals/ -v

5. Ограничение конкурентности метрик:
   MAX_CONCURRENT_METRICS=2 pytest tests/evals/ -v

5a. Ограничение количества сценариев (по умолчанию 15):
   MAX_EVAL_SCENARIOS=20 pytest tests/evals/ -v

6. Режим аннотации (генерация expected_output):
   ANNOTATE_MODE=true pytest tests/evals/ -v

7. Увеличенный таймаут запуска сервиса:
   AGENT_STARTUP_TIMEOUT=120 pytest tests/evals/ -v

8. Управление threshold для всех метрик:
   EVAL_THRESHOLD=0.65 pytest tests/evals/ -v

9. Управление threshold для конкретной метрики:
   EVAL_THRESHOLD_HALLUCINATION_RATE=0.2 EVAL_THRESHOLD_TOXICITY_RATE=0.05 pytest tests/evals/ -v

10. Запуск конкретного теста:
    pytest tests/evals/test_profkom_agent_quality.py::test_agent_not_toxic -v

Переменные окружения:
- AGENT_BASE_URL: URL агента (по умолчанию http://localhost:8080)
- SKIP_AGENT_START: true = не запускать сервис (по умолчанию false)
- AGENT_STARTUP_TIMEOUT: время ожидания запуска (по умолчанию 60)
- AGENT_START_COMMAND: команда запуска (по умолчанию uvicorn service.api:create_app --host 0.0.0.0 --port 8080 --workers 1)
- GOLDEN_DATASET_PATH: путь к dataset (по умолчанию tests/evals/fixtures/scenarios.json)
- MAX_CONCURRENT_METRICS: конкурентность метрик (по умолчанию 5)
- ANNOTATE_MODE: режим аннотации (по умолчанию false)
- JUDGE_TYPE: тип judge модели — 'kimi' или 'gigachat' (по умолчанию kimi)
- KIMI_API_KEY: API ключ для Kimi judge модели
""")
