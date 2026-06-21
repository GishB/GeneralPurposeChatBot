"""
Фабрика judge-моделей для DeepEval.

Позволяет переключаться между GigaChat и Kimi (Moonshot AI)
через переменную окружения JUDGE_TYPE.
"""

import os


def get_judge_model():
    """
    Фабричная функция для получения judge модели.

    Переменная окружения JUDGE_TYPE определяет провайдера:
        - "gigachat" (по умолчанию) — использует GigaChatJudgeModel
        - "kimi" — использует KimiJudgeModel

    Returns:
        Экземпляр DeepEvalBaseLLM-совместимой модели.
    """
    judge_type = os.getenv("JUDGE_TYPE", "kimi").lower()

    if judge_type == "kimi":
        from .kimi_judge import KimiJudgeModel
        return KimiJudgeModel()

    # По умолчанию GigaChat
    from .gigachat_judge import GigaChatJudgeModel
    return GigaChatJudgeModel()
