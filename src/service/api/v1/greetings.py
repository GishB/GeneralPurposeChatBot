"""Fast-path helpers for greeting messages.

Greetings should be answered instantly without invoking the full agent graph,
since the agent graph is tuned for trade-union consulting and tends to generate
long union-related intros even for a simple "hello".
"""

import re

# Regex matches a message that is *only* a greeting (optional punctuation/spaces).
_GREETING_RE = re.compile(
    r"^("
    r"привет|приветствую|"
    r"здравствуй(те)?|здрасте|здарова?|"
    r"хаюшки|хай|салют|"
    r"добрый\s+(день|вечер)|доброе\s+утро|доброй\s+ночи|"
    r"hello|hi|hey"
    r")[\s!,.?]*$",
    re.IGNORECASE | re.UNICODE,
)


def is_greeting(text: str) -> bool:
    """Return True if the user message is a plain greeting."""
    return bool(_GREETING_RE.match(text.strip()))
