from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

import docx2txt

from service.logger import LoggerConfigurator


@dataclass
class DocumentChunk:
    """Один чанк документа, готовый для записи в Chroma."""

    id: str
    text: str
    metadata: dict[str, Any]


def _read_docx(path: Path) -> str:
    """Чтение .docx в unicode-строку."""
    text = docx2txt.process(str(path)) or ""
    return text.strip()


def _split_into_chunks(
    text: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 256,
) -> List[str]:
    """Простое посимвольное разбиение текста на чанки с overlap (без учёта префикса)."""
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end]
        chunks.append(chunk)

        if end >= length:
            break

        # Отступаем назад на overlap символов
        start = end - chunk_overlap

    return chunks


def _calc_signature(text: str) -> str:
    """Подпись содержимого файла для отслеживания изменений."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _build_topic_prefix(full_text: str, max_tokens: int = 256) -> str:
    """Строим топик-контекст из начала документа на max_tokens токенов.

    Токен здесь грубо считаем как слово, разделённое пробелами.
    """
    if not full_text:
        return ""

    tokens = full_text.split()
    topic_tokens = tokens[:max_tokens]
    prefix = " ".join(topic_tokens)
    return prefix


def load_docx_with_metadata(
    logger: LoggerConfigurator,
    root_dir: str | Path,
    chunk_size: int = 750,
    chunk_overlap: int = 250,
    topic_tokens: int = 120,
) -> List[DocumentChunk]:
    """Обходит root_dir, читает все .docx и возвращает список чанков с осмысленными id.

    id формируется как "<rel_path>::chunk:<idx>", например:
    "contracts/lease_2024.docx::chunk:0"

    ВАЖНО: к каждому чанку в начало дописывается топик-контекст (первые topic_tokens
    токенов документа). Таким образом каждый чанк всегда содержит начало документа.
    """
    root = Path(root_dir)
    chunks: List[DocumentChunk] = []

    logger.debug("Loading docx with metadata...")
    for path in root.rglob("*.docx"):  # TO DO: tqdm
        full_text = _read_docx(path)
        if not full_text:
            continue

        rel_path = path.relative_to(root)
        rel_path_str = str(rel_path).replace(os.sep, "/")  # для стабильного id
        file_signature = _calc_signature(full_text)

        # Тема по папке (как раньше)
        topic = rel_path.parts[0] if len(rel_path.parts) > 1 else "general"

        # Топик-контекст на topic_tokens токенов из начала документа
        topic_prefix = _build_topic_prefix(full_text, max_tokens=topic_tokens)

        # Чанки по основному тексту
        text_chunks = _split_into_chunks(
            text=full_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        num_chunks = len(text_chunks)

        for idx, base_chunk_text in enumerate(text_chunks):
            doc_id = f"{rel_path_str}::chunk:{idx}"

            # ВАЖНО: препендим топик в начало чанка
            if topic_prefix:
                chunk_text = (
                    "# Титульный текст документа: \n\n"
                    + topic_prefix
                    + "\n\n"
                    + "## Часть текста по документу: \n\n"
                    + base_chunk_text
                    + "\n\n"
                )
            else:
                chunk_text = base_chunk_text

            metadata: dict[str, Any] = {
                "source": str(path),
                "rel_path": rel_path_str,
                "topic": topic,
                "filename": path.name,
                "extension": path.suffix,
                "chunk_index": idx,
                "num_chunks": num_chunks,
                "file_signature": file_signature,
                "topic_prefix_tokens": topic_tokens,
            }

            chunks.append(
                DocumentChunk(
                    id=doc_id,
                    text=chunk_text,
                    metadata=metadata,
                )
            )

    return chunks
