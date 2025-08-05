from typing import List
from pathlib import Path
import hashlib
from semantic_text_splitter import MarkdownSplitter

from UnionChatBot.utils.save_script.models.document import Document, ProcessingConfig


class MarkdownProcessor:
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.splitter = MarkdownSplitter.from_tiktoken_model(
            "gpt-3.5-turbo", capacity=config.max_tokens, overlap=config.overlap_tokens
        )

    def process_file(self, file_path: Path) -> List[Document]:
        text = file_path.read_text(encoding="utf-8")
        chunks = self.splitter.chunks(text)
        if not chunks:
            return []

        header = self._extract_header(chunks[0])
        docs = []
        for chunk in chunks:
            if len(chunk) < self.config.min_chunk_chars:
                continue
            content = self._format_content(header, chunk)
            doc_id = self._generate_id(content)
            metadata = {"source_file": str(file_path), "header": header}
            docs.append(Document(content=content, metadata=metadata, doc_id=doc_id))
        return docs

    def _extract_header(self, first_chunk: str) -> str:
        header = (
            first_chunk.replace("\n", " ")
            .replace("*", " ")
            .replace("#", " ")
            .replace("\\", " ")
        )
        header = header.split("!")[-1].split("base64")[-1].strip()
        return " ".join(header.split())

    def _format_content(self, header: str, chunk: str) -> str:
        return f"<header> {header} </header> <body> {chunk} </body>"

    def _generate_id(self, content: str) -> str:
        return hashlib.sha1(content.encode()).hexdigest()
