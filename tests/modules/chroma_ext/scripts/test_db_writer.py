from unittest.mock import MagicMock, patch

import pytest

from modules.chroma_ext.scripts.data_reader import DocumentChunk
from modules.chroma_ext.scripts.db_writer import (
    _collect_current_sources,
    _group_by_source,
    sync_docx_directory_to_collection,
)


class TestGroupBySource:
    def test_groups_by_source(self):
        chunks = [
            DocumentChunk(id="1", text="a", metadata={"source": "/a.docx"}),
            DocumentChunk(id="2", text="b", metadata={"source": "/a.docx"}),
            DocumentChunk(id="3", text="c", metadata={"source": "/b.docx"}),
        ]
        grouped = _group_by_source(chunks)
        assert len(grouped["/a.docx"]) == 2
        assert len(grouped["/b.docx"]) == 1


class TestCollectCurrentSources:
    def test_collects_docx_paths(self, tmp_path):
        (tmp_path / "a.docx").write_text("x")
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "b.docx").write_text("y")
        result = _collect_current_sources(str(tmp_path))
        assert result == {str(tmp_path / "a.docx"), str(tmp_path / "sub" / "b.docx")}


class TestSyncDocxDirectoryToCollection:
    @patch("modules.chroma_ext.scripts.db_writer.chromadb.HttpClient")
    @patch("modules.chroma_ext.scripts.db_writer.MyEmbeddingFunction")
    @patch("modules.chroma_ext.scripts.db_writer.load_docx_with_metadata")
    def test_no_chunks_early_return(self, mock_load, mock_embed, mock_client):
        mock_load.return_value = []
        logger = MagicMock()
        sync_docx_directory_to_collection(
            logger, "/docs", "test_collection", api_key="k", folder_id="f", host="h", port=8000
        )
        logger.warning.assert_called_once_with("No .docx files found, nothing to index")
        # HttpClient is created before the empty check in current implementation
        mock_client.assert_called_once()

    @patch("modules.chroma_ext.scripts.db_writer.chromadb.HttpClient")
    @patch("modules.chroma_ext.scripts.db_writer.MyEmbeddingFunction")
    @patch("modules.chroma_ext.scripts.db_writer.load_docx_with_metadata")
    def test_unchanged_file_skipped(self, mock_load, mock_embed, mock_client):
        collection = MagicMock()
        collection.get.return_value = {
            "ids": ["old"],
            "metadatas": [{"file_signature": "sig1"}],
        }
        mock_client.return_value.get_or_create_collection.return_value = collection

        chunks = [
            DocumentChunk(
                id="f::chunk:0",
                text="txt",
                metadata={"source": "/f.docx", "file_signature": "sig1"},
            )
        ]
        mock_load.return_value = chunks
        logger = MagicMock()

        sync_docx_directory_to_collection(
            logger, "/docs", "test_collection", api_key="k", folder_id="f", host="h", port=8000
        )
        collection.add.assert_not_called()
        collection.delete.assert_not_called()

    @patch("modules.chroma_ext.scripts.db_writer.chromadb.HttpClient")
    @patch("modules.chroma_ext.scripts.db_writer.MyEmbeddingFunction")
    @patch("modules.chroma_ext.scripts.db_writer.load_docx_with_metadata")
    def test_changed_file_deletes_and_adds(self, mock_load, mock_embed, mock_client):
        collection = MagicMock()
        collection.get.side_effect = [
            {
                "ids": ["old"],
                "metadatas": [{"file_signature": "old_sig"}],
            },
            {"ids": [], "metadatas": []},
        ]
        mock_client.return_value.get_or_create_collection.return_value = collection

        chunks = [
            DocumentChunk(
                id="f::chunk:0",
                text="new text",
                metadata={"source": "/f.docx", "file_signature": "new_sig"},
            )
        ]
        mock_load.return_value = chunks
        logger = MagicMock()

        sync_docx_directory_to_collection(
            logger, "/docs", "test_collection", api_key="k", folder_id="f", host="h", port=8000
        )
        collection.delete.assert_any_call(where={"source": "/f.docx"})
        collection.add.assert_called_once_with(
            ids=["f::chunk:0"],
            documents=["new text"],
            metadatas=[{"source": "/f.docx", "file_signature": "new_sig"}],
        )

    @patch("modules.chroma_ext.scripts.db_writer.chromadb.HttpClient")
    @patch("modules.chroma_ext.scripts.db_writer.MyEmbeddingFunction")
    @patch("modules.chroma_ext.scripts.db_writer.load_docx_with_metadata")
    def test_removes_orphaned_sources(self, mock_load, mock_embed, mock_client, tmp_path):
        collection = MagicMock()
        collection.get.side_effect = [
            {"ids": [], "metadatas": []},
            {
                "ids": ["old"],
                "metadatas": [{"source": str(tmp_path / "gone.docx")}],
            },
        ]
        mock_client.return_value.get_or_create_collection.return_value = collection

        (tmp_path / "keep.docx").write_text("x")
        chunks = [
            DocumentChunk(
                id="keep::chunk:0",
                text="keep",
                metadata={"source": str(tmp_path / "keep.docx"), "file_signature": "sig"},
            )
        ]
        mock_load.return_value = chunks
        logger = MagicMock()

        sync_docx_directory_to_collection(
            logger, str(tmp_path), "test_collection", api_key="k", folder_id="f", host="h", port=8000
        )
        collection.delete.assert_any_call(where={"source": str(tmp_path / "gone.docx")})
