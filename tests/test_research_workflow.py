"""Test the research workflow functionality."""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from typing import List

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from my_research_assistant.workflow import WorkflowRunner, QueryResult
from my_research_assistant.project_types import PaperMetadata, SearchResult
from my_research_assistant.file_locations import FileLocations
from my_research_assistant.interface_adapter import InterfaceAdapter
from my_research_assistant import file_locations
from my_research_assistant.paper_manager import format_paper_reference, format_research_result
from llama_index.core.llms import LLM


@pytest.fixture
def temp_file_locations():
    """Create a temporary directory and set FILE_LOCATIONS to use it."""
    original_file_locations = file_locations.FILE_LOCATIONS

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_locations = file_locations.FileLocations.get_locations(temp_dir)
        file_locations.FILE_LOCATIONS = temp_locations

        try:
            yield temp_locations
        finally:
            file_locations.FILE_LOCATIONS = original_file_locations


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = Mock(spec=LLM)

    # Mock acomplete to return research synthesis
    async def mock_acomplete(prompt):
        response = Mock()
        if "short, descriptive title" in prompt:
            response.text = "Research Findings on AI Safety"
        else:
            response.text = """## Overview
The research reveals significant advances in AI safety mechanisms through multi-agent verification systems.

## Detailed Analysis

### Safety Verification Approaches
ShieldAgent introduces a novel verification framework that uses multiple specialized agents to validate safety policies.

### Performance Characteristics
The system demonstrates robust performance across various safety scenarios.

## Synthesis and Implications
This work represents a significant step forward in making AI systems more reliable and safe.

## References
- ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning (ArXiv ID: 2503.22738)
- Safe AI Systems Through Multi-Agent Verification (ArXiv ID: 2503.22739)"""
        return response

    llm.acomplete = AsyncMock(side_effect=mock_acomplete)
    return llm


@pytest.fixture
def mock_interface():
    """Create a mock interface adapter for testing."""
    interface = Mock(spec=InterfaceAdapter)
    interface.show_progress = Mock()
    interface.show_success = Mock()
    interface.show_error = Mock()
    interface.show_info = Mock()
    interface.render_content = Mock()
    interface.display_papers = Mock()
    interface.progress_context = MagicMock()
    interface.progress_context.return_value.__enter__ = Mock()
    interface.progress_context.return_value.__exit__ = Mock()
    return interface


@pytest.fixture
def sample_papers():
    """Create sample paper metadata for testing."""
    return [
        PaperMetadata(
            paper_id="2503.22738",
            title="ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning",
            published=datetime(2025, 3, 31),
            updated=None,
            paper_abs_url="https://arxiv.org/abs/2503.22738",
            paper_pdf_url="https://arxiv.org/pdf/2503.22738.pdf",
            authors=["John Doe", "Jane Smith"],
            abstract="This paper presents a novel approach to agent safety...",
            categories=["Computer Science", "Artificial Intelligence"],
            doi=None,
            journal_ref=None,
            default_pdf_filename="2503.22738.pdf"
        ),
        PaperMetadata(
            paper_id="2503.22739",
            title="Safe AI Systems Through Multi-Agent Verification",
            published=datetime(2025, 3, 30),
            updated=None,
            paper_abs_url="https://arxiv.org/abs/2503.22739",
            paper_pdf_url="https://arxiv.org/pdf/2503.22739.pdf",
            authors=["Alice Johnson", "Bob Williams"],
            abstract="An approach to safety verification using multiple agents...",
            categories=["Computer Science", "Machine Learning"],
            doi=None,
            journal_ref=None,
            default_pdf_filename="2503.22739.pdf"
        )
    ]


@pytest.fixture
def sample_search_results(sample_papers):
    """Create sample search results for testing."""
    return [
        SearchResult(
            paper_id="2503.22738",
            pdf_filename="2503.22738.pdf",
            summary_filename="2503.22738.md",
            paper_title="ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning",
            page=5,
            chunk="The ShieldAgent framework uses multiple verification layers...",
            similarity_score=0.9123
        ),
        SearchResult(
            paper_id="2503.22738",
            pdf_filename="2503.22738.pdf",
            summary_filename="2503.22738.md",
            paper_title="ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning",
            page=7,
            chunk="Safety policies are verified through formal reasoning methods...",
            similarity_score=0.8765
        ),
        SearchResult(
            paper_id="2503.22739",
            pdf_filename="2503.22739.pdf",
            summary_filename="2503.22739.md",
            paper_title="Safe AI Systems Through Multi-Agent Verification",
            page=3,
            chunk="Multi-agent systems provide redundant safety checks...",
            similarity_score=0.8234
        )
    ]


# ===== UNIT TESTS FOR HELPER FUNCTIONS =====

def test_format_paper_reference_with_title(sample_papers):
    """Test formatting a paper reference with title."""
    paper = sample_papers[0]
    result = format_paper_reference(paper, include_title=True)

    assert "ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning" in result
    assert "John Doe, Jane Smith" in result
    assert "2503.22738" in result


def test_format_paper_reference_without_title(sample_papers):
    """Test formatting a paper reference without title."""
    paper = sample_papers[0]
    result = format_paper_reference(paper, include_title=False)

    assert "ShieldAgent" not in result
    assert "John Doe, Jane Smith" in result
    assert "2503.22738" in result


def test_format_paper_reference_many_authors():
    """Test formatting with many authors shows 'et al.'."""
    paper = PaperMetadata(
        paper_id="2503.22738",
        title="Test Paper",
        published=datetime(2025, 3, 31),
        updated=None,
        paper_abs_url="https://arxiv.org/abs/2503.22738",
        paper_pdf_url="https://arxiv.org/pdf/2503.22738.pdf",
        authors=["Author 1", "Author 2", "Author 3", "Author 4"],
        abstract="Test abstract",
        categories=["CS"],
        doi=None,
        journal_ref=None,
        default_pdf_filename="2503.22738.pdf"
    )

    result = format_paper_reference(paper)
    assert "et al." in result
    assert "Author 1, Author 2 et al." in result


def test_format_research_result(sample_papers):
    """Test formatting a complete research result."""
    query = "How do multi-agent systems improve AI safety?"
    synthesis = "Multi-agent systems improve safety through redundant verification."

    result = format_research_result(query, synthesis, sample_papers)

    assert query in result
    assert synthesis in result
    assert "Papers Analyzed" in result
    assert "ShieldAgent" in result
    assert "Safe AI Systems" in result
    assert "2503.22738" in result
    assert "2503.22739" in result


# ===== INTEGRATION TESTS FOR RESEARCH WORKFLOW =====

@pytest.mark.asyncio
async def test_research_query_success(mock_llm, mock_interface, temp_file_locations,
                                     sample_search_results, sample_papers):
    """Test successful research query execution."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    # Mock the vector store search functions
    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search, \
         patch('my_research_assistant.vector_store.search_content_index_filtered') as mock_content_search, \
         patch('my_research_assistant.paper_manager.get_papers_by_ids') as mock_get_papers:

        # Setup mocks
        mock_summary_search.return_value = sample_search_results[:2]  # Summary results
        mock_content_search.return_value = sample_search_results  # Detail results
        mock_get_papers.return_value = sample_papers

        # Execute research query
        result = await runner.research_query("How do multi-agent systems improve AI safety?")

        # Verify result
        assert result.success is True
        assert len(result.papers) == 2
        assert len(result.paper_ids) == 2
        assert "2503.22738" in result.paper_ids
        assert "2503.22739" in result.paper_ids
        assert result.content is not None
        assert "Research Results:" in result.content
        assert "Overview" in result.content
        assert "Papers Analyzed" in result.content

        # Verify search calls
        mock_summary_search.assert_called_once()
        mock_content_search.assert_called_once()

        # Verify search parameters
        summary_call = mock_summary_search.call_args
        assert summary_call.kwargs['k'] == 5
        assert summary_call.kwargs['use_mmr'] is True
        assert summary_call.kwargs['similarity_cutoff'] == 0.5


@pytest.mark.asyncio
async def test_research_query_no_papers_found(mock_llm, mock_interface, temp_file_locations):
    """Test research query when no papers are found."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search:
        # No results from summary search
        mock_summary_search.return_value = []

        result = await runner.research_query("Nonexistent topic")

        assert result.success is False
        assert len(result.papers) == 0
        assert len(result.paper_ids) == 0
        assert "No relevant papers found" in result.content


@pytest.mark.asyncio
async def test_research_query_fallback_to_summaries(mock_llm, mock_interface, temp_file_locations,
                                                    sample_search_results, sample_papers):
    """Test research query falls back to summaries when no detail chunks found."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search, \
         patch('my_research_assistant.vector_store.search_content_index_filtered') as mock_content_search, \
         patch('my_research_assistant.paper_manager.get_papers_by_ids') as mock_get_papers:

        # Summary results available, but no detail results
        mock_summary_search.return_value = sample_search_results[:2]
        mock_content_search.return_value = []  # No detail chunks
        mock_get_papers.return_value = sample_papers

        result = await runner.research_query("Test query")

        assert result.success is True
        # Should still have papers from summary results
        assert len(result.papers) > 0


@pytest.mark.asyncio
async def test_research_query_custom_parameters(mock_llm, mock_interface, temp_file_locations,
                                               sample_search_results, sample_papers):
    """Test research query with custom parameters."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search, \
         patch('my_research_assistant.vector_store.search_content_index_filtered') as mock_content_search, \
         patch('my_research_assistant.paper_manager.get_papers_by_ids') as mock_get_papers:

        mock_summary_search.return_value = sample_search_results
        mock_content_search.return_value = sample_search_results
        mock_get_papers.return_value = sample_papers

        # Execute with custom parameters
        result = await runner.research_query(
            "Test query",
            num_summary_papers=10,
            num_detail_chunks=20
        )

        assert result.success is True

        # Verify custom parameters were used
        summary_call = mock_summary_search.call_args
        content_call = mock_content_search.call_args

        assert summary_call.kwargs['k'] == 10
        assert content_call.kwargs['k'] == 20


@pytest.mark.asyncio
async def test_research_query_error_handling(mock_llm, mock_interface, temp_file_locations):
    """Test research query error handling."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search:
        # Simulate an error
        mock_summary_search.side_effect = Exception("Index not found")

        result = await runner.research_query("Test query")

        assert result.success is False
        assert "Research query failed" in result.message
        assert "Index not found" in result.content


@pytest.mark.asyncio
async def test_research_query_multiple_papers(mock_llm, mock_interface, temp_file_locations):
    """Test research query correctly groups chunks by paper."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    # Create more diverse search results
    diverse_results = [
        SearchResult(
            paper_id="2503.22738",
            pdf_filename="2503.22738.pdf",
            summary_filename="2503.22738.md",
            paper_title="Paper A",
            page=1,
            chunk="Content from paper A, page 1",
            similarity_score=0.95
        ),
        SearchResult(
            paper_id="2503.22738",
            pdf_filename="2503.22738.pdf",
            summary_filename="2503.22738.md",
            paper_title="Paper A",
            page=2,
            chunk="Content from paper A, page 2",
            similarity_score=0.90
        ),
        SearchResult(
            paper_id="2503.22739",
            pdf_filename="2503.22739.pdf",
            summary_filename="2503.22739.md",
            paper_title="Paper B",
            page=1,
            chunk="Content from paper B, page 1",
            similarity_score=0.85
        ),
        SearchResult(
            paper_id="2503.22740",
            pdf_filename="2503.22740.pdf",
            summary_filename="2503.22740.md",
            paper_title="Paper C",
            page=3,
            chunk="Content from paper C, page 3",
            similarity_score=0.80
        )
    ]

    papers = [
        PaperMetadata(
            paper_id="2503.22738",
            title="Paper A",
            published=datetime(2025, 3, 31),
            updated=None,
            paper_abs_url="https://arxiv.org/abs/2503.22738",
            paper_pdf_url="https://arxiv.org/pdf/2503.22738.pdf",
            authors=["Author A"],
            abstract="Abstract A",
            categories=["CS"],
            doi=None,
            journal_ref=None,
            default_pdf_filename="2503.22738.pdf"
        ),
        PaperMetadata(
            paper_id="2503.22739",
            title="Paper B",
            published=datetime(2025, 3, 30),
            updated=None,
            paper_abs_url="https://arxiv.org/abs/2503.22739",
            paper_pdf_url="https://arxiv.org/pdf/2503.22739.pdf",
            authors=["Author B"],
            abstract="Abstract B",
            categories=["CS"],
            doi=None,
            journal_ref=None,
            default_pdf_filename="2503.22739.pdf"
        ),
        PaperMetadata(
            paper_id="2503.22740",
            title="Paper C",
            published=datetime(2025, 3, 29),
            updated=None,
            paper_abs_url="https://arxiv.org/abs/2503.22740",
            paper_pdf_url="https://arxiv.org/pdf/2503.22740.pdf",
            authors=["Author C"],
            abstract="Abstract C",
            categories=["CS"],
            doi=None,
            journal_ref=None,
            default_pdf_filename="2503.22740.pdf"
        )
    ]

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search, \
         patch('my_research_assistant.vector_store.search_content_index_filtered') as mock_content_search, \
         patch('my_research_assistant.paper_manager.get_papers_by_ids') as mock_get_papers:

        mock_summary_search.return_value = diverse_results[:2]
        mock_content_search.return_value = diverse_results
        mock_get_papers.return_value = papers

        result = await runner.research_query("Test query")

        assert result.success is True
        assert len(result.papers) == 3
        assert "2503.22738" in result.paper_ids
        assert "2503.22739" in result.paper_ids
        assert "2503.22740" in result.paper_ids

        # Check that pages are correctly listed
        assert "Referenced Pages: 1, 2" in result.content or "1, 2" in result.content
        assert "Paper A" in result.content
        assert "Paper B" in result.content
        assert "Paper C" in result.content


@pytest.mark.asyncio
async def test_research_query_uses_prompt_template(mock_llm, mock_interface, temp_file_locations,
                                                   sample_search_results, sample_papers):
    """Test that research query uses the correct prompt template."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search, \
         patch('my_research_assistant.vector_store.search_content_index_filtered') as mock_content_search, \
         patch('my_research_assistant.paper_manager.get_papers_by_ids') as mock_get_papers:

        mock_summary_search.return_value = sample_search_results
        mock_content_search.return_value = sample_search_results
        mock_get_papers.return_value = sample_papers

        result = await runner.research_query("Test query")

        # Verify LLM was called
        assert mock_llm.acomplete.called

        # Get the prompt that was passed to the LLM
        call_args = mock_llm.acomplete.call_args_list
        synthesis_call = [call for call in call_args if "Research Question:" in str(call)][0]
        prompt_used = synthesis_call[0][0]

        # Verify prompt contains expected elements from template
        assert "Research Question:" in prompt_used
        assert "Test query" in prompt_used
        assert "Relevant Excerpts:" in prompt_used


# ===== VECTOR STORE FUNCTION TESTS =====

def test_search_summary_index_with_mmr(temp_file_locations):
    """Test search_summary_index with MMR parameter."""
    from my_research_assistant.vector_store import search_summary_index

    # We can't easily test this without a real index, but we can verify the function signature
    # and that it accepts the new parameters
    assert hasattr(search_summary_index, '__call__')

    # Check function signature includes new parameters
    import inspect
    sig = inspect.signature(search_summary_index)
    assert 'use_mmr' in sig.parameters
    assert 'similarity_cutoff' in sig.parameters


def test_search_content_index_filtered_signature():
    """Test search_content_index_filtered function signature."""
    from my_research_assistant.vector_store import search_content_index_filtered

    import inspect
    sig = inspect.signature(search_content_index_filtered)

    assert 'query' in sig.parameters
    assert 'paper_ids' in sig.parameters
    assert 'k' in sig.parameters
    assert 'file_locations' in sig.parameters
    assert 'similarity_cutoff' in sig.parameters


# ===== EDGE CASES =====

@pytest.mark.asyncio
async def test_research_query_empty_string(mock_llm, mock_interface, temp_file_locations):
    """Test research query with empty string."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search:
        mock_summary_search.return_value = []

        result = await runner.research_query("")

        # Should handle gracefully
        assert result.success is False


@pytest.mark.asyncio
async def test_research_query_very_long_query(mock_llm, mock_interface, temp_file_locations,
                                              sample_search_results, sample_papers):
    """Test research query with very long query string."""
    runner = WorkflowRunner(mock_llm, mock_interface, temp_file_locations)

    long_query = "How do " + "very " * 100 + "complex multi-agent systems work?"

    with patch('my_research_assistant.vector_store.search_summary_index') as mock_summary_search, \
         patch('my_research_assistant.vector_store.search_content_index_filtered') as mock_content_search, \
         patch('my_research_assistant.paper_manager.get_papers_by_ids') as mock_get_papers:

        mock_summary_search.return_value = sample_search_results
        mock_content_search.return_value = sample_search_results
        mock_get_papers.return_value = sample_papers

        result = await runner.research_query(long_query)

        assert result.success is True
        assert long_query in result.content
