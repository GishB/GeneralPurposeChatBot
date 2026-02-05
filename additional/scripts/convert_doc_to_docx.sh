#!/usr/bin/env bash
set -euo pipefail

# ---------- CONFIG ----------
# Папка с исходными .doc‑файлами (по умолчанию – src/data)
SRC_DIR="${1:-$(pwd)/data}"
# Выводим готовый .docx **в ту же папку**, где находится исходный .doc
OUT_DIR="$SRC_DIR"
# --------------------------------

mkdir -p "$OUT_DIR"

echo "🔎 Ищем .doc‑файлы в: $SRC_DIR"
echo "📁 Конвертируем их **на месте**, а затем удаляем оригиналы"
echo ""

# Пробегаем по всем .doc‑файлам рекурсивно
while IFS= read -r -d '' doc_path; do
    echo "⚙️  Конвертируем: $doc_path"
    if soffice --headless --convert-to docx --outdir "$OUT_DIR" "$doc_path"; then
        echo "✅  => $(basename "${doc_path%.*}.docx")"
        # Успешно сконвертировано – удаляем исходный .doc
        rm -f "$doc_path"
        echo "🗑️  Удалён оригинал: $doc_path"
    else
        echo "❌  Ошибка конвертации: $doc_path"
        # Если конвертация не удалась, оставляем файл нетронутым
    fi
done < <(find "$SRC_DIR" -type f -name '*.doc' -print0)

# На случай, если какие‑то .doc‑файлы «застряли» (например, конвертер упал)
# Можно выполнить принудительное удаление после основной проходки:
if compgen -G "$SRC_DIR/**/*.doc" > /dev/null; then
    echo "🔎 Находим оставшиеся .doc‑файлы и удаляем их..."
    find "$SRC_DIR" -type f -name '*.doc' -exec rm -f {} +
    echo "🗑️  Все оставшиеся .doc удалены"
fi

echo ""
echo "🎉 Готово! Все .doc → .docx находятся в их исходных каталогах"