#!/bin/bash
set -e  # Выход при первой ошибке

# Пути
ENV_PATH="$HOME/environments/chatbot/bin/activate"
PROJECT_PATH="$HOME/projects/GeneralPurposeChatBot/"
PY_SCRIPT="$HOME/projects/GeneralPurposeChatBot/src/scripts/load_data_to_chroma.py"

# Правильное получение аргументов
SRC_DIR="$1"              # Первый аргумент - путь к директории
COLLECTION_NAME="$2"      # Второй аргумент - имя коллекции

# Проверка аргументов
if [[ -z "$SRC_DIR" || -z "$COLLECTION_NAME" ]]; then
    echo "Использование: $0 <путь_к_директории> <имя_коллекции>"
    echo "Пример: $0 /tmp/md_azot_profkom/ my_collection"
    exit 1
fi

# Проверяем существование виртуального окружения
if [[ ! -f "$ENV_PATH" ]]; then
    echo "Ошибка: виртуальное окружение не найдено по пути $ENV_PATH"
    exit 1
fi

# Активируем виртуальное окружение
echo "Активируем виртуальное окружение..."
source "$ENV_PATH"

echo "Переустанавливаем для обеспечения актуальности..."
uv pip install --force-reinstall "$PROJECT_PATH"

# Проверяем существование Python скрипта
if [[ ! -f "$PY_SCRIPT" ]]; then
    echo "Ошибка: Python скрипт не найден по пути $PY_SCRIPT"
    exit 1
fi

# Проверяем существование исходной директории
if [[ ! -d "$SRC_DIR" ]]; then
    echo "Ошибка: исходная директория $SRC_DIR не найдена"
    exit 1
fi

# Запускаем скрипт
echo "Загружаем данные из $SRC_DIR в коллекцию $COLLECTION_NAME..."
cd "$HOME/projects/GeneralPurposeChatBot/src/scripts"
python load_data_to_chroma.py --source-dir "$SRC_DIR" --collection "$COLLECTION_NAME"

echo "Скрипт завершен!"