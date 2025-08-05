#!/bin/bash

for file in *; do
    if [[ -f "$file" && ! "$file" =~ \.sh$ && ! "$file" =~ \.md$ ]]; then
        new_name=$(echo "$file" | tr ' ' '_' | tr -d ',' | tr '[:upper:]' '[:lower:]' | sed 's/\.[^.]*$/.md/')
        echo "Конвертируем: $file -> $new_name"
        markitdown "$file" -o "../data/$new_name"
    fi
done