"""
Утилиты для работы с golden dataset.

Поддерживает:
- Загрузку из JSON файла
- Валидацию формата
- Генерацию expected_output через LLM (auto-annotate)
"""

import json
from pathlib import Path
from typing import Optional

from deepeval.test_case import LLMTestCase

from .judge_factory import get_judge_model


def validate_test_case(item: dict, index: int) -> tuple[bool, str]:
    """
    Валидирует один тест-кейс.

    Args:
        item: Словарь с тест-кейсом
        index: Индекс для сообщения об ошибке

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(item, dict):
        return False, f"Item {index}: должен быть объектом, получен {type(item).__name__}"

    if "input" not in item:
        return False, f"Item {index}: отсутствует обязательное поле 'input'"

    if not isinstance(item["input"], dict):
        return False, f"Item {index}: 'input' должен быть объектом"

    input_data = item["input"]

    if "message" not in input_data:
        return False, f"Item {index}: 'input.message' обязателен"

    if "expected_output" in item and item["expected_output"] is not None and not isinstance(item["expected_output"], str):
        return False, f"Item {index}: 'expected_output' должен быть строкой или null"

    if "metrics" in item and not isinstance(item["metrics"], list):
        return False, f"Item {index}: 'metrics' должен быть массивом"

    return True, ""


def validate_golden_dataset(data: list) -> tuple[bool, str]:
    """
    Валидирует golden dataset.

    Args:
        data: Загруженные JSON данные

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, list):
        return False, "Dataset должен быть JSON массивом"

    if len(data) == 0:
        return False, "Dataset пустой - нет тест-кейсов"

    for i, item in enumerate(data):
        is_valid, error = validate_test_case(item, i)
        if not is_valid:
            return False, error

    return True, ""


def load_golden_dataset(file_path: str) -> list[dict]:
    """
    Загружает golden dataset из JSON файла.

    Args:
        file_path: Путь к JSON файлу

    Returns:
        Список тест-кейсов

    Raises:
        FileNotFoundError: Если файл не найден
        ValueError: Если формат dataset неверный
        json.JSONDecodeError: Если JSON невалидный
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset не найден: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    is_valid, error = validate_golden_dataset(data)
    if not is_valid:
        raise ValueError(f"Неверный формат golden dataset: {error}")

    return data


def create_test_case_from_scenario(
    scenario: dict,
    actual_output: Optional[str] = None,
) -> LLMTestCase:
    """
    Создаёт LLMTestCase из сценария golden dataset.

    Args:
        scenario: Сценарий из golden dataset
        actual_output: Фактический ответ агента (если уже получен)

    Returns:
        LLMTestCase для оценки
    """
    input_data = scenario["input"]
    message = input_data.get("message", "")
    organisation = input_data.get("organisation", "")

    input_text = message
    if organisation:
        input_text = f"[Организация: {organisation}] {message}"

    context = []
    if organisation:
        context.append(f"Организация: {organisation}")
    if scenario.get("category"):
        context.append(f"Категория: {scenario['category']}")

    return LLMTestCase(
        input=input_text,
        actual_output=actual_output or "",
        expected_output=scenario.get("expected_output"),
        context=context if context else None,
    )


def auto_annotate_scenario(
    scenario: dict,
    actual_output: str,
) -> dict:
    """
    Автоматически генерирует expected_output через LLM.

    Args:
        scenario: Сценарий с input данными
        actual_output: Фактический ответ агента

    Returns:
        Аннотированный сценарий с expected_output
    """
    model = get_judge_model()

    input_data = scenario["input"]
    message = input_data.get("message", "")
    organisation = input_data.get("organisation", "не указана")

    prompt = f"""Ты — эксперт по профсоюзной тематике.

На основе запроса пользователя и ответа агента сгенерируй ИДЕАЛЬНЫЙ (reference) ответ.

Запрос пользователя (организация: {organisation}):
{message}

Ответ агента:
{actual_output[:1000]}...

Сгенерируй ideal/reference ответ, который должен был бы дать идеальный профсоюзный консультант.
Учитывай:
1. Релевантность запросу
2. Полноту информации
3. Дружелюбный, но профессиональный тон
4. Корректность с точки зрения трудового законодательства и профсоюзной практики

Верни ТОЛЬКО текст ответа, без пояснений.
"""

    try:
        expected_output = model.generate(prompt)
        scenario = scenario.copy()
        scenario["expected_output"] = expected_output.strip()
        scenario["_auto_annotated"] = True
        return scenario
    except Exception as e:
        scenario = scenario.copy()
        scenario["expected_output"] = actual_output
        scenario["_auto_annotation_failed"] = str(e)
        return scenario


def save_annotated_dataset(
    scenarios: list[dict],
    output_path: str,
) -> None:
    """
    Сохраняет аннотированный dataset.

    Args:
        scenarios: Список сценариев с expected_output
        output_path: Путь для сохранения
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] Аннотированный dataset сохранён: {output_path}")
