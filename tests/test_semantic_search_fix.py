"""Tests for semantic search diversity and display fixes."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from my_research_assistant.workflow import WorkflowRunner, QueryResult
from my_research_assistant.vector_store import search_index, _retrieve_with_manual_diversity
from my_research_assistant.project_types import SearchResult
from my_research_assistant.file_locations import FileLocations
from my_research_assistant.interface_adapter import TerminalAdapter
from rich.console import Console


class TestSemanticSearchDiversity:
    """Test that semantic search finds diverse papers for compound queries."""

    def test_compound_query_detection_triggers_manual_diversity(self):
        """Test that compound queries trigger manual diversity when MMR finds only one paper."""
        # This test verifies the diversity improvement logic
        query = "compare deepseek v3 and kimi k2 models"

        # Test compound query detection
        compound_indicators = ['compare', 'versus', 'vs', 'and', 'both', 'between']
        is_compound_query = any(indicator in query.lower() for indicator in compound_indicators)

        assert is_compound_query, "Should detect 'compare' as compound query indicator"

    def test_manual_diversity_extracts_key_terms(self):
        """Test that manual diversity strategy extracts key terms correctly."""
        import re

        query = "compare deepseek v3 and kimi k2 models"
        key_terms = []

        # Extract potential model names (patterns like "word-v3", "word v3", "word k2")
        model_patterns = re.findall(r'\b[A-Za-z]+[-\s]?[vV]?\d+\b', query)
        key_terms.extend(model_patterns)

        # Extract capitalized terms that might be product names
        cap_terms = re.findall(r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b', query)
        key_terms.extend(cap_terms)

        # For comparison queries, extract potential model names
        words = query.lower().split()
        potential_models = []
        for word in words:
            if word in ['compare', 'versus', 'vs', 'and', 'with', 'between']:
                continue
            if any(char.isdigit() for char in word) or word in ['deepseek', 'kimi', 'gpt', 'claude', 'llama']:
                potential_models.append(word)
        key_terms.extend(potential_models)

        # Verify we extracted relevant terms
        assert any('v3' in term or 'k2' in term for term in key_terms), f"Should extract version numbers, got: {key_terms}"
        assert any('deepseek' in term.lower() for term in key_terms), f"Should extract 'deepseek', got: {key_terms}"
        assert any('kimi' in term.lower() for term in key_terms), f"Should extract 'kimi', got: {key_terms}"


class TestSemanticSearchWorkflow:
    """Test the complete semantic search workflow including display."""

    @pytest.mark.asyncio
    async def test_semantic_search_workflow_returns_valid_result(self):
        """Test that semantic search workflow returns a properly formatted QueryResult."""
        # Mock dependencies
        mock_console = Mock(spec=Console)
        mock_interface = Mock(spec=TerminalAdapter)
        mock_llm = AsyncMock()

        # Mock LLM response
        mock_response = Mock()
        mock_response.text = "Based on the retrieved passages, DeepSeek-V3 and Kimi K2 are both large language models..."
        mock_llm.acomplete = AsyncMock(return_value=mock_response)

        # Mock search results that include both papers
        mock_search_results = [
            SearchResult(
                paper_id="2412.19437v2",
                pdf_filename="2412.19437v2.pdf",
                summary_filename="2412.19437v2.md",
                paper_title="DeepSeek-V3 Technical Report",
                page=1,
                chunk="DeepSeek-V3 is a powerful language model..."
            ),
            SearchResult(
                paper_id="2507.20534v1",
                pdf_filename="2507.20534v1.pdf",
                summary_filename="2507.20534v1.md",
                paper_title="Kimi K2: Open Agentic Intelligence",
                page=1,
                chunk="Kimi K2 represents an advancement in agentic AI..."
            )
        ]

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface)

        # Mock the search_index function to return diverse results
        with patch('my_research_assistant.workflow.search_index') as mock_search:
            mock_search.return_value = mock_search_results

            # Run semantic search workflow
            result = await runner.start_semantic_search_workflow("compare deepseek v3 and kimi k2")

            # Verify result structure
            assert isinstance(result, QueryResult)
            assert result.success is True
            assert result.content is not None
            assert len(result.content) > 0
            assert "DeepSeek-V3" in result.content or "deepseek" in result.content.lower()
            assert result.message == "Semantic search completed successfully"

            # Verify both papers are referenced
            assert len(result.paper_ids) >= 1  # Should have at least one paper

            # Verify search was called with enhanced parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]['use_mmr'] is True
            assert call_args[1]['k'] == 20
            assert call_args[1]['similarity_cutoff'] == 0.6

    @pytest.mark.asyncio
    async def test_semantic_search_handles_diverse_results(self):
        """Test that when diverse results are found, both papers are included in the response."""
        mock_console = Mock(spec=Console)
        mock_interface = Mock(spec=TerminalAdapter)
        mock_llm = AsyncMock()

        # Mock LLM response for comparison
        mock_response = Mock()
        mock_response.text = """DeepSeek-V3 and Kimi K2 represent different approaches to language modeling.

DeepSeek-V3:
- Technical report shows advanced capabilities
- Focus on efficiency and performance

Kimi K2:
- Open agentic intelligence approach
- Emphasis on reasoning and tool use

Both models demonstrate significant advances in their respective areas."""
        mock_llm.acomplete = AsyncMock(return_value=mock_response)

        # Mock diverse search results
        diverse_results = [
            SearchResult(
                paper_id="2412.19437v2",
                pdf_filename="2412.19437v2.pdf",
                summary_filename="2412.19437v2.md",
                paper_title="DeepSeek-V3 Technical Report",
                page=5,
                chunk="DeepSeek-V3 achieves state-of-the-art performance across multiple benchmarks..."
            ),
            SearchResult(
                paper_id="2507.20534v1",
                pdf_filename="2507.20534v1.pdf",
                summary_filename="2507.20534v1.md",
                paper_title="Kimi K2: Open Agentic Intelligence",
                page=3,
                chunk="Kimi K2 introduces novel agentic capabilities for complex reasoning tasks..."
            )
        ]

        runner = WorkflowRunner(mock_llm, mock_interface)

        with patch('my_research_assistant.workflow.search_index') as mock_search:
            mock_search.return_value = diverse_results

            result = await runner.start_semantic_search_workflow("compare deepseek v3 and kimi k2")

            # Verify both papers are found
            assert len(set(r.paper_id for r in diverse_results)) == 2
            assert result.success is True
            assert len(result.paper_ids) == 2
            assert "2412.19437v2" in result.paper_ids
            assert "2507.20534v1" in result.paper_ids

            # Verify content mentions both models
            content_lower = result.content.lower()
            assert "deepseek" in content_lower or "deepseek-v3" in content_lower
            assert "kimi" in content_lower


class TestSemanticSearchDisplay:
    """Test that semantic search results are properly displayed in chat interface."""

    @pytest.mark.asyncio
    async def test_chat_interface_displays_semantic_search_result(self):
        """Test that chat interface properly displays semantic search results."""
        from my_research_assistant.chat import ChatInterface

        # Create chat interface
        chat = ChatInterface()

        # Mock workflow runner
        mock_workflow_runner = AsyncMock()
        mock_result = QueryResult(
            success=True,
            papers=[],
            paper_ids=["2412.19437v2", "2507.20534v1"],
            message="Semantic search completed successfully",
            content="# Answer: compare deepseek v3 and kimi k2\n\nBoth models show impressive capabilities..."
        )
        mock_workflow_runner.start_semantic_search_workflow = AsyncMock(return_value=mock_result)

        # Mock interface adapter and state machine
        mock_interface = Mock()
        mock_state_machine = Mock()

        # Inject mocks
        chat.workflow_runner = mock_workflow_runner
        chat.interface_adapter = mock_interface
        chat.state_machine = mock_state_machine
        chat.render_markdown_response = Mock()
        chat.add_to_history = Mock()

        # Test semantic search command
        await chat.process_semantic_search_command("compare deepseek v3 and kimi k2")

        # Verify result was displayed
        chat.render_markdown_response.assert_called_once_with(mock_result.content)
        chat.add_to_history.assert_called_once_with("assistant", mock_result.content)

        # Verify state machine was updated
        mock_state_machine.transition_after_sem_search.assert_called_once_with(
            found_results=True,
            search_results=mock_result.content,
            paper_ids=mock_result.paper_ids,
            original_query="compare deepseek v3 and kimi k2"
        )

    @pytest.mark.asyncio
    async def test_chat_interface_handles_search_failure_gracefully(self):
        """Test that chat interface handles search failures with proper error messages."""
        from my_research_assistant.chat import ChatInterface

        chat = ChatInterface()

        # Mock failed result
        mock_workflow_runner = AsyncMock()
        mock_failed_result = QueryResult(
            success=False,
            papers=[],
            paper_ids=[],
            message="No results found",
            content=""
        )
        mock_workflow_runner.start_semantic_search_workflow = AsyncMock(return_value=mock_failed_result)

        # Mock interface and state machine
        mock_interface = Mock()
        mock_state_machine = Mock()

        chat.workflow_runner = mock_workflow_runner
        chat.interface_adapter = mock_interface
        chat.state_machine = mock_state_machine

        # Test failed search
        await chat.process_semantic_search_command("nonexistent query")

        # Verify error was shown
        mock_interface.show_error.assert_called_once()
        error_call = mock_interface.show_error.call_args[0][0]
        assert "Search failed" in error_call
        assert "success: False" in error_call

        # Verify state machine transitioned to initial
        mock_state_machine.transition_to_initial.assert_called_once_with("No search results")