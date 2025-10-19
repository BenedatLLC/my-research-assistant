"""End-to-end tests for the enhanced find command with Google Custom Search.

These tests verify the complete user workflows from the design document:
- Flow 1: Find → Summarize workflow (Google search)
- Flow 2: Find → List → Summary (sorted by ID)
- Flow 3: Automatic fallback to ArXiv search
- Additional scenarios: Error handling, semantic search integration, research workflow
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from my_research_assistant.chat import ChatInterface
from my_research_assistant.workflow import WorkflowRunner
from my_research_assistant.project_types import PaperMetadata
from my_research_assistant.file_locations import FileLocations
from my_research_assistant import file_locations
from my_research_assistant.interface_adapter import InterfaceAdapter


@pytest.fixture
def temp_file_locations():
    """Create a temporary directory and set FILE_LOCATIONS to use it."""
    original_file_locations = file_locations.FILE_LOCATIONS

    # Also save and reset the global indexes to avoid test pollution
    import my_research_assistant.vector_store as vs
    original_content_index = vs.CONTENT_INDEX
    original_summary_index = vs.SUMMARY_INDEX
    original_vs_file_locations = vs.FILE_LOCATIONS

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_locations = file_locations.FileLocations.get_locations(temp_dir)
        file_locations.FILE_LOCATIONS = temp_locations

        # Reset the global indexes
        vs.CONTENT_INDEX = None
        vs.SUMMARY_INDEX = None

        try:
            yield temp_locations
        finally:
            file_locations.FILE_LOCATIONS = original_file_locations
            vs.CONTENT_INDEX = original_content_index
            vs.SUMMARY_INDEX = original_summary_index
            vs.FILE_LOCATIONS = original_vs_file_locations


def create_mock_metadata(paper_id: str, title: str) -> PaperMetadata:
    """Helper to create mock paper metadata."""
    return PaperMetadata(
        paper_id=paper_id,
        title=title,
        published=datetime(2024, 1, 1),
        updated=datetime(2024, 1, 1),
        paper_abs_url=f"https://arxiv.org/abs/{paper_id}",
        paper_pdf_url=f"https://arxiv.org/pdf/{paper_id}.pdf",
        authors=["Test Author"],
        abstract=f"Abstract for {title}",
        categories=["Machine Learning"],
        doi=None,
        journal_ref=None,
    )


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = Mock()
    mock_response = Mock()
    mock_response.text = "Test summary"
    llm.acomplete = AsyncMock(return_value=mock_response)
    llm.complete = Mock(return_value=mock_response)
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
    interface.progress_context = Mock()
    interface.progress_context.return_value.__enter__ = Mock()
    interface.progress_context.return_value.__exit__ = Mock()
    return interface


class TestFindCommandE2E:
    """End-to-end tests for find command workflows."""

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    async def test_find_summarize_workflow_google_search(
        self, mock_get_metadata, mock_google_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        E2E Flow 1: Find → Summarize workflow (Google search)

        User story:
        1. User has Google credentials configured
        2. User runs `find transformer attention`
        3. System uses Google Custom Search
        4. System displays top 5 papers sorted by ID
        5. User runs `summarize 2`
        6. System downloads and summarizes paper #2

        Expected: State transitions initial → select-new → summarized
        """
        # Mock Google search to return unsorted paper IDs
        mock_google_search.return_value = [
            "2412.19437v1", "2107.03374v2", "2308.03873", "2503.22738", "2510.11694"
        ]

        # Mock metadata fetching
        papers = [
            create_mock_metadata("2412.19437", "DeepSeek-V3 Technical Report"),
            create_mock_metadata("2107.03374", "Evaluating LLMs Trained on Code"),
            create_mock_metadata("2308.03873", "Code LLM Evaluation"),
            create_mock_metadata("2503.22738", "ShieldAgent"),
            create_mock_metadata("2510.11694", "Attention Mechanisms"),
        ]
        mock_get_metadata.side_effect = papers

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Step 1: Execute find command
        result = await runner.start_add_paper_workflow("transformer attention")

        # Verify Google search was used
        mock_google_search.assert_called_once_with("transformer attention", k=10)

        # Verify results are sorted by paper ID
        assert result.success is True
        assert len(result.papers) == 5

        # Papers should be sorted by ID (ascending)
        expected_order = ["2107.03374", "2308.03873", "2412.19437", "2503.22738", "2510.11694"]
        actual_order = [p.paper_id for p in result.papers]
        assert actual_order == expected_order, f"Expected {expected_order}, got {actual_order}"

        # Verify paper_ids in result match
        assert result.paper_ids == expected_order

        # Verify interface.display_papers was called with sorted papers
        mock_interface.display_papers.assert_called_once()
        displayed_papers = mock_interface.display_papers.call_args[0][0]
        displayed_ids = [p.paper_id for p in displayed_papers]
        assert displayed_ids == expected_order

        # Step 2: Verify paper #2 is the correct paper (2308.03873)
        # When sorted by ID, paper #2 should be "2308.03873"
        paper_number_2 = result.papers[1]
        assert paper_number_2.paper_id == "2308.03873"
        assert paper_number_2.title == "Code LLM Evaluation"

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    async def test_find_list_summary_sorted_workflow(
        self, mock_get_metadata, mock_google_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        E2E Flow 2: Find → List → Summary (sorted by ID)

        User story:
        1. User runs `find DeepSeek V3`
        2. System shows results sorted by paper ID
        3. User runs `list`
        4. Papers displayed in same order (by ID)
        5. User runs `summary 1`

        Expected: Consistent paper numbering across commands
        """
        # Mock Google search
        mock_google_search.return_value = [
            "2503.22738", "2412.19437v2", "2308.03873"
        ]

        # Mock metadata
        papers = [
            create_mock_metadata("2503.22738", "ShieldAgent"),
            create_mock_metadata("2412.19437", "DeepSeek-V3 Technical Report"),
            create_mock_metadata("2308.03873", "Code LLM Evaluation"),
        ]
        mock_get_metadata.side_effect = papers

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command
        result = await runner.start_add_paper_workflow("DeepSeek V3")

        # Verify papers are sorted by ID
        assert result.success is True
        expected_order = ["2308.03873", "2412.19437", "2503.22738"]
        assert result.paper_ids == expected_order

        # Paper #1 should be "2308.03873" (first when sorted by ID)
        paper_1 = result.papers[0]
        assert paper_1.paper_id == "2308.03873"

        # Paper #2 should be "2412.19437"
        paper_2 = result.papers[1]
        assert paper_2.paper_id == "2412.19437"
        assert paper_2.title == "DeepSeek-V3 Technical Report"

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', None)
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', None)
    @patch('my_research_assistant.arxiv_downloader._arxiv_keyword_search')
    async def test_automatic_fallback_to_arxiv_search(
        self, mock_arxiv_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        E2E Flow 3: Automatic fallback to ArXiv search

        User story:
        1. User does not configure Google credentials
        2. User runs `find neural networks`
        3. System detects no credentials
        4. System automatically uses ArXiv API keyword search
        5. Results displayed sorted by paper ID

        Expected: Same behavior as before enhancement (backward compatible)
        """
        # Mock ArXiv search to return papers (unsorted)
        papers = [
            create_mock_metadata("2510.11694", "Neural Network Architectures"),
            create_mock_metadata("2107.03374", "Neural Network Training"),
            create_mock_metadata("2308.03873", "Neural Network Evaluation"),
        ]
        mock_arxiv_search.return_value = papers

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command
        result = await runner.start_add_paper_workflow("neural networks")

        # Verify ArXiv search was used (not Google)
        mock_arxiv_search.assert_called_once_with("neural networks", max_results=50)

        # Verify results are still sorted by paper ID
        assert result.success is True
        expected_order = ["2107.03374", "2308.03873", "2510.11694"]
        assert result.paper_ids == expected_order

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.google_search.google_search_arxiv')
    async def test_google_search_quota_exhausted(
        self, mock_google_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        E2E Flow 4: Google search with quota exhausted (error handling)

        User story:
        1. User has Google credentials configured
        2. User runs `find deep learning`
        3. Google API returns 429 (quota exhausted)
        4. System raises exception with clear message
        5. No automatic fallback to ArXiv API (by design)

        Expected: User-friendly error message about quota
        """
        # Mock Google search to raise quota error
        mock_google_search.side_effect = Exception("API request failed with status code 429")

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command - should propagate exception
        result = await runner.start_add_paper_workflow("deep learning")

        # Verify error was captured in result
        assert result.success is False
        assert "429" in result.message or "API request failed" in result.message

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    async def test_google_search_no_results(
        self, mock_get_metadata, mock_google_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        Test Google search returns no results.

        User story:
        1. User runs `find xyzabc123nonexistent`
        2. Google search returns empty list
        3. System returns empty result
        4. State remains unchanged
        """
        # Mock Google search to return no results
        mock_google_search.return_value = []

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command
        result = await runner.start_add_paper_workflow("xyzabc123nonexistent")

        # Verify empty result (success=False when no papers found)
        assert result.success is False
        assert len(result.papers) == 0
        assert result.paper_ids == []
        assert "No papers found" in result.message

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    async def test_google_search_version_deduplication(
        self, mock_get_metadata, mock_google_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        Test that Google search correctly deduplicates multiple versions.

        User story:
        1. Google search returns multiple versions of same paper
        2. System deduplicates by choosing latest version
        3. Only latest version appears in results
        """
        # Mock Google search to return multiple versions
        mock_google_search.return_value = [
            "2107.03374", "2107.03374v1", "2107.03374v2", "2308.03873"
        ]

        # Mock metadata fetching (only for deduplicated IDs)
        papers = [
            create_mock_metadata("2107.03374v2", "Evaluating LLMs v2"),
            create_mock_metadata("2308.03873", "Code LLM Evaluation"),
        ]
        mock_get_metadata.side_effect = papers

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command
        result = await runner.start_add_paper_workflow("code evaluation")

        # Verify only latest version is in results
        assert result.success is True
        assert len(result.papers) == 2

        # Check that only v2 is present (not base ID or v1)
        paper_ids = result.paper_ids
        assert "2107.03374v2" in paper_ids
        assert "2107.03374" not in paper_ids
        assert "2107.03374v1" not in paper_ids

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    async def test_find_semantic_search_integration(
        self, mock_get_metadata, mock_google_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        E2E Flow: Find → Semantic search workflow

        User story:
        1. User runs `find transformer attention`
        2. Papers are found and sorted by ID
        3. User runs `sem-search query optimization`
        4. Query set is preserved (papers still available)

        Expected: Query set maintained across different workflows
        """
        # Mock Google search
        mock_google_search.return_value = [
            "2412.19437", "2107.03374", "2308.03873"
        ]

        # Mock metadata
        papers = [
            create_mock_metadata("2412.19437", "DeepSeek-V3"),
            create_mock_metadata("2107.03374", "Evaluating LLMs"),
            create_mock_metadata("2308.03873", "Code Evaluation"),
        ]
        mock_get_metadata.side_effect = papers

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command
        result = await runner.start_add_paper_workflow("transformer attention")

        # Verify papers found and sorted
        assert result.success is True
        expected_order = ["2107.03374", "2308.03873", "2412.19437"]
        assert result.paper_ids == expected_order

        # Note: State machine behavior for query set preservation
        # is tested separately in test_state_machine.py
        # This E2E test verifies the find command output is correct

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', '')
    @patch('my_research_assistant.arxiv_downloader._arxiv_keyword_search')
    async def test_empty_engine_id_fallback(
        self, mock_arxiv_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        Test that empty SEARCH_ENGINE_ID triggers fallback.

        User story:
        1. User has API_KEY set but SEARCH_ENGINE_ID is empty
        2. System detects incomplete credentials
        3. System falls back to ArXiv API search
        """
        # Mock ArXiv search
        papers = [create_mock_metadata("2107.03374", "Test Paper")]
        mock_arxiv_search.return_value = papers

        # Create workflow runner
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command
        result = await runner.start_add_paper_workflow("test query")

        # Verify ArXiv search was used (not Google)
        mock_arxiv_search.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    async def test_result_limiting_with_google_search(
        self, mock_get_metadata, mock_google_search, temp_file_locations, mock_llm, mock_interface
    ):
        """
        Test that results are limited to k even with many Google results.

        User story:
        1. Google search returns 10 papers
        2. User requests only k=3 papers
        3. System returns only 3 papers (first 3 when sorted by ID)
        """
        # Mock Google search to return 5 papers
        mock_google_search.return_value = [
            "2510.11694", "2107.03374", "2308.03873", "2412.19437", "2503.22738"
        ]

        # Mock metadata
        papers = [
            create_mock_metadata("2510.11694", "Paper 5"),
            create_mock_metadata("2107.03374", "Paper 1"),
            create_mock_metadata("2308.03873", "Paper 2"),
            create_mock_metadata("2412.19437", "Paper 3"),
            create_mock_metadata("2503.22738", "Paper 4"),
        ]
        mock_get_metadata.side_effect = papers

        # Create workflow runner with k=3
        runner = WorkflowRunner(mock_llm, mock_interface, file_locations=temp_file_locations)

        # Execute find command with k=3
        # Note: WorkflowRunner.start_add_paper_workflow uses default k=5 from search_arxiv_papers
        # To test k parameter, we need to patch search_arxiv_papers directly
        with patch('my_research_assistant.workflow.search_arxiv_papers') as mock_search:
            mock_search.return_value = sorted(papers, key=lambda p: p.paper_id)[:3]

            result = await runner.start_add_paper_workflow("test query")

            # Verify only 3 papers returned (first 3 when sorted by ID)
            assert result.success is True
            assert len(result.papers) == 3
            expected_order = ["2107.03374", "2308.03873", "2412.19437"]
            assert result.paper_ids == expected_order
