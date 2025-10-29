"""
Tests for search_tester.py - Command-line tool for testing search APIs.

This module tests:
- Unit tests: Argument parsing, validation, and formatting functions
- Integration tests: Search function calling with mocked APIs
- E2E tests: Full workflow with temporary file structures
"""
import argparse
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from my_research_assistant.search_tester import (
    parse_arguments,
    validate_arguments,
    format_summary_header,
    format_search_result,
    main,
)
from my_research_assistant.project_types import SearchResult
from my_research_assistant import constants
from my_research_assistant.vector_store import IndexError as CustomIndexError


# === UNIT TESTS: Argument Parsing ===

def test_parse_arguments_defaults():
    """Test that argument parser sets correct default values."""
    args = parse_arguments(['test query'])

    assert args.query == 'test query'
    assert args.summary is False
    assert args.papers is None
    assert args.num_chunks == constants.CONTENT_SEARCH_K
    assert args.content_similarity_threshold == constants.CONTENT_SEARCH_SIMILARITY_CUTOFF
    assert args.use_mmr is False
    assert args.mmr_alpha == constants.CONTENT_SEARCH_MMR_ALPHA


def test_parse_arguments_summary_flag():
    """Test --summary flag parsing."""
    args = parse_arguments(['--summary', 'test query'])

    assert args.summary is True
    assert args.query == 'test query'


def test_parse_arguments_papers_flag():
    """Test --papers flag with comma-separated paper IDs."""
    args = parse_arguments(['--papers', '2503.12345,2503.67890', 'test query'])

    assert args.papers == '2503.12345,2503.67890'
    assert args.query == 'test query'


def test_parse_arguments_k_flag():
    """Test -k and --num-chunks flags."""
    args1 = parse_arguments(['-k', '10', 'test query'])
    args2 = parse_arguments(['--num-chunks', '15', 'test query'])

    assert args1.num_chunks == 10
    assert args2.num_chunks == 15


def test_parse_arguments_similarity_threshold():
    """Test --content-similarity-threshold flag."""
    args = parse_arguments(['--content-similarity-threshold', '0.7', 'test query'])

    assert args.content_similarity_threshold == 0.7


def test_parse_arguments_mmr_flags():
    """Test --use-mmr and --mmr-alpha flags."""
    args = parse_arguments(['--use-mmr', '--mmr-alpha', '0.8', 'test query'])

    assert args.use_mmr is True
    assert args.mmr_alpha == 0.8


# === UNIT TESTS: Argument Validation ===

def test_validate_arguments_success():
    """Test validation passes with valid arguments."""
    args = argparse.Namespace(
        summary=False,
        papers=None,
        use_mmr=False,
        mmr_alpha=0.5,
        content_similarity_threshold=0.6
    )

    # Should not raise any exceptions
    validate_arguments(args)


def test_validate_arguments_summary_and_papers_conflict():
    """Test validation fails when both --summary and --papers are specified."""
    args = argparse.Namespace(
        summary=True,
        papers='2503.12345',
        use_mmr=False,
        mmr_alpha=0.5,
        content_similarity_threshold=0.6
    )

    with pytest.raises(SystemExit) as exc_info:
        validate_arguments(args)
    assert exc_info.value.code == 1


def test_validate_arguments_mmr_alpha_without_use_mmr():
    """Test validation fails when --mmr-alpha specified without --use-mmr."""
    args = argparse.Namespace(
        summary=False,
        papers=None,
        use_mmr=False,
        mmr_alpha=0.8,  # Non-default value
        content_similarity_threshold=0.6
    )

    with pytest.raises(SystemExit) as exc_info:
        validate_arguments(args)
    assert exc_info.value.code == 1


def test_validate_arguments_similarity_threshold_out_of_range():
    """Test validation fails for similarity threshold outside [0.0, 1.0]."""
    # Test below range
    args1 = argparse.Namespace(
        summary=False,
        papers=None,
        use_mmr=False,
        mmr_alpha=0.5,
        content_similarity_threshold=-0.1
    )

    with pytest.raises(SystemExit):
        validate_arguments(args1)

    # Test above range
    args2 = argparse.Namespace(
        summary=False,
        papers=None,
        use_mmr=False,
        mmr_alpha=0.5,
        content_similarity_threshold=1.1
    )

    with pytest.raises(SystemExit):
        validate_arguments(args2)


def test_validate_arguments_mmr_alpha_out_of_range():
    """Test validation fails for mmr-alpha outside [0.0, 1.0]."""
    # Test below range
    args1 = argparse.Namespace(
        summary=False,
        papers=None,
        use_mmr=True,
        mmr_alpha=-0.1,
        content_similarity_threshold=0.6
    )

    with pytest.raises(SystemExit):
        validate_arguments(args1)

    # Test above range
    args2 = argparse.Namespace(
        summary=False,
        papers=None,
        use_mmr=True,
        mmr_alpha=1.5,
        content_similarity_threshold=0.6
    )

    with pytest.raises(SystemExit):
        validate_arguments(args2)


# === UNIT TESTS: Result Formatting ===

def test_format_summary_header_content_search():
    """Test summary header formatting for content index search."""
    header = format_summary_header(
        query="machine learning",
        function_name="search_index",
        k=20,
        similarity_threshold=0.6,
        use_mmr=True,
        mmr_alpha=0.5,
        num_results=15,
        num_unique_papers=5
    )

    assert "machine learning" in header
    assert "search_index" in header
    assert "k=20" in header
    assert "similarity_threshold=0.6" in header
    assert "use_mmr=True" in header
    assert "mmr_alpha=0.5" in header
    assert "15 results" in header
    assert "5" in header  # Unique papers count


def test_format_summary_header_summary_search():
    """Test summary header formatting for summary index search."""
    header = format_summary_header(
        query="transformers",
        function_name="search_summary_index",
        k=5,
        similarity_threshold=0.5,
        use_mmr=True,
        mmr_alpha=None,  # Not applicable for summary search
        num_results=3,
        num_unique_papers=2
    )

    assert "transformers" in header
    assert "search_summary_index" in header
    assert "k=5" in header
    assert "3 results" in header
    assert "2" in header  # Unique papers count


def test_format_search_result():
    """Test formatting of individual search result."""
    result = SearchResult(
        paper_id="2503.12345",
        pdf_filename="2503.12345v1.pdf",
        summary_filename="2503.12345.md",
        paper_title="Test Paper on Machine Learning",
        page=5,
        chunk="This is a test chunk about neural networks."
    )

    formatted = format_search_result(result, result_number=1, search_type="content")

    assert "Result 1" in formatted
    assert "2503.12345" in formatted
    assert "Test Paper on Machine Learning" in formatted
    assert "2503.12345v1.pdf" in formatted
    assert "**Page:** 5" in formatted
    assert "**Size:** 43 characters" in formatted
    assert "This is a test chunk about neural networks." in formatted


def test_format_search_result_summary_index():
    """Test formatting for summary index result (uses summary_filename)."""
    result = SearchResult(
        paper_id="2503.67890",
        pdf_filename="2503.67890v2.pdf",
        summary_filename="2503.67890.md",
        paper_title="Another Test Paper",
        page=0,  # Summaries don't have pages
        chunk="Summary content here."
    )

    formatted = format_search_result(result, result_number=2, search_type="summary")

    assert "Result 2" in formatted
    assert "2503.67890.md" in formatted  # Should show summary filename
    assert "**Page:** 0" in formatted


def test_unique_papers_count_with_multiple_chunks():
    """Test that unique papers count is calculated correctly when multiple chunks come from same paper."""
    with patch('my_research_assistant.search_tester.search_index') as mock_search:
        # Return 5 results from only 2 unique papers
        mock_search.return_value = [
            SearchResult(paper_id="2503.12345", pdf_filename="2503.12345v1.pdf",
                        summary_filename="2503.12345.md", paper_title="Paper 1", page=1, chunk="chunk 1"),
            SearchResult(paper_id="2503.12345", pdf_filename="2503.12345v1.pdf",
                        summary_filename="2503.12345.md", paper_title="Paper 1", page=2, chunk="chunk 2"),
            SearchResult(paper_id="2503.67890", pdf_filename="2503.67890v1.pdf",
                        summary_filename="2503.67890.md", paper_title="Paper 2", page=1, chunk="chunk 3"),
            SearchResult(paper_id="2503.12345", pdf_filename="2503.12345v1.pdf",
                        summary_filename="2503.12345.md", paper_title="Paper 1", page=3, chunk="chunk 4"),
            SearchResult(paper_id="2503.67890", pdf_filename="2503.67890v1.pdf",
                        summary_filename="2503.67890.md", paper_title="Paper 2", page=2, chunk="chunk 5"),
        ]

        with patch('sys.argv', ['search-tester', 'test query']):
            with patch('my_research_assistant.search_tester.TextPaginator') as mock_paginator:
                main()

                mock_paginator.return_value.paginate_lines.assert_called_once()
                call_args = mock_paginator.return_value.paginate_lines.call_args
                lines = call_args[0][0]
                formatted_text = '\n'.join(lines)

                # Should show 5 results but only 2 unique papers
                assert "5 results returned" in formatted_text
                assert "**Unique papers:** 2" in formatted_text


# === INTEGRATION TESTS: Search Function Calling ===

@patch('my_research_assistant.search_tester.search_index')
def test_main_calls_search_index(mock_search_index):
    """Test that main() calls search_index with correct parameters."""
    mock_search_index.return_value = [
        SearchResult(
            paper_id="2503.12345",
            pdf_filename="2503.12345v1.pdf",
            summary_filename="2503.12345.md",
            paper_title="Test Paper",
            page=1,
            chunk="Test content"
        )
    ]

    with patch('sys.argv', ['search-tester', '-k', '15', 'test query']):
        with patch('my_research_assistant.search_tester.TextPaginator'):
            main()

    mock_search_index.assert_called_once()
    call_args = mock_search_index.call_args
    assert call_args[1]['query'] == 'test query'
    assert call_args[1]['k'] == 15


@patch('my_research_assistant.search_tester.search_summary_index')
def test_main_calls_search_summary_index(mock_search_summary):
    """Test that main() calls search_summary_index when --summary is specified."""
    mock_search_summary.return_value = []

    with patch('sys.argv', ['search-tester', '--summary', 'test query']):
        with patch('my_research_assistant.search_tester.TextPaginator'):
            main()

    mock_search_summary.assert_called_once()
    call_args = mock_search_summary.call_args
    assert call_args[1]['query'] == 'test query'
    assert call_args[1]['k'] == constants.SUMMARY_SEARCH_K  # Should use summary default


@patch('my_research_assistant.search_tester.search_content_index_filtered')
def test_main_calls_search_content_index_filtered(mock_search_filtered):
    """Test that main() calls search_content_index_filtered when --papers is specified."""
    mock_search_filtered.return_value = []

    with patch('sys.argv', ['search-tester', '--papers', '2503.12345,2503.67890', 'test query']):
        with patch('my_research_assistant.search_tester.TextPaginator'):
            main()

    mock_search_filtered.assert_called_once()
    call_args = mock_search_filtered.call_args
    assert call_args[1]['query'] == 'test query'
    assert call_args[1]['paper_ids'] == ['2503.12345', '2503.67890']


@patch('my_research_assistant.search_tester.search_index')
def test_main_passes_mmr_parameters(mock_search_index):
    """Test that MMR parameters are correctly passed to search_index."""
    mock_search_index.return_value = []

    with patch('sys.argv', ['search-tester', '--use-mmr', '--mmr-alpha', '0.7', 'test query']):
        with patch('my_research_assistant.search_tester.TextPaginator'):
            main()

    call_args = mock_search_index.call_args
    assert call_args[1]['use_mmr'] is True
    assert call_args[1]['mmr_alpha'] == 0.7


@patch('my_research_assistant.search_tester.search_index')
def test_main_handles_index_error(mock_search_index, capsys):
    """Test that main() handles IndexError gracefully."""
    mock_search_index.side_effect = CustomIndexError("Index not found")

    with patch('sys.argv', ['search-tester', 'test query']):
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Index not found" in captured.err


# === END-TO-END TESTS ===

def test_e2e_content_search_workflow():
    """E2E test: Full workflow for content index search."""
    # This test would require a real index, which is complex to set up
    # For now, we'll mock at the search function level
    with patch('my_research_assistant.search_tester.search_index') as mock_search:
        mock_search.return_value = [
            SearchResult(
                paper_id="2503.12345",
                pdf_filename="2503.12345v1.pdf",
                summary_filename="2503.12345.md",
                paper_title="Test Paper",
                page=1,
                chunk="Test content about transformers"
            )
        ]

        with patch('sys.argv', ['search-tester', 'transformers']):
            with patch('my_research_assistant.search_tester.TextPaginator') as mock_paginator:
                main()

                # Verify paginator was called
                mock_paginator.return_value.paginate_lines.assert_called_once()
                call_args = mock_paginator.return_value.paginate_lines.call_args
                lines = call_args[0][0]

                # Verify formatted output contains expected content
                formatted_text = '\n'.join(lines)
                assert 'transformers' in formatted_text
                assert 'search_index' in formatted_text
                assert 'Test Paper' in formatted_text


def test_e2e_summary_search_workflow():
    """E2E test: Full workflow for summary index search."""
    with patch('my_research_assistant.search_tester.search_summary_index') as mock_search:
        mock_search.return_value = [
            SearchResult(
                paper_id="2503.67890",
                pdf_filename="2503.67890v1.pdf",
                summary_filename="2503.67890.md",
                paper_title="Another Paper",
                page=0,
                chunk="Summary about neural networks"
            )
        ]

        with patch('sys.argv', ['search-tester', '--summary', 'neural networks']):
            with patch('my_research_assistant.search_tester.TextPaginator') as mock_paginator:
                main()

                mock_paginator.return_value.paginate_lines.assert_called_once()
                call_args = mock_paginator.return_value.paginate_lines.call_args
                lines = call_args[0][0]

                formatted_text = '\n'.join(lines)
                assert 'neural networks' in formatted_text
                assert 'search_summary_index' in formatted_text
                assert 'Another Paper' in formatted_text


def test_e2e_validation_error():
    """E2E test: Validation error exits with status 1."""
    with patch('sys.argv', ['search-tester', '--summary', '--papers', '2503.12345', 'query']):
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
