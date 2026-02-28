from __future__ import annotations

from collections import defaultdict
from typing import List

import chromadb

from pathlib import Path
from service.logger import LoggerConfigurator
from modules.chroma_ext.utils import MyEmbeddingFunction
from .data_reader import DocumentChunk, load_docx_with_metadata


def _group_by_source(chunks: List[DocumentChunk]):
    by_source: dict[str, List[DocumentChunk]] = defaultdict(list)
    for ch in chunks:
        source = ch.metadata["source"]
        by_source[source].append(ch)
    return by_source

def _collect_current_sources(root_dir: str) -> set[str]:
    root = Path(root_dir)
    return {str(p) for p in root.rglob("*.docx")}

def sync_docx_directory_to_collection(
    logger: LoggerConfigurator,
    root_dir: str,
    collection_name: str,
    **kwargs
) -> None:
    """Синхронизирует все .docx из root_dir в коллекцию Chroma.

    Notes:
        Для каждого файла:
        - генерируются детерминированные id: "<rel_path>::chunk:<idx>";
        - рассчитывается подпись file_signature по контенту;
        - если в коллекции уже есть записи с тем же source и тем же file_signature,
          файл пропускается;
        - если подпись другая — все старые чанки этого файла удаляются и пишутся заново.
    """

    api_key = kwargs.get("api_key")
    folder_id = kwargs.get("folder_id")
    api_url = kwargs.get("api_url")
    chroma_host = kwargs.get("host")
    chroma_port = kwargs.get("port")

    logger.info(f"Chroma: {chroma_host}:{chroma_port}, collection={collection_name}")
    logger.info(f"Reading .docx from: {root_dir}")

    # Эмбеддер для ДОКУМЕНТОВ
    embedder = MyEmbeddingFunction(
        logger=logger,
        api_url=api_url,
        folder_id=folder_id,
        iam_token=api_key,
        text_type="doc",  # документные эмбеддинги
    )

    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedder,
    )

    # Читаем все файлы и получаем чанки с осмысленными id
    chunks = load_docx_with_metadata(logger=logger, root_dir=root_dir)
    if not chunks:
        logger.warning("No .docx files found, nothing to index")
        return

    logger.info(f"Loaded {len(chunks)} chunks from disk")

    # Группируем чанки по исходному файлу
    by_source = _group_by_source(chunks)

    for source, file_chunks in by_source.items():
        new_signature = file_chunks[0].metadata["file_signature"]
        logger.info(f"Processing file: {source} (signature={new_signature})")

        # Смотрим, что уже есть в коллекции по этому source
        existing = collection.get(
            where={"source": source},
            include=["metadatas"],
        )

        old_ids = existing.get("ids", [])
        old_metas = existing.get("metadatas", [])

        if old_ids:
            old_sig = old_metas[0].get("file_signature")
            if old_sig == new_signature:
                logger.info(f"  -> unchanged, skip (signature={old_sig})")
                continue

            logger.info(f"  -> changed, updating (old={old_sig}, new={new_signature})")
            # Удаляем все старые чанки этого файла
            collection.delete(where={"source": source})

        # Добавляем новые чанки
        ids = [ch.id for ch in file_chunks]
        docs = [ch.text for ch in file_chunks]
        metas = [ch.metadata for ch in file_chunks]

        logger.info(f"  -> adding {len(ids)} chunks")
        collection.add(
            ids=ids,
            documents=docs,
            metadatas=metas
        )

    current_sources = _collect_current_sources(root_dir)
    logger.info(f"Current sources on disk: {len(current_sources)}")

    # Забираем все метаданные из коллекции
    collection_data = collection.get(include=["metadatas"])
    metadatas = collection_data.get("metadatas", [])

    sources_in_collection = {m["source"] for m in metadatas if "source" in m}
    to_delete_sources = sources_in_collection - current_sources

    if not to_delete_sources:
        logger.info("No removed files detected, nothing to delete")
    else:
        logger.info(f"Found {len(to_delete_sources)} deleted files, cleaning up in Chroma")
        for src in to_delete_sources:
            logger.info(f"  -> deleting all chunks for removed file: {src}")
            collection.delete(where={"source": src})  # удаляем все чанки этого файла [web:34][web:41]

    logger.info("Sync finished")
