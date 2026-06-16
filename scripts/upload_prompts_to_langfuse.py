import os
import re
import sys
from pathlib import Path

# Добавляем venv в путь
sys.path.insert(0, "/Users/aleksandrsamofalov/PycharmProjects/UnionApp/GeneralPurposeChatBot/.venv/lib/python3.13/site-packages")

from langfuse import Langfuse

HOST = os.environ.get("LANGFUSE_HOST", "http://127.0.0.1:3001")
PUBLIC_KEY = os.environ["LANGFUSE_PUBLIC_KEY"]
SECRET_KEY = os.environ["LANGFUSE_SECRET_KEY"]

PROMPTS_DIR = Path("/Users/aleksandrsamofalov/PycharmProjects/UnionApp/GeneralPurposeChatBot/prompts")

# Имена файлов для загрузки
FILES = ["01-core-prompts.md", "02-enhanced-prompts.md"]


def parse_md(path: Path) -> dict[str, str]:
    """Парсит md-файл и возвращает {prompt_name: prompt_text}."""
    text = path.read_text(encoding="utf-8")
    # Разбиваем на секции по заголовкам ## N. name или ## name
    # Используем regex с захватом имени и содержимого до следующего заголовка ## или конца файла
    pattern = re.compile(
        r"^##\s+(?:\d+\.\s+)?(.+?)\n.*?```text\n(.*?)```",
        re.MULTILINE | re.DOTALL,
    )
    prompts = {}
    for match in pattern.finditer(text):
        name = match.group(1).strip()
        body = match.group(2).strip()
        prompts[name] = body
    return prompts


def upload_prompts():
    client = Langfuse(
        host=HOST,
        public_key=PUBLIC_KEY,
        secret_key=SECRET_KEY,
    )

    if not client.auth_check():
        print("Langfuse auth failed", file=sys.stderr)
        sys.exit(1)
    print(f"Connected to {HOST}")

    total = 0
    for filename in FILES:
        path = PROMPTS_DIR / filename
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            continue
        prompts = parse_md(path)
        print(f"\nParsed {len(prompts)} prompts from {filename}")
        for name, prompt_text in prompts.items():
            print(f"  Uploading {name} ...", end=" ")
            try:
                # Создаём prompt с labels production и latest
                client.create_prompt(
                    name=name,
                    prompt=prompt_text,
                    labels=["production", "latest"],
                    type="text",
                )
                print("OK")
                total += 1
            except Exception as e:
                print(f"ERROR: {e}", file=sys.stderr)

    print(f"\nTotal uploaded: {total}")


if __name__ == "__main__":
    upload_prompts()
