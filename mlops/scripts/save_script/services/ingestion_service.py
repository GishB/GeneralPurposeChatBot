from pathlib import Path

from UnionChatBot.utils.save_script.processors.markdown_processor import (
    MarkdownProcessor,
)
from UnionChatBot.utils.save_script.storage.chroma_storage import ChromaStorage
from UnionChatBot.utils.save_script.readers.file_reader import LocalFileReader


class IngestionService:
    def __init__(
        self,
        file_reader: LocalFileReader,
        processor: MarkdownProcessor,
        storage: ChromaStorage,
        collection_name: str,
    ):
        self.file_reader = file_reader
        self.processor = processor
        self.storage = storage
        self.collection_name = collection_name

    def ingest_directory(self, directory: Path):
        files = self.file_reader.read_files(directory)
        all_docs = []
        for file in files:
            docs = self.processor.process_file(file)
            all_docs.extend(docs)

        self.storage.store_documents(self.collection_name, all_docs)
