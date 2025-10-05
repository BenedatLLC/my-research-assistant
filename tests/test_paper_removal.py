"""Tests for paper removal functionality."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from my_research_assistant.paper_removal import (
    remove_paper_from_indexes,
    find_matching_papers,
    remove_paper
)
from my_research_assistant.file_locations import FileLocations
from my_research_assistant.project_types import PaperMetadata


@pytest.fixture
def temp_file_locations(tmp_path):
    """Create temporary file locations for testing."""
    doc_home = tmp_path / "docs"
    doc_home.mkdir()

    # Create all subdirectories
    (doc_home / "pdfs").mkdir()
    (doc_home / "paper_metadata").mkdir()
    (doc_home / "extracted_paper_text").mkdir()
    (doc_home / "summaries").mkdir()
    (doc_home / "notes").mkdir()
    (doc_home / "index").mkdir()
    (doc_home / "results").mkdir()

    file_locations = FileLocations(
        doc_home=str(doc_home),
        index_dir=str(doc_home / "index"),
        summaries_dir=str(doc_home / "summaries"),
        images_dir=str(doc_home / "summaries" / "images"),
        pdfs_dir=str(doc_home / "pdfs"),
        extracted_paper_text_dir=str(doc_home / "extracted_paper_text"),
        notes_dir=str(doc_home / "notes"),
        results_dir=str(doc_home / "results"),
        paper_metadata_dir=str(doc_home / "paper_metadata")
    )

    return file_locations


@pytest.fixture
def sample_paper_metadata():
    """Create sample paper metadata for testing."""
    return PaperMetadata(
        paper_id="2107.03374v2",
        title="Test Paper Title",
        authors=["Author One", "Author Two"],
        published=datetime(2021, 7, 7),
        updated=datetime(2021, 7, 7),
        abstract="Test abstract",
        categories=["cs.AI", "cs.LG"],
        paper_pdf_url="https://arxiv.org/pdf/2107.03374v2.pdf",
        paper_abs_url="https://arxiv.org/abs/2107.03374v2",
        doi=None,
        journal_ref=None
    )


class TestRemovePaperFromIndexes:
    """Tests for remove_paper_from_indexes function."""

    def test_remove_from_nonexistent_indexes(self, temp_file_locations):
        """Test removing from indexes when they don't exist."""
        content_chunks, summary_chunks = remove_paper_from_indexes(
            "2107.03374v2",
            temp_file_locations
        )

        assert content_chunks == 0
        assert summary_chunks == 0

    @patch('my_research_assistant.paper_removal.chromadb.PersistentClient')
    def test_remove_from_content_index(self, mock_chroma_client, temp_file_locations):
        """Test removing chunks from content index."""
        # Create the index directory
        content_db_path = os.path.join(temp_file_locations.index_dir, "content_chroma_db")
        os.makedirs(content_db_path)

        # Mock the ChromaDB client and collection
        mock_client_instance = MagicMock()
        mock_collection = MagicMock()
        mock_collection.get.return_value = {'ids': ['id1', 'id2', 'id3']}

        mock_client_instance.get_collection.return_value = mock_collection
        mock_chroma_client.return_value = mock_client_instance

        content_chunks, summary_chunks = remove_paper_from_indexes(
            "2107.03374v2",
            temp_file_locations
        )

        assert content_chunks == 3
        assert summary_chunks == 0
        mock_collection.delete.assert_called_once_with(where={"paper_id": "2107.03374v2"})

    @patch('my_research_assistant.paper_removal.chromadb.PersistentClient')
    def test_remove_from_both_indexes(self, mock_chroma_client, temp_file_locations):
        """Test removing chunks from both content and summary indexes."""
        # Create both index directories
        content_db_path = os.path.join(temp_file_locations.index_dir, "content_chroma_db")
        summary_db_path = os.path.join(temp_file_locations.index_dir, "summary_chroma_db")
        os.makedirs(content_db_path)
        os.makedirs(summary_db_path)

        # Mock the ChromaDB client and collections
        mock_client_instance = MagicMock()
        mock_content_collection = MagicMock()
        mock_summary_collection = MagicMock()

        mock_content_collection.get.return_value = {'ids': ['c1', 'c2']}
        mock_summary_collection.get.return_value = {'ids': ['s1']}

        def get_collection(name):
            if name == "content_index":
                return mock_content_collection
            elif name == "summary_index":
                return mock_summary_collection

        mock_client_instance.get_collection.side_effect = get_collection
        mock_chroma_client.return_value = mock_client_instance

        content_chunks, summary_chunks = remove_paper_from_indexes(
            "2107.03374v2",
            temp_file_locations
        )

        assert content_chunks == 2
        assert summary_chunks == 1
        mock_content_collection.delete.assert_called_once_with(where={"paper_id": "2107.03374v2"})
        mock_summary_collection.delete.assert_called_once_with(where={"paper_id": "2107.03374v2"})

    @patch('my_research_assistant.paper_removal.chromadb.PersistentClient')
    def test_remove_handles_collection_errors(self, mock_chroma_client, temp_file_locations, capsys):
        """Test that errors accessing collections are handled gracefully."""
        # Create the index directory
        content_db_path = os.path.join(temp_file_locations.index_dir, "content_chroma_db")
        os.makedirs(content_db_path)

        # Mock the ChromaDB client to raise an error
        mock_client_instance = MagicMock()
        mock_client_instance.get_collection.side_effect = Exception("Collection not found")
        mock_chroma_client.return_value = mock_client_instance

        content_chunks, summary_chunks = remove_paper_from_indexes(
            "2107.03374v2",
            temp_file_locations
        )

        # Should return 0 for both and not crash
        assert content_chunks == 0
        assert summary_chunks == 0

        # Check that error message was printed
        captured = capsys.readouterr()
        assert "Could not access content index" in captured.out


class TestFindMatchingPapers:
    """Tests for find_matching_papers function."""

    @patch('my_research_assistant.paper_removal.get_downloaded_paper_ids')
    def test_exact_match(self, mock_get_papers, temp_file_locations):
        """Test finding exact paper ID match."""
        mock_get_papers.return_value = ["2107.03374v1", "2107.03374v2", "2108.12345v1"]

        matches = find_matching_papers("2107.03374v2", temp_file_locations)

        assert len(matches) == 1
        assert matches[0] == "2107.03374v2"

    @patch('my_research_assistant.paper_removal.get_downloaded_paper_ids')
    def test_prefix_match_multiple_versions(self, mock_get_papers, temp_file_locations):
        """Test finding multiple versions of a paper."""
        mock_get_papers.return_value = ["2107.03374v1", "2107.03374v2", "2108.12345v1"]

        matches = find_matching_papers("2107.03374", temp_file_locations)

        assert len(matches) == 2
        assert "2107.03374v1" in matches
        assert "2107.03374v2" in matches

    @patch('my_research_assistant.paper_removal.get_downloaded_paper_ids')
    def test_no_match(self, mock_get_papers, temp_file_locations):
        """Test when no papers match."""
        mock_get_papers.return_value = ["2107.03374v1", "2108.12345v1"]

        matches = find_matching_papers("2109.99999", temp_file_locations)

        assert len(matches) == 0

    @patch('my_research_assistant.paper_removal.get_downloaded_paper_ids')
    def test_single_version_match(self, mock_get_papers, temp_file_locations):
        """Test finding single version when using prefix."""
        mock_get_papers.return_value = ["2107.03374v1", "2108.12345v1"]

        matches = find_matching_papers("2108.12345", temp_file_locations)

        assert len(matches) == 1
        assert matches[0] == "2108.12345v1"


class TestRemovePaper:
    """Tests for remove_paper function."""

    def create_paper_files(self, file_locations, paper_id):
        """Helper to create all paper files."""
        # Create PDF
        pdf_path = os.path.join(file_locations.pdfs_dir, f"{paper_id}.pdf")
        with open(pdf_path, 'w') as f:
            f.write("fake pdf content")

        # Create metadata
        metadata_path = os.path.join(file_locations.paper_metadata_dir, f"{paper_id}.json")
        with open(metadata_path, 'w') as f:
            f.write('{"paper_id": "' + paper_id + '"}')

        # Create extracted text
        text_path = os.path.join(file_locations.extracted_paper_text_dir, f"{paper_id}.md")
        with open(text_path, 'w') as f:
            f.write("# Extracted text")

        # Create summary
        summary_path = os.path.join(file_locations.summaries_dir, f"{paper_id}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary")

        # Create notes
        notes_path = os.path.join(file_locations.notes_dir, f"{paper_id}.md")
        with open(notes_path, 'w') as f:
            f.write("# Notes")

    @patch('my_research_assistant.paper_removal.remove_paper_from_indexes')
    @patch('my_research_assistant.paper_removal.get_paper_metadata')
    @patch('my_research_assistant.paper_removal.find_matching_papers')
    def test_remove_paper_not_found(self, mock_find, mock_get_metadata, mock_remove_indexes, temp_file_locations):
        """Test removing a paper that doesn't exist."""
        mock_find.return_value = []

        success, message = remove_paper("2109.99999v1", temp_file_locations)

        assert not success
        assert "not found" in message
        mock_get_metadata.assert_not_called()
        mock_remove_indexes.assert_not_called()

    @patch('my_research_assistant.paper_removal.remove_paper_from_indexes')
    @patch('my_research_assistant.paper_removal.get_paper_metadata')
    @patch('my_research_assistant.paper_removal.find_matching_papers')
    def test_remove_paper_ambiguous(self, mock_find, mock_get_metadata, mock_remove_indexes, temp_file_locations):
        """Test removing a paper with ambiguous version."""
        mock_find.return_value = ["2107.03374v1", "2107.03374v2"]

        success, message = remove_paper("2107.03374", temp_file_locations)

        assert not success
        assert "Ambiguous removal request" in message
        assert "2107.03374v1 and 2107.03374v2" in message
        mock_get_metadata.assert_not_called()
        mock_remove_indexes.assert_not_called()

    @patch('my_research_assistant.paper_removal.remove_paper_from_indexes')
    @patch('my_research_assistant.paper_removal.get_paper_metadata')
    @patch('my_research_assistant.paper_removal.find_matching_papers')
    def test_remove_paper_cancelled(self, mock_find, mock_get_metadata, mock_remove_indexes,
                                   temp_file_locations, sample_paper_metadata):
        """Test removing a paper when user cancels."""
        mock_find.return_value = ["2107.03374v2"]
        mock_get_metadata.return_value = sample_paper_metadata

        # Mock confirmation callback to return False (cancel)
        def cancel_callback(paper_metadata):
            return False

        success, message = remove_paper(
            "2107.03374v2",
            temp_file_locations,
            confirm_callback=cancel_callback
        )

        assert not success
        assert "cancelled" in message.lower()
        mock_remove_indexes.assert_not_called()

    @patch('my_research_assistant.paper_removal.remove_paper_from_indexes')
    @patch('my_research_assistant.paper_removal.get_paper_metadata')
    @patch('my_research_assistant.paper_removal.find_matching_papers')
    def test_remove_paper_complete_success(self, mock_find, mock_get_metadata, mock_remove_indexes,
                                          temp_file_locations, sample_paper_metadata):
        """Test complete successful removal of all paper files."""
        paper_id = "2107.03374v2"
        mock_find.return_value = [paper_id]
        mock_get_metadata.return_value = sample_paper_metadata
        mock_remove_indexes.return_value = (22, 1)  # chunks removed

        # Create all paper files
        self.create_paper_files(temp_file_locations, paper_id)

        # Mock confirmation callbacks to return True
        def confirm_callback(paper_metadata):
            return True

        def notes_confirm_callback(notes_path):
            return True

        success, message = remove_paper(
            paper_id,
            temp_file_locations,
            confirm_callback=confirm_callback,
            notes_confirm_callback=notes_confirm_callback
        )

        assert success
        assert "completed successfully" in message
        assert "22 chunks from the content index" in message
        assert "1 chunks from the summary index" in message

        # Verify files were deleted
        assert not os.path.exists(os.path.join(temp_file_locations.pdfs_dir, f"{paper_id}.pdf"))
        assert not os.path.exists(os.path.join(temp_file_locations.extracted_paper_text_dir, f"{paper_id}.md"))
        assert not os.path.exists(os.path.join(temp_file_locations.summaries_dir, f"{paper_id}.md"))
        assert not os.path.exists(os.path.join(temp_file_locations.notes_dir, f"{paper_id}.md"))
        assert not os.path.exists(os.path.join(temp_file_locations.paper_metadata_dir, f"{paper_id}.json"))

    @patch('my_research_assistant.paper_removal.remove_paper_from_indexes')
    @patch('my_research_assistant.paper_removal.get_paper_metadata')
    @patch('my_research_assistant.paper_removal.find_matching_papers')
    def test_remove_paper_partial_files(self, mock_find, mock_get_metadata, mock_remove_indexes,
                                       temp_file_locations, sample_paper_metadata):
        """Test removal when only some files exist."""
        paper_id = "2107.03374v2"
        mock_find.return_value = [paper_id]
        mock_get_metadata.return_value = sample_paper_metadata
        mock_remove_indexes.return_value = (5, 0)

        # Create only PDF and summary
        pdf_path = os.path.join(temp_file_locations.pdfs_dir, f"{paper_id}.pdf")
        with open(pdf_path, 'w') as f:
            f.write("fake pdf content")

        summary_path = os.path.join(temp_file_locations.summaries_dir, f"{paper_id}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary")

        # Mock confirmation callback
        def confirm_callback(paper_metadata):
            return True

        success, message = remove_paper(
            paper_id,
            temp_file_locations,
            confirm_callback=confirm_callback
        )

        assert success
        assert "completed successfully" in message
        assert "Removed downloaded paper" in message
        assert "Removed summary" in message
        assert "No extracted paper text found" in message
        assert "No paper notes found" in message

    @patch('my_research_assistant.paper_removal.remove_paper_from_indexes')
    @patch('my_research_assistant.paper_removal.get_paper_metadata')
    @patch('my_research_assistant.paper_removal.find_matching_papers')
    def test_remove_paper_notes_declined(self, mock_find, mock_get_metadata, mock_remove_indexes,
                                        temp_file_locations, sample_paper_metadata):
        """Test removal when user declines to delete notes."""
        paper_id = "2107.03374v2"
        mock_find.return_value = [paper_id]
        mock_get_metadata.return_value = sample_paper_metadata
        mock_remove_indexes.return_value = (0, 0)

        # Create notes file
        notes_path = os.path.join(temp_file_locations.notes_dir, f"{paper_id}.md")
        with open(notes_path, 'w') as f:
            f.write("# My important notes")

        # Mock confirmation callbacks
        def confirm_callback(paper_metadata):
            return True

        def notes_confirm_callback(notes_path):
            return False  # Decline to delete notes

        success, message = remove_paper(
            paper_id,
            temp_file_locations,
            confirm_callback=confirm_callback,
            notes_confirm_callback=notes_confirm_callback
        )

        assert success
        assert "completed successfully" in message
        assert "Kept notes file" in message
        assert "user chose not to delete" in message

        # Verify notes file still exists
        assert os.path.exists(notes_path)
