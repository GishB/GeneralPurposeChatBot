import re


def is_specific_error(text: str) -> bool:
    """Обрабатывает случаи, когда ответ на запрос пользователя это заглушка Яндекса.

    Args:
        text: генерация YandexGPT модели после обработки вопроса.

    Returns:
        bool: Если True, то этот ответ пользователю не показываем.
    """
    # Регулярное выражение для поиска ссылок на Яндекс
    pattern = r"\b(?:https?://)?(?:[a-z0-9-]+\.)*yandex\.(?:ru|com|ua|by|kz)(?:/\S*)?\b"

    # Игнорируем регистр для поиска
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False
