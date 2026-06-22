"""Утилиты для парсинга ответов LLM в агенте."""

import json
import re


def parse_json_response(text: str) -> dict | list | None:
    """Извлекает JSON-объект или массив из ответа LLM.

    Обрабатывает markdown-обёртки (```json ... ```), лишние обратные кавычки
    и префикс «json». Если прямой парсинг не удался, пытается найти первый
    JSON-объект/массив в тексте.

    Args:
        text: Сырой текст ответа от языковой модели.

    Returns:
        Распарсенный dict/list или None, если JSON не найден.
    """
    if not text:
        return None

    cleaned = text.strip()

    # Убираем markdown-блоки кода
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    cleaned = cleaned.strip().strip("`").removeprefix("json").strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Пробуем найти первый JSON-объект или массив внутри мусора
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    return None
