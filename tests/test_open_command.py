"""Tests for the open command functionality."""

import os
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from my_research_assistant.result_storage import open_paper_content
from my_research_assistant.file_locations import FileLocations


@pytest.fixture
def temp_file_locations():
    """Create temporary file locations for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create subdirectories
        pdfs_dir = os.path.join(temp_dir, 'pdfs')
        extracted_dir = os.path.join(temp_dir, 'extracted_paper_text')
        os.makedirs(pdfs_dir)
        os.makedirs(extracted_dir)

        # Create file locations object
        file_locations = FileLocations(
            doc_home=temp_dir,
            index_dir=os.path.join(temp_dir, 'index'),
            summaries_dir=os.path.join(temp_dir, 'summaries'),
            images_dir=os.path.join(temp_dir, 'summaries', 'images'),
            pdfs_dir=pdfs_dir,
            extracted_paper_text_dir=extracted_dir,
            notes_dir=os.path.join(temp_dir, 'notes'),
            results_dir=os.path.join(temp_dir, 'results'),
            paper_metadata_dir=os.path.join(temp_dir, 'paper_metadata')
        )

        yield file_locations


@pytest.fixture
def sample_paper_files(temp_file_locations):
    """Create sample paper files for testing."""
    paper_id = "2107.03374v2"

    # Create PDF file
    pdf_path = os.path.join(temp_file_locations.pdfs_dir, f"{paper_id}.pdf")
    with open(pdf_path, 'w') as f:
        f.write("Mock PDF content")

    # Create extracted markdown file
    extracted_path = os.path.join(temp_file_locations.extracted_paper_text_dir, f"{paper_id}.md")
    with open(extracted_path, 'w') as f:
        f.write("""# Evaluating Large Language Models Trained on Code

Mark Chen, Jerry Tworek, Heewoo Jun, et al.

## Abstract

This paper introduces Codex, a GPT language model fine-tuned on publicly available code from GitHub.

## Introduction

Large language models have shown impressive capabilities...

## Method

We fine-tune GPT-3 on code from GitHub repositories...

## Results

Codex solves 28.8% of problems on the first attempt...

## Conclusion

We have shown that large language models can be effectively trained on code...
""")

    return paper_id, pdf_path, extracted_path


class TestOpenPaperContentWithPDFViewer:
    """Tests for open_paper_content when PDF_VIEWER is set."""

    def test_open_with_valid_pdf_viewer(self, sample_paper_files, temp_file_locations):
        """Test opening a paper with valid PDF_VIEWER set."""
        paper_id, pdf_path, _ = sample_paper_files

        with patch.dict(os.environ, {'PDF_VIEWER': '/usr/bin/open'}):
            with patch('subprocess.Popen') as mock_popen:
                # Mock successful subprocess launch
                mock_process = MagicMock()
                mock_popen.return_value = mock_process

                success, content, action_type = open_paper_content(paper_id, temp_file_locations)

                assert success is True
                assert action_type == "viewer"
                assert pdf_path in content
                assert "/usr/bin/open" in content
                assert "Paper has been opened using PDF viewer" in content

                # Verify subprocess was called correctly
                mock_popen.assert_called_once_with(
                    ['/usr/bin/open', pdf_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True
                )

    def test_open_with_invalid_pdf_viewer(self, sample_paper_files, temp_file_locations):
        """Test opening a paper with invalid PDF_VIEWER path."""
        paper_id, _, _ = sample_paper_files

        with patch.dict(os.environ, {'PDF_VIEWER': '/nonexistent/viewer'}):
            with patch('shutil.which', return_value=None):
                success, content, action_type = open_paper_content(paper_id, temp_file_locations)

                assert success is False
                assert action_type == "error"
                assert "open failed: PDF_VIEWER is set to '/nonexistent/viewer', which was not found" in content

    def test_open_with_subprocess_failure(self, sample_paper_files, temp_file_locations):
        """Test opening a paper when subprocess fails to launch."""
        paper_id, _, _ = sample_paper_files

        with patch.dict(os.environ, {'PDF_VIEWER': '/usr/bin/open'}):
            with patch('subprocess.Popen', side_effect=Exception("Launch failed")):
                success, content, action_type = open_paper_content(paper_id, temp_file_locations)

                assert success is False
                assert action_type == "error"
                assert "open failed: Could not launch PDF viewer" in content
                assert "Launch failed" in content


class TestOpenPaperContentWithoutPDFViewer:
    """Tests for open_paper_content when PDF_VIEWER is not set (markdown fallback)."""

    def test_open_without_pdf_viewer_returns_markdown(self, sample_paper_files, temp_file_locations):
        """Test opening a paper without PDF_VIEWER returns extracted markdown."""
        paper_id, _, extracted_path = sample_paper_files

        with patch.dict(os.environ, {}, clear=True):
            # Ensure PDF_VIEWER is not set
            if 'PDF_VIEWER' in os.environ:
                del os.environ['PDF_VIEWER']

            success, content, action_type = open_paper_content(paper_id, temp_file_locations)

            assert success is True
            assert action_type == "markdown"
            assert "Evaluating Large Language Models Trained on Code" in content
            assert "Mark Chen" in content
            assert "Abstract" in content
            assert "Codex" in content

    def test_open_without_pdf_viewer_missing_extracted_text(self, temp_file_locations):
        """Test opening a paper without PDF_VIEWER when extracted text doesn't exist."""
        paper_id = "2107.03374v2"

        # Create PDF but not extracted text
        pdf_path = os.path.join(temp_file_locations.pdfs_dir, f"{paper_id}.pdf")
        with open(pdf_path, 'w') as f:
            f.write("Mock PDF content")

        with patch.dict(os.environ, {}, clear=True):
            if 'PDF_VIEWER' in os.environ:
                del os.environ['PDF_VIEWER']

            success, content, action_type = open_paper_content(paper_id, temp_file_locations)

            assert success is False
            assert action_type == "error"
            assert "open failed: Extracted text not found" in content
            assert paper_id in content


class TestOpenPaperContentErrorCases:
    """Tests for error cases in open_paper_content."""

    def test_open_nonexistent_paper(self, temp_file_locations):
        """Test opening a paper that doesn't exist."""
        paper_id = "9999.99999v1"

        success, content, action_type = open_paper_content(paper_id, temp_file_locations)

        assert success is False
        assert action_type == "error"
        assert "open failed: Paper 9999.99999v1 has not been downloaded" in content
        assert "PDF not found" in content

    def test_open_with_pdf_viewer_but_no_pdf(self, temp_file_locations):
        """Test opening a paper with PDF_VIEWER set but PDF doesn't exist."""
        paper_id = "2107.03374v2"

        with patch.dict(os.environ, {'PDF_VIEWER': '/usr/bin/open'}):
            success, content, action_type = open_paper_content(paper_id, temp_file_locations)

            assert success is False
            assert action_type == "error"
            assert "open failed: Paper 2107.03374v2 has not been downloaded" in content


class TestOpenCommandIntegration:
    """Integration tests for the open command in the chat interface."""

    @pytest.mark.asyncio
    async def test_process_open_command_with_pdf_viewer(self, sample_paper_files, temp_file_locations):
        """Test process_open_command with PDF_VIEWER set."""
        from my_research_assistant.chat import ChatInterface
        from my_research_assistant.project_types import PaperMetadata
        from datetime import datetime

        paper_id, pdf_path, _ = sample_paper_files

        # Create a paper metadata object
        paper = PaperMetadata(
            paper_id=paper_id,
            title="Evaluating Large Language Models Trained on Code",
            authors=["Mark Chen", "Jerry Tworek"],
            abstract="Test abstract",
            categories=["cs.CL"],
            published=datetime.now(),
            updated=datetime.now(),
            paper_pdf_url=f"https://arxiv.org/pdf/{paper_id}.pdf",
            paper_abs_url=f"http://arxiv.org/abs/{paper_id}",
            doi=None,
            journal_ref=None
        )

        # Create chat interface
        chat = ChatInterface()
        chat.initialize()

        # Set up state machine
        chat.state_machine.state_vars.last_query_set = [paper_id]

        with patch.dict(os.environ, {'PDF_VIEWER': '/usr/bin/open'}):
            with patch('subprocess.Popen') as mock_popen:
                with patch('my_research_assistant.chat.FILE_LOCATIONS', temp_file_locations):
                    mock_process = MagicMock()
                    mock_popen.return_value = mock_process

                    # Process the open command
                    await chat.process_open_command("1")

                    # Verify subprocess was called
                    mock_popen.assert_called_once()

                    # Verify state machine transition
                    assert chat.state_machine.current_state.value == "summarized"
                    assert chat.state_machine.state_vars.selected_paper.paper_id == paper_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
