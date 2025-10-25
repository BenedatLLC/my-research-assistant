"""Tests for summarizer module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from my_research_assistant.summarizer import (
    summarize_paper,
    extract_markdown,
    insert_metadata,
    save_summary,
    SummarizationError
)
from my_research_assistant.project_types import PaperMetadata


@pytest.fixture
def sample_paper_metadata():
    """Create a sample PaperMetadata object for testing."""
    return PaperMetadata(
        paper_id="2024.12345v1",
        title="Sample Research Paper",
        published=datetime(2024, 1, 15),
        updated=datetime(2024, 1, 20),
        paper_abs_url="https://arxiv.org/abs/2024.12345",
        paper_pdf_url="https://arxiv.org/pdf/2024.12345.pdf",
        authors=["John Doe", "Jane Smith"],
        abstract="This is a sample abstract for testing purposes.",
        categories=["cs.AI", "cs.LG"],
        doi="10.1000/xyz123",
        journal_ref="Journal of AI Research, Vol. 1, 2024"
    )


class TestSummarizePaper:
    """Test the summarize_paper function."""

    @patch('my_research_assistant.summarizer.get_default_model')
    @patch('my_research_assistant.summarizer.subst_prompt')
    def test_summarize_paper_basic(self, mock_subst_prompt, mock_get_model, sample_paper_metadata):
        """Test basic paper summarization without feedback."""
        # Setup mocks
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm

        mock_response = Mock()
        mock_response.text = "```markdown\n# Sample Summary\n\nThis is a test summary.\n```"
        mock_llm.complete.return_value = mock_response

        mock_subst_prompt.return_value = "Test prompt"

        # Test input
        text = "This is the full paper text for testing."

        # Call function
        result = summarize_paper(text, sample_paper_metadata)

        # Assertions
        mock_subst_prompt.assert_called_once_with('base-summary-v2', text_block=text)
        mock_get_model.assert_called_once()
        mock_llm.complete.assert_called_once_with("Test prompt")
        
        # Check that metadata was inserted
        assert "Paper id: 2024.12345v1" in result
        assert "Authors: John Doe, Jane Smith" in result
        assert "Categories: cs.AI, cs.LG" in result

    @patch('my_research_assistant.summarizer.get_default_model')
    @patch('my_research_assistant.summarizer.subst_prompt')
    def test_summarize_paper_with_feedback(self, mock_subst_prompt, mock_get_model, sample_paper_metadata):
        """Test paper summarization with feedback and previous summary."""
        # Setup mocks
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm

        mock_response = Mock()
        mock_response.text = "```markdown\n# Improved Summary\n\nThis is an improved summary.\n```"
        mock_llm.complete.return_value = mock_response

        mock_subst_prompt.return_value = "Improvement prompt"

        # Test inputs
        text = "This is the full paper text."
        feedback = "Please make it more technical"
        previous_summary = "# Old Summary\n\nThis was the old summary."

        # Call function
        result = summarize_paper(text, sample_paper_metadata, feedback=feedback, previous_summary=previous_summary)

        # Assertions
        mock_subst_prompt.assert_called_once_with(
            'improve-summary-v2',
            feedback=feedback,
            previous_summary=previous_summary,
            text_block=text
        )
        mock_llm.complete.assert_called_once_with("Improvement prompt")
        
        # Check result
        assert "# Improved Summary" in result
        assert "Paper id: 2024.12345v1" in result

    @patch('my_research_assistant.summarizer.get_default_model')
    @patch('my_research_assistant.summarizer.subst_prompt')
    def test_summarize_paper_no_markdown_blocks(self, mock_subst_prompt, mock_get_model, sample_paper_metadata):
        """Test summarization when response has no markdown code blocks."""
        # Setup mocks
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm

        mock_response = Mock()
        mock_response.text = "# Plain Summary\n\nThis summary has no code blocks."
        mock_llm.complete.return_value = mock_response

        mock_subst_prompt.return_value = "Test prompt"

        # Test input
        text = "Paper text"

        # Call function
        result = summarize_paper(text, sample_paper_metadata)

        # Should work with plain text (extract_markdown returns original text)
        assert "# Plain Summary" in result
        assert "Paper id: 2024.12345v1" in result

    @patch('my_research_assistant.summarizer.get_default_model')
    @patch('my_research_assistant.summarizer.subst_prompt')
    def test_summarize_paper_llm_error(self, mock_subst_prompt, mock_get_model, sample_paper_metadata):
        """Test handling of LLM errors during summarization."""
        # Setup mocks
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm
        mock_llm.complete.side_effect = Exception("LLM API error")
        
        mock_subst_prompt.return_value = "Test prompt"
        
        # Test input
        text = "Paper text"
        
        # Call function and expect exception
        with pytest.raises(SummarizationError) as exc_info:
            summarize_paper(text, sample_paper_metadata)
        
        assert "An error occurred during summarizing: LLM API error" in str(exc_info.value)

    @patch('my_research_assistant.summarizer.get_default_model')
    @patch('my_research_assistant.summarizer.subst_prompt')
    def test_summarize_paper_no_title_in_response(self, mock_subst_prompt, mock_get_model, sample_paper_metadata):
        """Test handling when LLM response doesn't contain a title."""
        # Setup mocks
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm

        mock_response = Mock()
        mock_response.text = "```markdown\nThis summary has no title heading.\n```"
        mock_llm.complete.return_value = mock_response

        mock_subst_prompt.return_value = "Test prompt"

        # Test input
        text = "Paper text"

        # Call function and expect SummarizationError
        with pytest.raises(SummarizationError) as exc_info:
            summarize_paper(text, sample_paper_metadata)

        assert "Generated markdown did not contain a title" in str(exc_info.value)

    @patch('my_research_assistant.summarizer.get_default_model')
    @patch('my_research_assistant.summarizer.subst_prompt')
    def test_summarize_paper_md_code_block(self, mock_subst_prompt, mock_get_model, sample_paper_metadata):
        """Test extraction from ```md code blocks."""
        # Setup mocks
        mock_llm = Mock()
        mock_get_model.return_value = mock_llm

        mock_response = Mock()
        mock_response.text = "```md\n# MD Block Summary\n\nThis uses md instead of markdown.\n```"
        mock_llm.complete.return_value = mock_response
        
        mock_subst_prompt.return_value = "Test prompt"
        
        # Test input
        text = "Paper text"
        
        # Call function
        result = summarize_paper(text, sample_paper_metadata)
        
        # Should extract from md block
        assert "# MD Block Summary" in result
        assert "Paper id: 2024.12345v1" in result


class TestExtractMarkdown:
    """Test the extract_markdown helper function."""

    def test_extract_markdown_with_markdown_block(self):
        """Test extraction from ```markdown blocks."""
        text = "Here is some text\n```markdown\n# Title\nContent\n```\nMore text"
        result = extract_markdown(text)
        assert result == "# Title\nContent"

    def test_extract_markdown_with_md_block(self):
        """Test extraction from ```md blocks."""
        text = "Preamble\n```md\n# Another Title\nMore content\n```\nPostamble"
        result = extract_markdown(text)
        assert result == "# Another Title\nMore content"

    def test_extract_markdown_no_blocks(self):
        """Test when there are no code blocks."""
        text = "Just plain text with no code blocks"
        result = extract_markdown(text)
        assert result == "Just plain text with no code blocks"

    def test_extract_markdown_empty_block(self):
        """Test extraction from empty markdown block."""
        text = "```markdown\n\n```"
        result = extract_markdown(text)
        assert result == ""


class TestInsertMetadata:
    """Test the insert_metadata helper function."""

    def test_insert_metadata_with_title(self, sample_paper_metadata):
        """Test inserting metadata after a title."""
        markdown = "# Paper Title\n\nSome content here."
        result = insert_metadata(markdown, sample_paper_metadata)
        
        lines = result.split('\n')
        assert lines[0] == "# Paper Title"
        assert "Paper id: 2024.12345v1" in result
        assert "Authors: John Doe, Jane Smith" in result
        assert "Categories: cs.AI, cs.LG" in result
        assert "Published: 2024-01-15" in result
        assert "Updated: 2024-01-20" in result
        assert "## Abstract" in result
        assert sample_paper_metadata.abstract in result

    def test_insert_metadata_no_title(self, sample_paper_metadata):
        """Test error when markdown has no title."""
        markdown = "Just some content without a title heading."
        
        with pytest.raises(SummarizationError) as exc_info:
            insert_metadata(markdown, sample_paper_metadata)
        
        assert "Generated markdown did not contain a title" in str(exc_info.value)

    def test_insert_metadata_no_updated_date(self):
        """Test metadata insertion when no updated date."""
        pmd = PaperMetadata(
            paper_id="2024.67890",
            title="Test Paper",
            published=datetime(2024, 5, 10),
            updated=None,  # No updated date
            paper_abs_url="https://arxiv.org/abs/2024.67890",
            paper_pdf_url="https://arxiv.org/pdf/2024.67890.pdf",
            authors=["Test Author"],
            abstract="Test abstract",
            categories=["cs.AI"],
            doi=None,
            journal_ref=None
        )
        
        markdown = "# Test Title\n\nContent"
        result = insert_metadata(markdown, pmd)
        
        assert "Updated:" not in result
        assert "Published: 2024-05-10" in result

    def test_insert_metadata_no_abstract(self):
        """Test metadata insertion when no abstract."""
        pmd = PaperMetadata(
            paper_id="2024.67890",
            title="Test Paper",
            published=datetime(2024, 5, 10),
            updated=None,
            paper_abs_url="https://arxiv.org/abs/2024.67890",
            paper_pdf_url="https://arxiv.org/pdf/2024.67890.pdf",
            authors=["Test Author"],
            abstract=None,  # No abstract
            categories=["cs.AI"],
            doi=None,
            journal_ref=None
        )
        
        markdown = "# Test Title\n\nContent"
        result = insert_metadata(markdown, pmd)
        
        assert "## Abstract" not in result
        assert "Paper id: 2024.67890" in result


class TestSaveSummary:
    """Test the save_summary function."""

    @patch('my_research_assistant.summarizer.FILE_LOCATIONS')
    @patch('builtins.open')
    def test_save_summary(self, mock_open, mock_file_locations):
        """Test saving a summary to file."""
        # Setup mocks
        mock_file_locations.ensure_summaries_dir.return_value = None
        mock_file_locations.summaries_dir = "/test/summaries"
        
        # Test inputs
        markdown = "# Test Summary\n\nThis is a test."
        paper_id = "2024.12345"
        
        # Call function
        result = save_summary(markdown, paper_id)
        
        # Assertions
        mock_file_locations.ensure_summaries_dir.assert_called_once()
        expected_path = "/test/summaries/2024.12345.md"
        mock_open.assert_called_once_with(expected_path, 'w')
        
        # Check that write was called with correct content
        mock_file = mock_open.return_value.__enter__.return_value
        mock_file.write.assert_called_once_with(markdown)
        
        assert result == expected_path