"""Comprehensive tests for rebuild_index and main() function in vector_store.py"""

import os
import sys
import pytest
import tempfile
from os.path import join
from unittest.mock import patch, MagicMock
from my_research_assistant import file_locations
from my_research_assistant.project_types import PaperMetadata

EXAMPLE_PAPER_ID = '2503.22738'
EXAMPLE_PAPER_ID_2 = '2503.00237'


def create_mock_metadata(paper_id: str) -> PaperMetadata:
    """Create a mock PaperMetadata object for testing."""
    import datetime
    return PaperMetadata(
        paper_id=paper_id,
        title=f"Test Paper {paper_id}",
        published=datetime.datetime(2025, 3, 1),
        updated=None,
        paper_abs_url=f"http://arxiv.org/abs/{paper_id}",
        paper_pdf_url=f"http://arxiv.org/pdf/{paper_id}.pdf",
        authors=["Test Author"],
        categories=["cs.AI"],
        abstract="Test abstract for paper.",
        doi=None,
        journal_ref=None
    )


def create_test_pdf(file_locations, paper_id: str):
    """Create a minimal test PDF file."""
    file_locations.ensure_pdfs_dir()
    pdf_path = join(file_locations.pdfs_dir, f"{paper_id}.pdf")
    # Create a minimal valid PDF
    with open(pdf_path, 'wb') as f:
        f.write(b'%PDF-1.4\n')
        f.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
        f.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
        f.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n')
        f.write(b'4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 100 Td (Test content) Tj ET\nendstream\nendobj\n')
        f.write(b'xref\n0 5\n')
        f.write(b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n')
    return pdf_path


def create_test_metadata_file(file_locations, paper_id: str):
    """Create a test metadata JSON file."""
    import json
    file_locations.ensure_paper_metadata_dir()
    metadata_path = join(file_locations.paper_metadata_dir, f"{paper_id}.json")
    metadata = {
        "paper_id": paper_id,
        "title": f"Test Paper {paper_id}",
        "published": "2025-03-01T00:00:00",
        "updated": None,
        "paper_abs_url": f"http://arxiv.org/abs/{paper_id}",
        "paper_pdf_url": f"http://arxiv.org/pdf/{paper_id}.pdf",
        "authors": ["Test Author"],
        "categories": ["cs.AI"],
        "abstract": "Test abstract",
        "doi": None,
        "journal_ref": None
    }
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    return metadata_path


@pytest.fixture
def temp_file_locations():
    """Create a temporary directory and set FILE_LOCATIONS to use it."""
    original_file_locations = file_locations.FILE_LOCATIONS

    import my_research_assistant.vector_store as vs
    original_content_index = vs.CONTENT_INDEX
    original_summary_index = vs.SUMMARY_INDEX
    original_vs_file_locations = vs.FILE_LOCATIONS

    with tempfile.TemporaryDirectory() as temp_dir:
        prompts_dir = os.path.join(temp_dir, 'prompts')
        os.makedirs(prompts_dir, exist_ok=True)

        temp_locations = file_locations.FileLocations.get_locations(temp_dir)
        file_locations.FILE_LOCATIONS = temp_locations

        # Clear ChromaDB shared system state before resetting indexes
        try:
            import chromadb.api.shared_system_client as shared_system
            if hasattr(shared_system.SharedSystemClient, '_identifier_to_system'):
                # Properly shut down any existing systems before clearing
                for system in list(shared_system.SharedSystemClient._identifier_to_system.values()):
                    try:
                        system.stop()
                    except Exception:
                        pass
                shared_system.SharedSystemClient._identifier_to_system.clear()
        except Exception:
            pass  # Ignore if ChromaDB internals changed

        vs.CONTENT_INDEX = None
        vs.SUMMARY_INDEX = None

        try:
            yield temp_locations
        finally:
            # Clean up ChromaDB state before restoring
            vs.CONTENT_INDEX = None
            vs.SUMMARY_INDEX = None

            try:
                import chromadb.api.shared_system_client as shared_system
                if hasattr(shared_system.SharedSystemClient, '_identifier_to_system'):
                    # Properly shut down any existing systems before clearing
                    for system in list(shared_system.SharedSystemClient._identifier_to_system.values()):
                        try:
                            system.stop()
                        except Exception:
                            pass
                    shared_system.SharedSystemClient._identifier_to_system.clear()
            except Exception:
                pass

            file_locations.FILE_LOCATIONS = original_file_locations
            vs.CONTENT_INDEX = original_content_index
            vs.SUMMARY_INDEX = original_summary_index
            vs.FILE_LOCATIONS = original_vs_file_locations


@pytest.fixture
def mock_indexing():
    """Mock expensive indexing operations to speed up tests."""
    with patch('my_research_assistant.vector_store.index_file_using_pymupdf_parser') as mock_index_file, \
         patch('my_research_assistant.vector_store.index_summary') as mock_index_summary, \
         patch('my_research_assistant.vector_store.index_notes') as mock_index_notes:

        # Make mocks succeed by default
        mock_index_file.return_value = None
        mock_index_summary.return_value = None
        mock_index_notes.return_value = None

        yield {
            'index_file': mock_index_file,
            'index_summary': mock_index_summary,
            'index_notes': mock_index_notes
        }


class TestRebuildIndexComprehensive:
    """Comprehensive tests for rebuild_index function."""

    def test_rebuild_index_with_all_content_types(self, temp_file_locations, mock_indexing):
        """Test rebuild_index with PDFs, summaries, and notes."""
        import my_research_assistant.vector_store as vs
        from my_research_assistant.arxiv_downloader import get_paper_metadata

        vs.FILE_LOCATIONS = temp_file_locations

        # Create test paper and metadata
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)

        # Create summary
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\nThis paper discusses agent safety mechanisms.")

        # Create notes
        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(notes_path, 'w') as f:
            f.write("# My Notes\nInteresting approach to verifiable safety.")

        # Mock get_paper_metadata to return test metadata
        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = create_mock_metadata(EXAMPLE_PAPER_ID)

            # Run rebuild_index
            vs.rebuild_index(temp_file_locations)

            # Verify all three types were indexed
            assert vs.CONTENT_INDEX is not None
            assert vs.SUMMARY_INDEX is not None

            # Verify mocks were called
            assert mock_indexing['index_file'].call_count == 1
            assert mock_indexing['index_summary'].call_count == 1
            assert mock_indexing['index_notes'].call_count == 1

    def test_rebuild_index_only_pdfs(self, temp_file_locations, mock_indexing):
        """Test rebuild_index with only PDFs (no summaries or notes)."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create test paper (no summary or notes)
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)

        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = create_mock_metadata(EXAMPLE_PAPER_ID)

            vs.rebuild_index(temp_file_locations)

            # Should succeed with just PDF
            assert vs.CONTENT_INDEX is not None

            # Should only index PDF content, not summary or notes
            assert mock_indexing['index_file'].call_count == 1
            assert mock_indexing['index_summary'].call_count == 0
            assert mock_indexing['index_notes'].call_count == 0

    def test_rebuild_index_clears_old_index(self, temp_file_locations, mock_indexing):
        """Test that rebuild_index clears old index data."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create test paper
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)

        # Create initial index
        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = create_mock_metadata(EXAMPLE_PAPER_ID)

            # First rebuild
            vs.rebuild_index(temp_file_locations)
            first_content_index = vs.CONTENT_INDEX

            # Rebuild again (should clear and recreate)
            vs.rebuild_index(temp_file_locations)
            second_content_index = vs.CONTENT_INDEX

            # Indexes should be different objects (cleared and recreated)
            assert second_content_index is not first_content_index

    def test_rebuild_index_no_papers(self, temp_file_locations):
        """Test rebuild_index with no downloaded papers."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # No papers downloaded
        with pytest.raises(vs.IndexError) as exc_info:
            vs.rebuild_index(temp_file_locations)

        assert "No papers were reindexed" in str(exc_info.value)

    def test_rebuild_index_handles_missing_metadata(self, temp_file_locations, mock_indexing):
        """Test rebuild_index handles papers with missing metadata gracefully."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create a real paper with metadata
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)

        # Create a fake paper file without metadata
        fake_paper_id = "9999.99999v1"
        create_test_pdf(temp_file_locations, fake_paper_id)
        # Don't create metadata for this one

        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            # Return metadata for real paper, raise exception for fake
            def get_metadata_side_effect(paper_id):
                if paper_id == EXAMPLE_PAPER_ID:
                    return create_mock_metadata(paper_id)
                else:
                    raise Exception(f"No metadata for {paper_id}")

            mock_get_metadata.side_effect = get_metadata_side_effect

            # rebuild_index should handle the missing metadata gracefully
            vs.rebuild_index(temp_file_locations)

            # Should have indexed the real paper
            assert vs.CONTENT_INDEX is not None
            assert mock_indexing['index_file'].call_count == 1

    def test_rebuild_index_handles_indexing_failures(self, temp_file_locations, capsys):
        """Test rebuild_index handles indexing failures gracefully."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create two test papers
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID_2)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID_2)

        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata, \
             patch('my_research_assistant.vector_store.index_file_using_pymupdf_parser') as mock_index_file:

            # First paper returns metadata, second paper also returns metadata
            mock_get_metadata.side_effect = lambda pid: create_mock_metadata(pid)

            # First paper indexes successfully, second fails
            def index_side_effect(metadata, file_locs):
                if metadata.paper_id == EXAMPLE_PAPER_ID:
                    return None  # Success
                else:
                    raise Exception("Indexing failed")

            mock_index_file.side_effect = index_side_effect

            # Should succeed with at least one paper indexed
            vs.rebuild_index(temp_file_locations)

            captured = capsys.readouterr()
            assert "1 papers indexed, 1 failed" in captured.out


class TestRebuildIndexCLI:
    """Test the main() CLI function for rebuild-index command."""

    def test_main_function_success(self, temp_file_locations, mock_indexing):
        """Test that main() function executes successfully."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create test paper
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)

        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = create_mock_metadata(EXAMPLE_PAPER_ID)

            # Call main() which should run rebuild_index
            vs.main()

            # Should have created indexes
            assert vs.CONTENT_INDEX is not None

    def test_main_function_error_handling(self, temp_file_locations):
        """Test that main() handles errors gracefully."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # No papers downloaded - should raise IndexError
        with pytest.raises(SystemExit) as exc_info:
            vs.main()

        # Should exit with code 1
        assert exc_info.value.code == 1

    def test_main_function_output(self, temp_file_locations, capsys, mock_indexing):
        """Test that main() produces expected output messages."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create test paper
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)

        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = create_mock_metadata(EXAMPLE_PAPER_ID)

            vs.main()

            # Capture output
            captured = capsys.readouterr()

            # Should have success messages
            assert "Rebuild index completed successfully!" in captured.out or \
                   "completed successfully" in captured.out.lower()

    def test_main_function_error_output(self, temp_file_locations, capsys):
        """Test that main() outputs error messages on failure."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # No papers - should fail
        try:
            vs.main()
        except SystemExit:
            pass  # Expected

        captured = capsys.readouterr()

        # Should have error message
        assert "Error rebuilding index:" in captured.out or "error" in captured.out.lower()


class TestRebuildIndexStateCounting:
    """Test that rebuild_index correctly counts successes and failures."""

    def test_rebuild_counts_all_successes(self, temp_file_locations, capsys, mock_indexing):
        """Test that rebuild_index reports correct success counts."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create test paper with summary and notes
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)

        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\nTest summary content.")

        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(notes_path, 'w') as f:
            f.write("# Notes\nTest notes content.")

        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = create_mock_metadata(EXAMPLE_PAPER_ID)

            vs.rebuild_index(temp_file_locations)

            captured = capsys.readouterr()

            # Should report success for all three types
            assert "1 papers indexed" in captured.out  # Content
            assert "1 summaries indexed" in captured.out  # Summary
            assert "1 notes indexed" in captured.out  # Notes


class TestRebuildIndexPerformance:
    """Test rebuild_index with multiple papers."""

    def test_rebuild_multiple_papers_with_varied_content(self, temp_file_locations, mock_indexing):
        """Test rebuild with multiple papers having different content types."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Create two test papers
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID)
        create_test_pdf(temp_file_locations, EXAMPLE_PAPER_ID_2)
        create_test_metadata_file(temp_file_locations, EXAMPLE_PAPER_ID_2)

        # Create summary for first paper
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\nAgent safety framework.")

        # Create notes only for second paper
        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID_2}.md")
        with open(notes_path, 'w') as f:
            f.write("# Notes\nInteresting research directions.")

        with patch('my_research_assistant.vector_store.get_paper_metadata') as mock_get_metadata:
            mock_get_metadata.side_effect = lambda pid: create_mock_metadata(pid)

            vs.rebuild_index(temp_file_locations)

            # Should have indexed all papers
            assert vs.CONTENT_INDEX is not None
            assert vs.SUMMARY_INDEX is not None

            # Verify indexing calls
            assert mock_indexing['index_file'].call_count == 2
            assert mock_indexing['index_summary'].call_count == 1
            assert mock_indexing['index_notes'].call_count == 1
