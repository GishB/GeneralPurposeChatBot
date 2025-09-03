#!/bin/bash
set -euo pipefail
SRC="$1"
TGT="$2"
mkdir -p "$TGT"
shopt -s nullglob globstar
for src in "$SRC"/**/*; do
    if [[ -f "$src" ]]; then
        base=$(basename "$src")
        if [[ "$base" =~ \.sh$ || "$base" =~ \.md$ ]]; then
            continue
        fi
        rel=${src#$SRC/}
        rel_dir=$(dirname "$rel" )
        norm_name=$(echo "${base%.*}" | tr ' ' '_' | tr -d ',' | tr '[:upper:]' '[:lower:]')
        dst_dir="$TGT/$rel_dir"
        dst="$dst_dir/$norm_name.md"
        mkdir -p "$dst_dir"
        echo "Конвертируем: $src -> $dst"
        markitdown "$src" -o "$dst"
    fi
done