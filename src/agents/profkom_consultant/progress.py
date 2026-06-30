"""Человекочитаемые сообщения прогресса для нод агента."""

from __future__ import annotations

from typing import Final

# Отображение технических имён нод на глаголы в русском языке.
NODE_STEP_MESSAGES: Final[dict[str, str]] = {
    "validate": "Проверяю вопрос на соответствие политике общения…",
    "decompose_question": "Разбираю ваш вопрос на простые части…",
    "answer_parts_async": "Ищу ответы в документах профсоюза…",
    "collect_final_answer": "Собираю развёрнутый ответ…",
    "check_user_answer": "Проверяю, насколько ответ отвечает на ваш вопрос…",
    "generate_additional_questions": "Уточняю детали, чтобы ответ был точнее…",
    "validate_final_answer": "Проверяю готовый ответ перед отправкой…",
    "update_user_history_context": "Сохраняю контекст разговора…",
    "reject_stub": "Формирую ответ по тематике вопроса…",
    "done": "Ответ готов",
    "error": "Произошла ошибка",
}


NODE_STEP_KEYS: Final[tuple[str, ...]] = tuple(NODE_STEP_MESSAGES.keys())
