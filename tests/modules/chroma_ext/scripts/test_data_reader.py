from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.chroma_ext.scripts.data_reader import (
    DocumentChunk,
    _build_topic_prefix,
    _calc_signature,
    _read_docx,
    _split_into_chunks,
    load_docx_with_metadata,
)


class TestReadDocx:
    @patch("modules.chroma_ext.scripts.data_reader.docx2txt.process")
    def test_returns_stripped_text(self, mock_process):
        mock_process.return_value = "  hello world  \n\n"
        result = _read_docx(Path("/fake/doc.docx"))
        assert result == "hello world"

    @patch("modules.chroma_ext.scripts.data_reader.docx2txt.process")
    def test_returns_empty_when_none(self, mock_process):
        mock_process.return_value = None
        assert _read_docx(Path("/fake/doc.docx")) == ""


class TestSplitIntoChunks:
    def test_empty_text(self):
        assert _split_into_chunks("") == []

    def test_exact_size_no_overlap(self):
        text = "a" * 10
        chunks = _split_into_chunks(text, chunk_size=5, chunk_overlap=0)
        assert chunks == ["a" * 5, "a" * 5]

    def test_overlap(self):
        text = "a" * 10
        chunks = _split_into_chunks(text, chunk_size=6, chunk_overlap=2)
        assert chunks == ["a" * 6, "a" * 6]

    def test_single_chunk_when_text_shorter(self):
        text = "short"
        chunks = _split_into_chunks(text, chunk_size=100, chunk_overlap=10)
        assert chunks == ["short"]


class TestCalcSignature:
    def test_deterministic(self):
        assert _calc_signature("hello") == _calc_signature("hello")
        assert _calc_signature("hello") != _calc_signature("world")


class TestBuildTopicPrefix:
    def test_empty(self):
        assert _build_topic_prefix("") == ""

    def test_truncates_to_max_tokens(self):
        text = "one two three four five"
        assert _build_topic_prefix(text, max_tokens=3) == "one two three"

    def test_full_when_short(self):
        text = "one two"
        assert _build_topic_prefix(text, max_tokens=10) == "one two"


class TestLoadDocxWithMetadata:
    @patch("modules.chroma_ext.scripts.data_reader.docx2txt.process")
    def test_skips_empty_files(self, mock_process, tmp_path):
        mock_process.return_value = ""
        (tmp_path / "empty.docx").write_text("fake")
        logger = MagicMock()
        result = load_docx_with_metadata(logger, tmp_path)
        assert result == []

    @patch("modules.chroma_ext.scripts.data_reader.docx2txt.process")
    def test_loads_single_file_with_topic_prefix(self, mock_process, tmp_path):
        text = "Title of document. " + "body " * 200
        mock_process.return_value = text
        (tmp_path / "contract.docx").write_text("fake")
        logger = MagicMock()
        result = load_docx_with_metadata(logger, tmp_path, chunk_size=50, chunk_overlap=10, topic_tokens=5)

        assert len(result) >= 1
        chunk = result[0]
        assert isinstance(chunk, DocumentChunk)
        assert chunk.id == "contract.docx::chunk:0"
        assert chunk.metadata["filename"] == "contract.docx"
        assert chunk.metadata["topic"] == "general"
        assert "Title of" in chunk.text
        assert chunk.metadata["file_signature"] == _calc_signature(text.strip())

    @patch("modules.chroma_ext.scripts.data_reader.docx2txt.process")
    def test_nested_directory_topic(self, mock_process, tmp_path):
        text = "some content here"
        mock_process.return_value = text
        nested = tmp_path / "hr"
        nested.mkdir()
        (nested / "rules.docx").write_text("fake")
        logger = MagicMock()
        result = load_docx_with_metadata(logger, tmp_path)
        assert len(result) == 1
        assert result[0].metadata["topic"] == "hr"
        assert result[0].id == "hr/rules.docx::chunk:0"

    @patch("modules.chroma_ext.scripts.data_reader.docx2txt.process")
    def test_multiple_chunks(self, mock_process, tmp_path):
        text = "a" * 100
        mock_process.return_value = text
        (tmp_path / "long.docx").write_text("fake")
        logger = MagicMock()
        result = load_docx_with_metadata(logger, tmp_path, chunk_size=30, chunk_overlap=5)
        assert len(result) > 1
        for idx, chunk in enumerate(result):
            assert chunk.metadata["chunk_index"] == idx
            assert chunk.metadata["num_chunks"] == len(result)
