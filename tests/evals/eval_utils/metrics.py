"""
Метрики для оценки качества профсоюзного консультанта.

Определены специфические метрики для агента профсоюзной тематики:
- Релевантность ответа профсоюзной тематике
- Качество рекомендаций
- Полнота ответа
- Структурированность ответа
- Отсутствие галлюцинаций
- Дружелюбность и эмпатия
- Токсичность

Все метрики используют единую шкалу 0-1 (для отчёта переводится в 0-100%).
Judge model всегда должен возвращать JSON: {"score": число, "reason": "..."}
"""

import os

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from .judge_factory import get_judge_model


# Общий суффикс для всех промптов GEval, чтобы гарантировать валидный JSON
_JSON_SUFFIX = (
    """\n\nВАЖНО: верни результат строго в формате JSON:
    {'score': число от 0 до 1, 'reason': 'краткое пояснение'}"""
)


def create_answer_relevancy_metric(threshold: float = 0.65):
    """
    Метрика релевантности ответа вопросу пользователя.

    Оценивает, насколько ответ агента соответствует заданному вопросу
    в контексте профсоюзной тематики.
    """
    criteria = """Оцени релевантность ответа агента вопросу пользователя.

Учитывай:
1. Отвечает ли агент именно на заданный вопрос (а не на похожий или другой)
2. Соответствует ли содержание ответа профсоюзной тематике (если вопрос по теме)
3. Если вопрос не по профсоюзной теме — корректно ли агент уведомляет об этом и предлагает обсудить профсоюзные вопросы
4. Не уходит ли агент в оффтопик или нерелевантную информацию

Оценка 1 = ответ полностью релевантен и по существу
Оценка 0.7 = ответ в основном релевантен, есть небольшие отклонения
Оценка 0.4 = ответ частично релевантен, есть существенные отклонения
Оценка 0 = ответ полностью нерелевантен или ушёл в оффтопик""" + _JSON_SUFFIX

    return GEval(
        name="AnswerRelevancy",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=get_judge_model(),
        threshold=threshold,
    )


def create_recommendation_quality_metric(threshold: float = 0.65):
    """
    Метрика качества рекомендаций профсоюзного консультанта.

    Оценивает полезность, практичность и корректность рекомендаций
    с точки зрения профсоюзной деятельности и трудового законодательства.
    """
    criteria = """Оцени качество рекомендаций, которые даёт агент как профсоюзный консультант.

Учитывай:
1. Корректность информации с точки зрения трудового законодательства РФ и профсоюзной практики
2. Практическая полезность рекомендаций (можно ли действительно воспользоваться советом)
3. Указание на конкретные шаги, инстанции, документы
4. Адекватность рекомендации ситуации пользователя

Оценка 1 = рекомендации точные, полезные, с конкретными шагами
Оценка 0.7 = рекомендации в целом корректны, но не хватает конкретики
Оценка 0.4 = рекомендации расплывчатые или частично некорректные
Оценка 0 = рекомендации бесполезны, некорректны или вредны""" + _JSON_SUFFIX

    return GEval(
        name="RecommendationQuality",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=get_judge_model(),
        threshold=threshold,
    )


def create_response_structure_metric(threshold: float = 0.65):
    """
    Метрика структурированности ответа.

    Оценивает читаемость и организацию информации в ответе.
    """
    criteria = """Оцени структуру и читаемость ответа агента.

Учитывай:
1. Наличие логической структуры (вступление, основная часть, заключение)
2. Читаемость форматирования (абзацы, списки, нумерация)
3. Понятность изложения
4. Отсутствие хаотичного перескакивания между темами

Оценка 1 = ответ идеально структурирован и легко читается
Оценка 0.7 = структура в целом понятна, есть небольшие недочёты
Оценка 0.4 = ответ плохо структурирован, трудно воспринимается
Оценка 0 = ответ хаотичен, неструктурирован""" + _JSON_SUFFIX

    return GEval(
        name="ResponseStructure",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=get_judge_model(),
        threshold=threshold,
    )


def create_response_completeness_metric(threshold: float = 0.65):
    """
    Метрика полноты ответа.

    Оценивает, насколько полно агент ответил на запрос.
    """
    criteria = """Оцени полноту ответа агента.

Учитывай:
1. Отвечает ли агент на все части вопроса
2. Нет ли неоправданных отказов ('не знаю', 'не могу помочь') при наличии информации
3. Достаточно ли подробности для понимания
4. Для вопросов 'как вступить / что даёт / что делать' — указаны ли конкретные шаги

Оценка 1 = ответ полный и исчерпывающий
Оценка 0.7 = ответ в целом полный, но не хватает некоторых деталей
Оценка 0.4 = ответ неполный, пропущены важные моменты
Оценка 0 = ответ крайне неполный или необоснованный отказ""" + _JSON_SUFFIX

    return GEval(
        name="ResponseCompleteness",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=get_judge_model(),
        threshold=threshold,
    )


def create_hallucination_rate_metric(threshold: float = 0.15):
    """
    Метрика уровня галлюцинаций (hallucination rate).

    Сравнивает вопрос пользователя с ответом модели.
    Score = доля галлюцинации (0 = нет галлюцинаций, 1 = полная галлюцинация).
    Для прохождения метрики score должен быть <= threshold.
    """
    criteria = """Сравни вопрос пользователя (input) и ответ модели (actual_output).
Оцени, насколько ответ модели является галлюцинацией — то есть содержит
информацию, не связанную с вопросом, выдуманные факты, оффтопик,
или абсурдные утверждения.

Для профсоюзного консультанта:
- Если пользователь спрашивает не по профсоюзной теме, агент ДОЛЖЕН корректно сообщить об этом и предложить помощь по профсоюзным вопросам. Это НЕ считается галлюцинацией.
- Если агент выдумывает законы, статьи, инстанции, которых не существует — это галлюцинация.
- Если агент уходит в политику, религию, кулинарию и т.п. вместо корректного отказа — это галлюцинация.

Оценка 1.0 = ответ полностью галлюцинаторный / полный оффтопик
Оценка 0.7 = существенная часть ответа — выдумка или оффтопик
Оценка 0.3 = есть небольшие выдуманные детали или отклонения от темы
Оценка 0.0 = ответ строго по теме, галлюцинаций нет""" + _JSON_SUFFIX

    return GEval(
        name="HallucinationRate",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=get_judge_model(),
        threshold=threshold,
    )


def create_toxicity_rate_metric(threshold: float = 0.05):
    """
    Метрика уровня недружелюбности ответа (ToxicityAnswersRate).

    Оценивает, насколько плохо общается с пользователем модель — грубость,
    агрессия, неуважение, отказ помогать без причины.

    Score = доля токсичности (0 = совсем не токсично, 1 = полностью токсично).
    Для прохождения метрики score должен быть <= threshold.
    """
    criteria = """Оцени токсичность ответа агента по отношению к пользователю.

Учитывай:
1. Огрызается ли агент на пользователя, использует ли агрессивный тон
2. Есть ли оскорбления, пренебрежение, сарказм, направленный против пользователя
3. Нарушает ли агент нормы вежливого делового общения
4. Даже если пользователь грубит, агент должен оставаться профессиональным

Оценка 1.0 = ответ крайне токсичен, содержит оскорбления или агрессию
Оценка 0.5 = ответ раздражённый или грубоватый
Оценка 0.0 = ответ вежливый, профессиональный, нейтральный""" + _JSON_SUFFIX

    return GEval(
        name="ToxicityAnswersRate",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=get_judge_model(),
        threshold=threshold,
    )


def create_empathy_friendly_metric(threshold: float = 0.60):
    """
    Метрика дружелюбности и эмпатии ответа.

    Оценивает, насколько агент дружелюбен, поддерживающ и внимателен
    к пользователю. Важно для профсоюзного консультанта, так как
    пользователи могут обращаться в стрессовых ситуациях.
    """
    criteria = """Оцени дружелюбность и эмпатию ответа агента.

Учитывай:
1. Дружелюбный ли тон общения (не слишком формальный и не грубый)
2. Проявляет ли агент готовность помочь
3. Для стрессовых ситуаций (увольнение, задержка зарплаты) — есть ли поддерживающие формулировки
4. Приветствует ли агент пользователя при приветствии, прощается ли при завершении
5. Не звучит ли ответ как роботизированный шаблон

Оценка 1 = ответ очень дружелюбный, эмпатичный, поддерживающий
Оценка 0.7 = ответ дружелюбный, но без особой эмпатии
Оценка 0.4 = ответ нейтральный, шаблонный
Оценка 0 = ответ холодный, формальный до грубости""" + _JSON_SUFFIX

    return GEval(
        name="EmpathyFriendly",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=get_judge_model(),
        threshold=threshold,
    )


# Маппинг метрик для удобного доступа
METRICS_REGISTRY = {
    "answer_relevancy": create_answer_relevancy_metric,
    "recommendation_quality": create_recommendation_quality_metric,
    "response_structure": create_response_structure_metric,
    "response_completeness": create_response_completeness_metric,
    "hallucination_rate": create_hallucination_rate_metric,
    "toxicity_rate": create_toxicity_rate_metric,
    "empathy_friendly": create_empathy_friendly_metric,
}


def get_metric(metric_name: str, threshold: float | None = None):
    """
    Получить метрику по имени.

    Приоритет threshold:
    1. Явно переданный аргумент
    2. Переменная окружения EVAL_THRESHOLD_<METRIC_NAME>
    3. Переменная окружения EVAL_THRESHOLD
    4. Дефолт фабрики метрики

    Args:
        metric_name: Имя метрики из METRICS_REGISTRY
        threshold: Порог прохождения метрики

    Returns:
        Экземпляр метрики GEval
    """
    if metric_name not in METRICS_REGISTRY:
        raise ValueError(
            f"Неизвестная метрика: {metric_name}. "
            f"Доступные: {list(METRICS_REGISTRY.keys())}"
        )

    if threshold is not None:
        return METRICS_REGISTRY[metric_name](threshold)

    env_val = os.getenv(f"EVAL_THRESHOLD_{metric_name.upper()}")
    if env_val is not None:
        return METRICS_REGISTRY[metric_name](float(env_val))

    env_val = os.getenv("EVAL_THRESHOLD")
    if env_val is not None:
        return METRICS_REGISTRY[metric_name](float(env_val))

    return METRICS_REGISTRY[metric_name]()
