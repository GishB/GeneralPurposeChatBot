from pathlib import Path
from typing import List


class LocalFileReader:
    def read_files(self, directory: Path, pattern: str = "*.md") -> List[Path]:
        if not directory.exists():
            raise FileNotFoundError(f"Директория {directory} не найдена")
        return sorted(directory.rglob(pattern))
