"""Tests for the validate_store module."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from rich.console import Console

from my_research_assistant.validate_store import (
    get_paper_store_status,
    validate_store,
    format_store_validation_table,
    print_store_validation,
    PaperStoreStatus
)
from my_research_assistant.file_locations import FileLocations


@pytest.fixture
def temp_file_locations():
    """Create temporary file locations for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create subdirectories
        pdfs_dir = os.path.join(temp_dir, 'pdfs')
        summaries_dir = os.path.join(temp_dir, 'summaries')
        extracted_text_dir = os.path.join(temp_dir, 'extracted_paper_text')
        notes_dir = os.path.join(temp_dir, 'notes')
        index_dir = os.path.join(temp_dir, 'index')
        images_dir = os.path.join(summaries_dir, 'images')
        results_dir = os.path.join(temp_dir, 'results')
        paper_metadata_dir = os.path.join(temp_dir, 'paper_metadata')

        for dir_path in [pdfs_dir, summaries_dir, extracted_text_dir, notes_dir,
                         index_dir, images_dir, results_dir, paper_metadata_dir]:
            os.makedirs(dir_path, exist_ok=True)

        yield FileLocations(
            doc_home=temp_dir,
            pdfs_dir=pdfs_dir,
            summaries_dir=summaries_dir,
            extracted_paper_text_dir=extracted_text_dir,
            notes_dir=notes_dir,
            index_dir=index_dir,
            images_dir=images_dir,
            results_dir=results_dir,
            paper_metadata_dir=paper_metadata_dir
        )


def test_paper_store_status_creation():
    """Test that PaperStoreStatus can be created correctly."""
    status = PaperStoreStatus(
        "2503.22738v1",  # paper_id
        True,             # has_metadata
        50,               # content_index_chunks
        True,             # has_summary
        True,             # has_extracted_paper_text
        20,               # summary_index_chunks
        False             # has_notes
    )

    assert status.paper_id == "2503.22738v1"
    assert status.has_metadata is True
    assert status.content_index_chunks == 50
    assert status.has_summary is True
    assert status.has_extracted_paper_text is True
    assert status.summary_index_chunks == 20
    assert status.has_notes is False


@patch('my_research_assistant.validate_store._count_chunks_for_paper')
def test_get_paper_store_status(mock_count_chunks, temp_file_locations):
    """Test getting store status for a single paper."""
    # Set up mock return values
    mock_count_chunks.side_effect = [25, 10]  # content=25, summary=10

    # Create test files
    paper_id = "2503.22738v1"

    # Create metadata file
    metadata_path = os.path.join(temp_file_locations.paper_metadata_dir, f"{paper_id}.json")
    with open(metadata_path, 'w') as f:
        f.write('{"title": "Test paper"}')

    # Create summary file
    summary_path = os.path.join(temp_file_locations.summaries_dir, f"{paper_id}.md")
    with open(summary_path, 'w') as f:
        f.write("Test summary")

    # Create extracted text file
    extracted_text_path = os.path.join(temp_file_locations.extracted_paper_text_dir, f"{paper_id}.md")
    with open(extracted_text_path, 'w') as f:
        f.write("Test extracted text")

    # Don't create notes file to test False case

    status = get_paper_store_status(paper_id, temp_file_locations)

    assert status.paper_id == paper_id
    assert status.has_metadata is True
    assert status.content_index_chunks == 25
    assert status.has_summary is True
    assert status.has_extracted_paper_text is True
    assert status.summary_index_chunks == 10
    assert status.has_notes is False

    # Verify that _count_chunks_for_paper was called correctly
    assert mock_count_chunks.call_count == 2
    mock_count_chunks.assert_any_call(paper_id, "content", temp_file_locations)
    mock_count_chunks.assert_any_call(paper_id, "summary", temp_file_locations)


@patch('my_research_assistant.validate_store.get_downloaded_paper_ids')
@patch('my_research_assistant.validate_store.get_paper_store_status')
def test_validate_store(mock_get_status, mock_get_paper_ids, temp_file_locations):
    """Test validating the entire store."""
    # Mock downloaded paper IDs
    mock_get_paper_ids.return_value = ["2503.22738v1", "2401.02777v2"]

    # Mock paper statuses - they'll be called in sorted order
    status1 = PaperStoreStatus("2401.02777v2", False, 0, False, False, 0, False)  # Called first (alphabetically first)
    status2 = PaperStoreStatus("2503.22738v1", True, 50, True, True, 20, True)   # Called second
    mock_get_status.side_effect = [status1, status2]

    statuses = validate_store(temp_file_locations)

    assert len(statuses) == 2
    # Should be sorted alphabetically
    paper_ids = [status.paper_id for status in statuses]
    assert sorted(paper_ids) == paper_ids  # Verify it's sorted
    assert "2401.02777v2" in paper_ids
    assert "2503.22738v1" in paper_ids


def test_format_store_validation_table():
    """Test formatting store validation results as a table."""
    statuses = [
        PaperStoreStatus("2503.22738v1", True, 50, True, True, 20, True),
        PaperStoreStatus("2401.02777v2", False, 0, False, False, 0, False)
    ]

    table = format_store_validation_table(statuses)

    assert table.title == "Store Validation Results"
    assert len(table.columns) == 7  # Updated to 7 columns with Has Metadata
    assert len(table.rows) == 2


@patch('my_research_assistant.validate_store.validate_store')
def test_print_store_validation_no_papers(mock_validate_store, temp_file_locations):
    """Test printing validation when no papers are found."""
    mock_validate_store.return_value = []

    console = Console(file=open(os.devnull, 'w'))  # Suppress output

    print_store_validation(console, temp_file_locations)

    mock_validate_store.assert_called_once_with(temp_file_locations)


@patch('my_research_assistant.validate_store.validate_store')
def test_print_store_validation_with_papers(mock_validate_store, temp_file_locations):
    """Test printing validation when papers are found."""
    statuses = [
        PaperStoreStatus("2503.22738v1", True, 50, True, True, 20, True),
        PaperStoreStatus("2401.02777v2", False, 24, False, False, 0, False)
    ]
    mock_validate_store.return_value = statuses

    console = Console(file=open(os.devnull, 'w'))  # Suppress output

    print_store_validation(console, temp_file_locations)

    mock_validate_store.assert_called_once_with(temp_file_locations)


def test_count_chunks_for_paper_with_results(temp_file_locations):
    """Test counting chunks when paper exists in index."""
    # Mock the collection
    mock_collection = MagicMock()
    mock_collection.get.return_value = {
        'metadatas': [
            {'paper_id': '2503.22738v1'},
            {'paper_id': '2503.22738v1'},
            {'paper_id': 'different_paper'}
        ]
    }

    # Mock the client
    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    # Mock chromadb.PersistentClient where it's imported (inside the function)
    with patch('chromadb.PersistentClient', return_value=mock_client):
        # Mock os.path.exists to return True for the db path
        with patch('my_research_assistant.validate_store.os.path.exists', return_value=True):
            from my_research_assistant.validate_store import _count_chunks_for_paper

            count = _count_chunks_for_paper("2503.22738v1", "content", temp_file_locations)

            assert count == 2  # Only results 1 and 2 match the paper_id


@patch('my_research_assistant.validate_store._get_or_initialize_index')
def test_count_chunks_for_paper_with_exception(mock_get_index, temp_file_locations):
    """Test counting chunks when an exception occurs."""
    mock_get_index.side_effect = Exception("Index error")

    from my_research_assistant.validate_store import _count_chunks_for_paper

    count = _count_chunks_for_paper("2503.22738v1", "content", temp_file_locations)

    assert count == 0  # Should return 0 on any exception