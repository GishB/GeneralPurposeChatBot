import argparse
import os
from pathlib import Path

from UnionChatBot.utils.save_script.processors.markdown_processor import (
    MarkdownProcessor,
)
from UnionChatBot.utils.save_script.storage.chroma_storage import ChromaStorage
from UnionChatBot.utils.save_script.readers.file_reader import LocalFileReader
from UnionChatBot.utils.save_script.services.ingestion_service import IngestionService
from UnionChatBot.utils.save_script.models.document import ProcessingConfig


def main():
    parser = argparse.ArgumentParser(
        description="Заполняем векторную базу данных исходя из MarkDown документов"
    )
    parser.add_argument(
        "--source-dir", type=Path, default=Path(__file__).parent.parent / "data"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=os.getenv("COLLECTION_NAME", "PRODUCTION_PROFKOM"),
    )
    parser.add_argument(
        "--chroma-host",
        type=str,
        default=os.getenv(
            "CHROMA_HOST", "https://www.supermeatboy.ru/chromadb/"
        ),  # домен вместо IP
    )
    parser.add_argument("--api-token", type=str, default=os.getenv("NGINX_TOKEN"))
    args = parser.parse_args()

    config = ProcessingConfig.from_env()
    processor = MarkdownProcessor(config)
    storage = ChromaStorage(host=args.chroma_host, token=args.api_token)
    reader = LocalFileReader()
    service = IngestionService(reader, processor, storage, args.collection)
    service.ingest_directory(args.source_dir)


if __name__ == "__main__":
    main()
