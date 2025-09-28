"""Tests for paper argument parsing functionality.

This module tests the parse_paper_argument function and related utilities
according to the design specified in designs/command-arguments.md.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from my_research_assistant.paper_manager import (
    parse_paper_argument,
    is_arxiv_id_format,
    find_downloaded_papers_by_base_id,
    get_all_downloaded_papers
)
from my_research_assistant.file_locations import FileLocations
from my_research_assistant.project_types import PaperMetadata


class TestArxivIdFormat:
    """Test ArXiv ID format validation."""

    def test_valid_arxiv_ids(self):
        """Test that valid ArXiv IDs are recognized."""
        valid_ids = [
            "2107.03374",
            "2107.03374v1",
            "2107.03374v2",
            "1234.56789",
            "1234.56789v10",
            "2023.12345",
            "2023.12345v1"
        ]
        for arxiv_id in valid_ids:
            assert is_arxiv_id_format(arxiv_id), f"Should recognize {arxiv_id} as valid ArXiv ID"

    def test_invalid_arxiv_ids(self):
        """Test that invalid formats are not recognized as ArXiv IDs."""
        invalid_ids = [
            "123",
            "abc.def",
            "2107.123",  # Too few digits after dot
            "2107.1234567",  # Too many digits after dot
            "21.12345",  # Too few digits before dot
            "21070.12345",  # Too many digits before dot
            "2107.12345v",  # Version without number
            "2107.12345va",  # Invalid version format
            "",
            "  ",
            "not-an-id"
        ]
        for invalid_id in invalid_ids:
            assert not is_arxiv_id_format(invalid_id), f"Should not recognize {invalid_id} as valid ArXiv ID"


class TestFindDownloadedPapers:
    """Test finding downloaded papers by base ID."""

    def test_find_papers_with_versions(self):
        """Test finding papers when multiple versions exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(pdfs_dir)

            # Create mock PDF files
            test_files = ["2107.03374v1.pdf", "2107.03374v2.pdf", "2210.12345v1.pdf"]
            for filename in test_files:
                with open(os.path.join(pdfs_dir, filename), 'w') as f:
                    f.write("mock pdf")

            file_locations = FileLocations(
                doc_home=tmpdir,
                index_dir=os.path.join(tmpdir, "index"),
                summaries_dir=os.path.join(tmpdir, "summaries"),
                images_dir=os.path.join(tmpdir, "images"),
                pdfs_dir=pdfs_dir,
                extracted_paper_text_dir=os.path.join(tmpdir, "extracted"),
                notes_dir=os.path.join(tmpdir, "notes"),
                results_dir=os.path.join(tmpdir, "results"),
                paper_metadata_dir=os.path.join(tmpdir, "metadata")
            )

            # Test finding papers for base ID with multiple versions
            result = find_downloaded_papers_by_base_id("2107.03374", file_locations)
            assert set(result) == {"2107.03374v1", "2107.03374v2"}

            # Test finding papers for base ID with single version
            result = find_downloaded_papers_by_base_id("2210.12345", file_locations)
            assert result == ["2210.12345v1"]

            # Test finding papers for non-existent base ID
            result = find_downloaded_papers_by_base_id("9999.99999", file_locations)
            assert result == []

    def test_find_papers_no_pdfs_dir(self):
        """Test behavior when PDFs directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_locations = FileLocations(
                doc_home=tmpdir,
                index_dir=os.path.join(tmpdir, "index"),
                summaries_dir=os.path.join(tmpdir, "summaries"),
                images_dir=os.path.join(tmpdir, "images"),
                pdfs_dir=os.path.join(tmpdir, "nonexistent"),
                extracted_paper_text_dir=os.path.join(tmpdir, "extracted"),
                notes_dir=os.path.join(tmpdir, "notes"),
                results_dir=os.path.join(tmpdir, "results"),
                paper_metadata_dir=os.path.join(tmpdir, "metadata")
            )

            result = find_downloaded_papers_by_base_id("2107.03374", file_locations)
            assert result == []


class TestParsePaperArgument:
    """Test the main parse_paper_argument function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp()
        self.pdfs_dir = os.path.join(self.tmpdir, "pdfs")
        os.makedirs(self.pdfs_dir)

        self.file_locations = FileLocations(
            doc_home=self.tmpdir,
            index_dir=os.path.join(self.tmpdir, "index"),
            summaries_dir=os.path.join(self.tmpdir, "summaries"),
            images_dir=os.path.join(self.tmpdir, "images"),
            pdfs_dir=self.pdfs_dir,
            extracted_paper_text_dir=os.path.join(self.tmpdir, "extracted"),
            notes_dir=os.path.join(self.tmpdir, "notes"),
            results_dir=os.path.join(self.tmpdir, "results"),
            paper_metadata_dir=os.path.join(self.tmpdir, "metadata")
        )

        # Create mock PDF files
        test_files = ["2107.03374v1.pdf", "2107.03374v2.pdf", "2210.12345v1.pdf"]
        for filename in test_files:
            with open(os.path.join(self.pdfs_dir, filename), 'w') as f:
                f.write("mock pdf")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_empty_argument(self):
        """Test error handling for empty argument."""
        paper, error = parse_paper_argument("test", "", [], self.file_locations)
        assert paper is None
        assert "Please provide a paper number or ID" in error
        assert "test failed" in error

    def test_multiple_arguments(self):
        """Test error handling for multiple arguments."""
        paper, error = parse_paper_argument("test", "arg1 arg2", [], self.file_locations)
        assert paper is None
        assert "exactly one paper number or ID" in error
        assert "test failed" in error

    def test_integer_with_empty_query_set(self):
        """Test integer argument when last_query_set is empty."""
        paper, error = parse_paper_argument("test", "1", [], self.file_locations)
        assert paper is None
        assert "No papers in current list" in error
        assert "test failed" in error

    def test_integer_out_of_range(self):
        """Test integer argument that's out of range."""
        last_query_set = ["2107.03374v1", "2210.12345v1"]

        # Test below range
        paper, error = parse_paper_argument("test", "0", last_query_set, self.file_locations)
        assert paper is None
        assert "Invalid paper number '0'" in error
        assert "Choose 1-2" in error

        # Test above range
        paper, error = parse_paper_argument("test", "3", last_query_set, self.file_locations)
        assert paper is None
        assert "Invalid paper number '3'" in error
        assert "Choose 1-2" in error

    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_valid_integer_argument(self, mock_get_metadata):
        """Test valid integer argument."""
        # Mock the metadata function
        mock_paper = MagicMock()
        mock_paper.paper_id = "2107.03374v1"
        mock_paper.get_local_pdf_path.return_value = os.path.join(self.pdfs_dir, "2107.03374v1.pdf")
        mock_get_metadata.return_value = mock_paper

        last_query_set = ["2107.03374v1", "2210.12345v1"]

        paper, error = parse_paper_argument("test", "1", last_query_set, self.file_locations)
        assert paper is not None
        assert error == ""
        assert paper.paper_id == "2107.03374v1"

    def test_invalid_format(self):
        """Test argument that's neither integer nor ArXiv ID."""
        paper, error = parse_paper_argument("test", "invalid-format", [], self.file_locations)
        assert paper is None
        assert "not a valid paper number or ArXiv ID" in error
        assert "test failed" in error

    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_arxiv_id_with_version(self, mock_get_metadata):
        """Test ArXiv ID with specific version."""
        # Mock the metadata function
        mock_paper = MagicMock()
        mock_paper.paper_id = "2107.03374v1"
        mock_paper.get_local_pdf_path.return_value = os.path.join(self.pdfs_dir, "2107.03374v1.pdf")
        mock_get_metadata.return_value = mock_paper

        paper, error = parse_paper_argument("test", "2107.03374v1", [], self.file_locations)
        assert paper is not None
        assert error == ""
        assert paper.paper_id == "2107.03374v1"

    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_arxiv_id_without_version_single_match(self, mock_get_metadata):
        """Test ArXiv ID without version when only one version exists."""
        # Remove one of the test files to have only one version
        os.remove(os.path.join(self.pdfs_dir, "2107.03374v2.pdf"))

        # Mock the metadata function
        mock_paper = MagicMock()
        mock_paper.paper_id = "2107.03374v1"
        mock_paper.get_local_pdf_path.return_value = os.path.join(self.pdfs_dir, "2107.03374v1.pdf")
        mock_get_metadata.return_value = mock_paper

        paper, error = parse_paper_argument("test", "2107.03374", [], self.file_locations)
        assert paper is not None
        assert error == ""
        assert paper.paper_id == "2107.03374v1"

    def test_arxiv_id_without_version_multiple_matches(self):
        """Test ArXiv ID without version when multiple versions exist."""
        paper, error = parse_paper_argument("test", "2107.03374", [], self.file_locations)
        assert paper is None
        assert "Multiple versions found for 2107.03374" in error
        assert "2107.03374v1, 2107.03374v2" in error
        assert "Please specify version" in error
        assert "test failed" in error

    def test_arxiv_id_not_downloaded(self):
        """Test ArXiv ID that hasn't been downloaded."""
        paper, error = parse_paper_argument("test", "9999.99999", [], self.file_locations)
        assert paper is None
        assert "Paper 9999.99999 has not been downloaded" in error
        assert "test failed" in error

    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_arxiv_id_pdf_missing(self, mock_get_metadata):
        """Test ArXiv ID where metadata exists but PDF is missing."""
        # Mock the metadata function
        mock_paper = MagicMock()
        mock_paper.paper_id = "2107.03374v1"
        mock_paper.get_local_pdf_path.return_value = os.path.join(self.pdfs_dir, "nonexistent.pdf")
        mock_get_metadata.return_value = mock_paper

        paper, error = parse_paper_argument("test", "2107.03374v1", [], self.file_locations)
        assert paper is None
        assert "PDF not found" in error
        assert "test failed" in error

    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_metadata_loading_error(self, mock_get_metadata):
        """Test error handling when metadata loading fails."""
        mock_get_metadata.side_effect = Exception("Metadata error")

        paper, error = parse_paper_argument("test", "2107.03374v1", [], self.file_locations)
        assert paper is None
        assert "Error loading paper 2107.03374v1" in error
        assert "test failed" in error

    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_metadata_returns_none(self, mock_get_metadata):
        """Test error handling when get_paper_metadata returns None."""
        mock_get_metadata.return_value = None

        paper, error = parse_paper_argument("test", "2107.03374v1", [], self.file_locations)
        assert paper is None
        assert "Could not load metadata for paper 2107.03374v1" in error
        assert "test failed" in error


if __name__ == "__main__":
    pytest.main([__file__])