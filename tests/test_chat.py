"""Test the ChatInterface functionality, including semantic search command."""

import pytest
import asyncio
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from my_research_assistant.chat import ChatInterface
from my_research_assistant.file_locations import FileLocations
from my_research_assistant import file_locations


@pytest.fixture
def temp_file_locations():
    """Create a temporary directory and set FILE_LOCATIONS to use it.
    After the test, restore the original FILE_LOCATIONS.
    """
    # Save the original FILE_LOCATIONS
    original_file_locations = file_locations.FILE_LOCATIONS
    
    # Also save and reset the global VECTOR_STORE to avoid test pollution
    import my_research_assistant.vector_store as vs
    original_vector_store = vs.VECTOR_STORE
    original_vs_file_locations = vs.FILE_LOCATIONS
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create new FileLocations pointing to the temp directory
        temp_locations = file_locations.FileLocations.get_locations(temp_dir)
        
        # Replace the module-level FILE_LOCATIONS
        file_locations.FILE_LOCATIONS = temp_locations
        
        # Reset the global VECTOR_STORE to None so it gets reinitialized
        vs.VECTOR_STORE = None
        
        try:
            yield temp_locations
        finally:
            # Restore the original FILE_LOCATIONS and VECTOR_STORE
            file_locations.FILE_LOCATIONS = original_file_locations
            vs.VECTOR_STORE = original_vector_store
            vs.FILE_LOCATIONS = original_vs_file_locations


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = Mock()
    # Mock the acomplete method to return a mock response
    mock_response = Mock()
    mock_response.text = "Test summary of search results"
    llm.acomplete = AsyncMock(return_value=mock_response)
    return llm


class TestChatInterface:
    """Test ChatInterface functionality."""
    
    def test_chat_interface_initialization(self):
        """Test that ChatInterface can be initialized."""
        chat = ChatInterface()
        
        assert chat.console is not None
        assert chat.llm is None  # Not initialized until initialize() is called
        assert chat.workflow_runner is None
        assert chat.conversation_history == []
        assert chat.current_papers == []
        assert chat.current_state == "ready"
    
    @patch('my_research_assistant.chat.get_default_model')
    def test_chat_interface_initialize_success(self, mock_get_model, temp_file_locations):
        """Test successful ChatInterface initialization."""
        # Mock the LLM
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm
        
        chat = ChatInterface()
        result = chat.initialize()
        
        assert result is True
        assert chat.llm == mock_llm
        assert chat.workflow_runner is not None
    
    @patch('my_research_assistant.chat.get_default_model')
    def test_chat_interface_initialize_failure(self, mock_get_model, temp_file_locations):
        """Test ChatInterface initialization failure."""
        # Mock get_default_model to raise an exception
        mock_get_model.side_effect = Exception("API key not found")
        
        chat = ChatInterface()
        result = chat.initialize()
        
        assert result is False
        assert chat.llm is None
        assert chat.workflow_runner is None
    
    def test_add_to_history(self):
        """Test adding messages to conversation history."""
        chat = ChatInterface()
        
        chat.add_to_history("user", "test message")
        
        assert len(chat.conversation_history) == 1
        assert chat.conversation_history[0]['role'] == "user"
        assert chat.conversation_history[0]['content'] == "test message"
        assert 'timestamp' in chat.conversation_history[0]
    
    def test_clear_history(self):
        """Test clearing conversation history."""
        chat = ChatInterface()
        
        # Add some history
        chat.add_to_history("user", "test message 1")
        chat.add_to_history("assistant", "test response 1")
        
        assert len(chat.conversation_history) == 2
        
        # Clear history
        chat.clear_history()
        
        assert len(chat.conversation_history) == 0


class TestChatSemanticSearch:
    """Test semantic search functionality in ChatInterface."""
    
    @pytest.mark.asyncio
    @patch('my_research_assistant.chat.get_default_model')
    async def test_semantic_search_command_success(self, mock_get_model, temp_file_locations):
        """Test successful semantic search command execution."""
        # Set up indexed papers for testing
        from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
        import my_research_assistant.vector_store as vs
        
        # Override the imported FILE_LOCATIONS in vector_store
        vs.FILE_LOCATIONS = temp_file_locations
        
        # Download and index a paper for testing
        paper_id = '2503.22738'
        md = get_paper_metadata(paper_id)
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)
        
        # Mock the LLM
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.text = "Test summary of search results from the semantic search"
        mock_llm.acomplete = AsyncMock(return_value=mock_response)
        mock_get_model.return_value = mock_llm
        
        # Initialize chat interface
        chat = ChatInterface()
        init_result = chat.initialize()
        assert init_result is True
        
        # Test semantic search command
        test_query = "agent safety and shielding"
        
        # Capture the initial state
        initial_state = chat.current_state
        
        # Execute semantic search command
        await chat.process_semantic_search_command(test_query)
        
        # Verify state was reset
        assert chat.current_state == "ready"
        
        # Verify history was updated (should have assistant response)
        assert len(chat.conversation_history) == 1
        assert chat.conversation_history[0]['role'] == "assistant"
        
        # Verify LLM was called
        mock_llm.acomplete.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('my_research_assistant.chat.get_default_model')
    async def test_semantic_search_command_no_results(self, mock_get_model, temp_file_locations):
        """Test semantic search command when no results are found."""
        # Mock the LLM
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm
        
        # Initialize chat interface
        chat = ChatInterface()
        init_result = chat.initialize()
        assert init_result is True
        
        # Test semantic search command with no indexed papers
        test_query = "nonexistent topic that should return no results"
        
        # Execute semantic search command - should handle gracefully
        await chat.process_semantic_search_command(test_query)
        
        # Verify state was reset
        assert chat.current_state == "ready"
    
    @pytest.mark.asyncio
    @patch('my_research_assistant.chat.get_default_model')
    async def test_semantic_search_command_error_handling(self, mock_get_model, temp_file_locations):
        """Test semantic search command error handling."""
        # Mock the LLM to raise an exception
        mock_llm = Mock()
        mock_llm.acomplete = AsyncMock(side_effect=Exception("LLM error"))
        mock_get_model.return_value = mock_llm
        
        # Initialize chat interface
        chat = ChatInterface()
        init_result = chat.initialize()
        assert init_result is True
        
        # Test semantic search command with error
        test_query = "test query"
        
        # Execute semantic search command - should handle exception gracefully
        await chat.process_semantic_search_command(test_query)
        
        # Verify state was reset even after error
        assert chat.current_state == "ready"