from dataclasses import dataclass
from typing import Dict


@dataclass
class Document:
    content: str
    metadata: Dict[str, any]
    doc_id: str


@dataclass
class ProcessingConfig:
    max_tokens: int = 700
    overlap_tokens: int = 300
    min_chunk_chars: int = 50

    @classmethod
    def from_env(cls):
        import os

        return cls(
            max_tokens=int(os.getenv("MAX_TOKENS", "700")),
            overlap_tokens=int(os.getenv("OVERLAP_TOKENS", "300")),
            min_chunk_chars=int(os.getenv("MIN_CHUNK_CHARS", "50")),
        )
