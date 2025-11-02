"""
Unit tests for the prompt.py module.
"""
import pytest
import re
from unittest.mock import patch, mock_open

from my_research_assistant.prompt import (
    subst_prompt,
    subst_prompts,
    PromptFileError,
    PromptVarError,
    PROMPT_VAR_RE
)


class TestPromptVariableRegex:
    """Test the PROMPT_VAR_RE regex pattern."""
    
    def test_single_variable_match(self):
        """Test matching a single variable."""
        text = "Hello {{name}}"
        matches = PROMPT_VAR_RE.findall(text)
        assert matches == ["name"]
    
    def test_multiple_variable_match(self):
        """Test matching multiple variables."""
        text = "Hello {{name}}, today is {{date}}"
        matches = PROMPT_VAR_RE.findall(text)
        assert matches == ["name", "date"]
    
    def test_variable_with_underscore(self):
        """Test variables with underscores."""
        text = "Process {{text_block}} and {{file_path}}"
        matches = PROMPT_VAR_RE.findall(text)
        assert matches == ["text_block", "file_path"]
    
    def test_variable_with_numbers(self):
        """Test variables with numbers."""
        text = "Item {{item1}} and {{var_2}}"
        matches = PROMPT_VAR_RE.findall(text)
        assert matches == ["item1", "var_2"]
    
    def test_no_matches(self):
        """Test text with no variables."""
        text = "No variables here"
        matches = PROMPT_VAR_RE.findall(text)
        assert matches == []
    
    def test_invalid_variable_format(self):
        """Test that invalid formats don't match."""
        text = "Invalid {name} or {{123invalid}}"
        matches = PROMPT_VAR_RE.findall(text)
        assert matches == []


class TestSubstPrompt:
    """Test the subst_prompt function."""
    
    @patch("my_research_assistant.prompt.resources")
    def test_basic_substitution(self, mock_resources):
        """Test basic variable substitution."""
        mock_file_content = "Hello {{name}}, welcome to {{place}}!"
        mock_file = mock_open(read_data=mock_file_content)
        mock_resources.files.return_value.joinpath.return_value.open = mock_file
        
        result = subst_prompt("test", name="Alice", place="Python")
        
        assert result == "Hello Alice, welcome to Python!"
        mock_resources.files.assert_called_once()
        mock_resources.files.return_value.joinpath.assert_called_once_with("prompts/test.md")
    
    @patch("my_research_assistant.prompt.resources")
    def test_no_variables(self, mock_resources):
        """Test prompt with no variables."""
        mock_file_content = "This is a simple prompt with no variables."
        mock_file = mock_open(read_data=mock_file_content)
        mock_resources.files.return_value.joinpath.return_value.open = mock_file
        
        result = subst_prompt("test")
        
        assert result == "This is a simple prompt with no variables."
    
    @patch("my_research_assistant.prompt.resources")
    def test_missing_variable_error(self, mock_resources):
        """Test PromptVarError is raised for missing variables."""
        mock_file_content = "Hello {{name}}, welcome to {{place}}!"
        mock_file = mock_open(read_data=mock_file_content)
        mock_resources.files.return_value.joinpath.return_value.open = mock_file
        
        with pytest.raises(PromptVarError) as exc_info:
            subst_prompt("test", name="Alice")  # missing 'place'
        
        assert "place" in str(exc_info.value)
        assert "not provided in keyword arguments" in str(exc_info.value)
    
    @patch("my_research_assistant.prompt.resources")
    def test_file_not_found_error(self, mock_resources):
        """Test PromptFileError is raised when prompt file doesn't exist."""
        mock_resources.files.return_value.joinpath.return_value.open.side_effect = FileNotFoundError()
        
        with pytest.raises(PromptFileError) as exc_info:
            subst_prompt("nonexistent")
        
        assert "nonexistent" in str(exc_info.value)
        assert "Clould not load prompt" in str(exc_info.value)  # Note: original typo preserved
    
    @patch("my_research_assistant.prompt.resources")
    def test_extra_kwargs_ignored(self, mock_resources):
        """Test that extra kwargs are ignored."""
        mock_file_content = "Hello {{name}}!"
        mock_file = mock_open(read_data=mock_file_content)
        mock_resources.files.return_value.joinpath.return_value.open = mock_file
        
        result = subst_prompt("test", name="Alice", extra="ignored")
        
        assert result == "Hello Alice!"
    
    @patch("my_research_assistant.prompt.resources")
    def test_multiline_prompt(self, mock_resources):
        """Test substitution in multiline prompts."""
        mock_file_content = """Title: {{title}}
        
Content: {{content}}
---
End of prompt"""
        mock_file = mock_open(read_data=mock_file_content)
        mock_resources.files.return_value.joinpath.return_value.open = mock_file
        
        result = subst_prompt("test", title="Test Title", content="Test content")
        
        expected = """Title: Test Title
        
Content: Test content
---
End of prompt"""
        assert result == expected
    
    @patch("my_research_assistant.prompt.resources")
    def test_special_characters_in_values(self, mock_resources):
        """Test substitution with special characters in values."""
        mock_file_content = "Text: {{text}}"
        mock_file = mock_open(read_data=mock_file_content)
        mock_resources.files.return_value.joinpath.return_value.open = mock_file
        
        special_text = "Text with {braces} and $pecial characters!"
        result = subst_prompt("test", text=special_text)
        
        assert result == f"Text: {special_text}"


class TestSubstPrompts:
    """Test the subst_prompts function."""
    
    @patch("my_research_assistant.prompt.subst_prompt")
    def test_multiple_prompts(self, mock_subst_prompt):
        """Test combining multiple prompts."""
        mock_subst_prompt.side_effect = ["First prompt", "Second prompt", "Third prompt"]
        
        result = subst_prompts(["prompt1", "prompt2", "prompt3"], var="value")
        
        expected = "First prompt\nSecond prompt\nThird prompt"
        assert result == expected
        
        assert mock_subst_prompt.call_count == 3
        mock_subst_prompt.assert_any_call("prompt1", var="value")
        mock_subst_prompt.assert_any_call("prompt2", var="value")
        mock_subst_prompt.assert_any_call("prompt3", var="value")
    
    @patch("my_research_assistant.prompt.subst_prompt")
    def test_single_prompt(self, mock_subst_prompt):
        """Test with a single prompt."""
        mock_subst_prompt.return_value = "Single prompt"
        
        result = subst_prompts(["prompt1"], var="value")
        
        assert result == "Single prompt"
        mock_subst_prompt.assert_called_once_with("prompt1", var="value")
    
    @patch("my_research_assistant.prompt.subst_prompt")
    def test_empty_list(self, mock_subst_prompt):
        """Test with empty prompt list."""
        result = subst_prompts([], var="value")
        
        assert result == ""
        mock_subst_prompt.assert_not_called()
    
    @patch("my_research_assistant.prompt.subst_prompt")
    def test_propagates_exceptions(self, mock_subst_prompt):
        """Test that exceptions from subst_prompt are propagated."""
        mock_subst_prompt.side_effect = PromptVarError("Missing variable")
        
        with pytest.raises(PromptVarError):
            subst_prompts(["prompt1"], var="value")


class TestIntegration:
    """Integration tests using actual prompt files."""
    
    def test_actual_prompt_file(self):
        """Test with an actual prompt file from the project."""
        result = subst_prompt("base-summary-v1", text_block="This is test content")
        
        assert "This is test content" in result
        assert "Key ideas of the paper" in result
        assert "Implementation approach" in result
        assert "Experiments" in result
        assert "Related work" in result
    
    def test_multiple_actual_prompts(self):
        """Test combining multiple actual prompt files."""
        result = subst_prompts(
            ["base-summary-v1", "improve-summary-v1"],
            text_block="Test content",
            summary="Test summary",
            feedback="Make it better",
            previous_summary="Previous test summary"
        )

        lines = result.split('\n')
        assert len(lines) > 10  # Should have content from both prompts
        assert "Key ideas of the paper" in result
        assert any("improve" in line.lower() for line in lines)