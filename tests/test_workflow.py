"""Test the ResearchAssistantWorkflow functionality."""

import pytest
import asyncio
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import List

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from my_research_assistant.workflow import (
    ResearchAssistantWorkflow, 
    WorkflowRunner,
    SearchResultsEvent,
    PaperSelectedEvent,
    PaperDownloadedEvent,
    PaperIndexedEvent,
    SummaryGeneratedEvent,
    SummaryImproveEvent,
    SummarySavedEvent,
    SemanticSearchEvent,
    SemanticSearchResultsEvent
)
from my_research_assistant.project_types import PaperMetadata
from my_research_assistant.file_locations import FileLocations
from my_research_assistant.interface_adapter import InterfaceAdapter
from my_research_assistant import file_locations
from llama_index.core.workflow import StartEvent, StopEvent, Context
from llama_index.core.llms import LLM


@pytest.fixture
def temp_file_locations():
    """Create a temporary directory and set FILE_LOCATIONS to use it."""
    # Save the original FILE_LOCATIONS
    original_file_locations = file_locations.FILE_LOCATIONS
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create new FileLocations pointing to the temp directory
        temp_locations = file_locations.FileLocations.get_locations(temp_dir)
        
        # Replace the module-level FILE_LOCATIONS
        file_locations.FILE_LOCATIONS = temp_locations
        
        try:
            yield temp_locations
        finally:
            # Restore the original FILE_LOCATIONS
            file_locations.FILE_LOCATIONS = original_file_locations


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = Mock(spec=LLM)
    llm.complete = Mock()
    return llm


@pytest.fixture
def sample_paper_metadata():
    """Create sample paper metadata for testing."""
    return PaperMetadata(
        paper_id="2503.22738",
        title="ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning",
        published=datetime(2025, 3, 31),
        updated=None,
        paper_abs_url="https://arxiv.org/abs/2503.22738",
        paper_pdf_url="https://arxiv.org/pdf/2503.22738.pdf",
        authors=["John Doe", "Jane Smith"],
        abstract="This paper presents a novel approach...",
        categories=["Computer Science", "Artificial Intelligence"],
        doi=None,
        journal_ref=None,
        default_pdf_filename="2503.22738.pdf"
    )


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

@pytest.fixture
def workflow(mock_llm, mock_interface, temp_file_locations):
    """Create a workflow instance for testing."""
    return ResearchAssistantWorkflow(llm=mock_llm, interface=mock_interface, file_locations=temp_file_locations)


class TestWorkflowEvents:
    """Test workflow event creation and structure."""
    
    def test_search_results_event(self, sample_paper_metadata):
        """Test SearchResultsEvent creation."""
        papers = [sample_paper_metadata]
        event = SearchResultsEvent(papers=papers, query="test query")
        
        assert event.papers == papers
        assert event.query == "test query"
    
    def test_paper_selected_event(self, sample_paper_metadata):
        """Test PaperSelectedEvent creation."""
        event = PaperSelectedEvent(paper=sample_paper_metadata)
        assert event.paper == sample_paper_metadata
    
    def test_paper_downloaded_event(self, sample_paper_metadata):
        """Test PaperDownloadedEvent creation."""
        event = PaperDownloadedEvent(
            paper=sample_paper_metadata, 
            local_path="/tmp/test.pdf"
        )
        assert event.paper == sample_paper_metadata
        assert event.local_path == "/tmp/test.pdf"
    
    def test_paper_indexed_event(self, sample_paper_metadata):
        """Test PaperIndexedEvent creation."""
        event = PaperIndexedEvent(
            paper=sample_paper_metadata,
            paper_text="Sample paper text content"
        )
        assert event.paper == sample_paper_metadata
        assert event.paper_text == "Sample paper text content"
    
    def test_summary_generated_event(self, sample_paper_metadata):
        """Test SummaryGeneratedEvent creation."""
        event = SummaryGeneratedEvent(
            paper=sample_paper_metadata,
            summary="# Test Summary\nThis is a test summary",
            paper_text="Full paper text"
        )
        assert event.paper == sample_paper_metadata
        assert event.summary == "# Test Summary\nThis is a test summary"
        assert event.paper_text == "Full paper text"
    
    def test_summary_improve_event(self, sample_paper_metadata):
        """Test SummaryImproveEvent creation."""
        event = SummaryImproveEvent(
            paper=sample_paper_metadata,
            current_summary="Old summary",
            paper_text="Full paper text",
            feedback="Make it more detailed"
        )
        assert event.paper == sample_paper_metadata
        assert event.current_summary == "Old summary"
        assert event.paper_text == "Full paper text"
        assert event.feedback == "Make it more detailed"


class TestWorkflowSteps:
    """Test individual workflow steps."""
    
    @pytest.mark.asyncio
    async def test_search_papers_success(self, workflow, sample_paper_metadata):
        """Test successful paper search step."""
        # Mock the search function
        with patch('my_research_assistant.workflow.search_arxiv_papers') as mock_search:
            mock_search.return_value = [sample_paper_metadata]
            
            # Create mock context
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            
            # Create start event
            start_event = StartEvent(query="test query")
            
            # Run the step
            result = await workflow.search_papers_impl(ctx, "test query")
            
            # Verify results
            assert isinstance(result, SearchResultsEvent)
            assert len(result.papers) == 1
            assert result.papers[0] == sample_paper_metadata
            assert result.query == "test query"
            
            # Verify search was called correctly
            mock_search.assert_called_once_with("test query", k=5)
            
            # Verify context was used
            assert ctx.write_event_to_stream.call_count == 2  # Progress + results
    
    @pytest.mark.asyncio
    async def test_search_papers_no_results(self, workflow):
        """Test paper search step when no papers found."""
        with patch('my_research_assistant.workflow.search_arxiv_papers') as mock_search:
            mock_search.return_value = []
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            start_event = StartEvent(query="nonexistent query")
            
            result = await workflow.search_papers_impl(ctx, "nonexistent query")
            
            assert isinstance(result, StopEvent)
            assert "No papers found" in result.result
    
    @pytest.mark.asyncio
    async def test_search_papers_exception(self, workflow):
        """Test paper search step when search fails."""
        with patch('my_research_assistant.workflow.search_arxiv_papers') as mock_search:
            mock_search.side_effect = Exception("API Error")
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            start_event = StartEvent(query="test query")
            
            result = await workflow.search_papers_impl(ctx, "test query")
            
            assert isinstance(result, StopEvent)
            assert "Search failed" in result.result
            assert "API Error" in result.result
    
    @pytest.mark.asyncio
    async def test_handle_paper_selection_success(self, workflow, sample_paper_metadata):
        """Test successful paper selection."""
        ctx = Mock(spec=Context)
        ctx.write_event_to_stream = Mock()
        
        search_event = SearchResultsEvent(papers=[sample_paper_metadata], query="test")
        
        result = await workflow.handle_paper_selection(ctx, search_event)
        
        assert isinstance(result, PaperSelectedEvent)
        assert result.paper == sample_paper_metadata
    
    @pytest.mark.asyncio
    async def test_handle_paper_selection_no_papers(self, workflow):
        """Test paper selection with no papers available."""
        ctx = Mock(spec=Context)
        ctx.write_event_to_stream = Mock()
        
        search_event = SearchResultsEvent(papers=[], query="test")
        
        result = await workflow.handle_paper_selection(ctx, search_event)
        
        assert isinstance(result, StopEvent)
        assert "No papers available" in result.result
    
    @pytest.mark.asyncio
    async def test_download_paper_step_success(self, workflow, sample_paper_metadata, temp_file_locations):
        """Test successful paper download."""
        with patch('my_research_assistant.workflow.download_paper') as mock_download:
            mock_download.return_value = "/tmp/test.pdf"
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            
            select_event = PaperSelectedEvent(paper=sample_paper_metadata)
            
            result = await workflow.download_paper_step(ctx, select_event)
            
            assert isinstance(result, PaperDownloadedEvent)
            assert result.paper == sample_paper_metadata
            assert result.local_path == "/tmp/test.pdf"
            
            mock_download.assert_called_once_with(sample_paper_metadata, temp_file_locations)
    
    @pytest.mark.asyncio
    async def test_download_paper_step_failure(self, workflow, sample_paper_metadata):
        """Test paper download failure."""
        with patch('my_research_assistant.workflow.download_paper') as mock_download:
            mock_download.side_effect = Exception("Download failed")
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            
            select_event = PaperSelectedEvent(paper=sample_paper_metadata)
            
            result = await workflow.download_paper_step(ctx, select_event)
            
            assert isinstance(result, StopEvent)
            assert "Download failed" in result.result
    
    @pytest.mark.asyncio
    async def test_index_paper_step_success(self, workflow, sample_paper_metadata):
        """Test successful paper indexing."""
        with patch('my_research_assistant.workflow.index_file') as mock_index:
            mock_index.return_value = "Sample paper text content"
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            
            download_event = PaperDownloadedEvent(
                paper=sample_paper_metadata, 
                local_path="/tmp/test.pdf"
            )
            
            result = await workflow.index_paper_step(ctx, download_event)
            
            assert isinstance(result, PaperIndexedEvent)
            assert result.paper == sample_paper_metadata
            assert result.paper_text == "Sample paper text content"
            
            mock_index.assert_called_once_with(sample_paper_metadata)
    
    @pytest.mark.asyncio
    async def test_generate_summary_step_success(self, workflow, sample_paper_metadata):
        """Test successful summary generation."""
        with patch('my_research_assistant.workflow.summarize_paper') as mock_summarize:
            mock_summarize.return_value = "# Test Summary\nThis is a test summary"
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            
            index_event = PaperIndexedEvent(
                paper=sample_paper_metadata,
                paper_text="Full paper text"
            )
            
            result = await workflow.generate_summary_step(ctx, index_event)
            
            assert isinstance(result, SummaryGeneratedEvent)
            assert result.paper == sample_paper_metadata
            assert result.summary == "# Test Summary\nThis is a test summary"
            assert result.paper_text == "Full paper text"
            
            mock_summarize.assert_called_once_with("Full paper text", sample_paper_metadata)
    
    @pytest.mark.asyncio
    async def test_improve_summary_step_success(self, workflow, sample_paper_metadata):
        """Test successful summary improvement."""
        with patch('my_research_assistant.workflow.summarize_paper') as mock_summarize:
            mock_summarize.return_value = "# Improved Summary\nThis is an improved summary"
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            
            improve_event = SummaryImproveEvent(
                paper=sample_paper_metadata,
                current_summary="Old summary",
                paper_text="Full paper text",
                feedback="Make it more detailed"
            )
            
            result = await workflow.improve_summary_step(ctx, improve_event)
            
            assert isinstance(result, SummaryGeneratedEvent)
            assert result.paper == sample_paper_metadata
            assert result.summary == "# Improved Summary\nThis is an improved summary"
            
            mock_summarize.assert_called_once_with(
                "Full paper text", 
                sample_paper_metadata,
                feedback="Make it more detailed",
                previous_summary="Old summary"
            )
    
    @pytest.mark.asyncio
    async def test_save_summary_step_success(self, workflow, sample_paper_metadata, temp_file_locations):
        """Test successful summary saving."""
        with patch('my_research_assistant.workflow.save_summary') as mock_save:
            expected_path = f"{temp_file_locations.summaries_dir}/2503.22738.md"
            mock_save.return_value = expected_path
            
            ctx = Mock(spec=Context)
            ctx.write_event_to_stream = Mock()
            
            summary_event = SummaryGeneratedEvent(
                paper=sample_paper_metadata,
                summary="# Test Summary\nContent",
                paper_text="Full text"
            )
            
            result = await workflow.save_summary_step(ctx, summary_event)
            
            assert isinstance(result, StopEvent)
            assert "Summary saved successfully" in result.result
            assert expected_path in result.result
            
            mock_save.assert_called_once_with("# Test Summary\nContent", "2503.22738")


class TestWorkflowRunner:
    """Test the WorkflowRunner helper class."""
    
    def test_workflow_runner_init(self, mock_llm, mock_interface, temp_file_locations):
        """Test WorkflowRunner initialization."""
        runner = WorkflowRunner(llm=mock_llm, interface=mock_interface, file_locations=temp_file_locations)
        
        assert runner.workflow is not None
        assert isinstance(runner.workflow, ResearchAssistantWorkflow)
        assert runner.current_state is None
    
    def test_start_workflow_basic(self, mock_llm, mock_interface, temp_file_locations, sample_paper_metadata):
        """Test starting a workflow with mocked components."""
        runner = WorkflowRunner(llm=mock_llm, interface=mock_interface, file_locations=temp_file_locations)
        
        # This would require more complex mocking of the entire workflow execution
        # For now, we just test that the method exists and can be called
        assert hasattr(runner, 'start_add_paper_workflow')
        assert callable(runner.start_add_paper_workflow)
        assert hasattr(runner, 'start_semantic_search_workflow')
        assert callable(runner.start_semantic_search_workflow)


class TestWorkflowIntegration:
    """Integration tests for the complete workflow."""
    
    def test_workflow_initialization(self, mock_llm, mock_interface, temp_file_locations):
        """Test that workflow can be properly initialized."""
        workflow = ResearchAssistantWorkflow(llm=mock_llm, interface=mock_interface, file_locations=temp_file_locations)
        
        assert workflow.llm == mock_llm
        assert workflow.interface == mock_interface
        assert workflow.file_locations == temp_file_locations
        assert hasattr(workflow, 'tools')
        assert len(workflow.tools) == 6  # All 6 expected tools
    
    def test_workflow_tools_registration(self, workflow):
        """Test that all required tools are registered."""
        expected_tools = [
            "search_arxiv_papers",
            "download_paper", 
            "index_file",
            "search_index",
            "summarize_paper",
            "save_summary"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in workflow.tools
            assert workflow.tools[tool_name] is not None


@pytest.mark.integration
class TestWorkflowEndToEnd:
    """End-to-end workflow tests (requires network and API access)."""
    
    @pytest.mark.skipif(True, reason="Requires API keys and network access")
    @pytest.mark.asyncio
    async def test_full_workflow_execution(self, temp_file_locations):
        """Test complete workflow execution with real components.
        
        This test is skipped by default as it requires:
        - Valid OpenAI API key
        - Network access to ArXiv
        - Proper environment setup
        """
        from my_research_assistant.models import get_default_model
        
        llm = get_default_model()
        workflow = ResearchAssistantWorkflow(llm=llm, file_locations=temp_file_locations)
        
        # This would test the complete flow but is disabled for CI
        # runner = WorkflowRunner(llm=llm, file_locations=temp_file_locations)
        # result = await runner.start_workflow("machine learning transformers")
        # assert "Summary saved successfully" in result
        pass