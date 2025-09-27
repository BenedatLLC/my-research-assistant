"""Integration tests for the validate-store command in the chat interface."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock

from my_research_assistant.chat import ChatInterface
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


@pytest.mark.asyncio
async def test_validate_store_command_integration(temp_file_locations):
    """Test that validate-store command works in chat interface."""

    # Patch the global FILE_LOCATIONS to use our temp directory
    with patch('my_research_assistant.chat.FILE_LOCATIONS', temp_file_locations):
        with patch('my_research_assistant.validate_store.FILE_LOCATIONS', temp_file_locations):

            # Create a test PDF file
            test_pdf = os.path.join(temp_file_locations.pdfs_dir, "2503.22738v1.pdf")
            with open(test_pdf, 'w') as f:
                f.write("test pdf content")

            # Create a test summary file
            test_summary = os.path.join(temp_file_locations.summaries_dir, "2503.22738v1.md")
            with open(test_summary, 'w') as f:
                f.write("# Test Summary\nThis is a test summary.")

            # Mock the LLM initialization and other dependencies
            with patch('my_research_assistant.chat.get_default_model') as mock_get_model:
                mock_get_model.return_value = MagicMock()

                # Mock the index functions to avoid actual ChromaDB operations
                with patch('my_research_assistant.validate_store._get_or_initialize_index') as mock_get_index:
                    # Mock a successful index with some chunks
                    mock_index = MagicMock()
                    mock_retriever = MagicMock()
                    mock_index.as_retriever.return_value = mock_retriever

                    # Mock chunks for content index
                    mock_result = MagicMock()
                    mock_result.metadata = {'paper_id': '2503.22738v1'}
                    mock_retriever.retrieve.return_value = [mock_result, mock_result]  # 2 chunks

                    mock_get_index.return_value = mock_index

                    # Create chat interface
                    chat_interface = ChatInterface()

                    # Initialize the interface (mock the LLM setup)
                    with patch.object(chat_interface, 'initialize') as mock_init:
                        mock_init.return_value = True

                        # Test the validate-store command directly
                        await chat_interface.process_validate_store_command()

                        # Verify the command executed without error
                        # (If it throws an exception, the test will fail)

                        # Check that history was updated
                        assert len(chat_interface.conversation_history) > 0
                        last_entry = chat_interface.conversation_history[-1]
                        assert last_entry['role'] == 'assistant'
                        assert 'validate-store completed' in last_entry['content']


@pytest.mark.asyncio
async def test_validate_store_command_no_papers(temp_file_locations):
    """Test validate-store command when no papers exist."""

    # Patch the global FILE_LOCATIONS to use our temp directory
    with patch('my_research_assistant.chat.FILE_LOCATIONS', temp_file_locations):
        with patch('my_research_assistant.validate_store.FILE_LOCATIONS', temp_file_locations):

            # Mock the LLM initialization and other dependencies
            with patch('my_research_assistant.chat.get_default_model') as mock_get_model:
                mock_get_model.return_value = MagicMock()

                # Create chat interface
                chat_interface = ChatInterface()

                # Initialize the interface (mock the LLM setup)
                with patch.object(chat_interface, 'initialize') as mock_init:
                    mock_init.return_value = True

                    # Test the validate-store command with no papers
                    await chat_interface.process_validate_store_command()

                    # Verify the command executed without error
                    assert len(chat_interface.conversation_history) > 0
                    last_entry = chat_interface.conversation_history[-1]
                    assert last_entry['role'] == 'assistant'
                    assert 'validate-store completed' in last_entry['content']


@pytest.mark.asyncio
async def test_validate_store_command_error_handling(temp_file_locations):
    """Test validate-store command error handling."""

    # Patch the global FILE_LOCATIONS to use our temp directory
    with patch('my_research_assistant.chat.FILE_LOCATIONS', temp_file_locations):
        with patch('my_research_assistant.validate_store.FILE_LOCATIONS', temp_file_locations):

            # Mock the LLM initialization and other dependencies
            with patch('my_research_assistant.chat.get_default_model') as mock_get_model:
                mock_get_model.return_value = MagicMock()

                # Mock print_store_validation to raise an exception
                with patch('my_research_assistant.chat.print_store_validation') as mock_print:
                    mock_print.side_effect = Exception("Test error")

                    # Create chat interface
                    chat_interface = ChatInterface()

                    # Initialize the interface (mock the LLM setup)
                    with patch.object(chat_interface, 'initialize') as mock_init:
                        mock_init.return_value = True

                        # Mock the interface adapter's show_error method
                        chat_interface.interface_adapter.show_error = MagicMock()

                        # Test the validate-store command with error
                        await chat_interface.process_validate_store_command()

                        # Verify error handling was called
                        chat_interface.interface_adapter.show_error.assert_called_once()
                        error_call = chat_interface.interface_adapter.show_error.call_args[0][0]
                        assert "Store validation failed" in error_call
                        assert "Test error" in error_call