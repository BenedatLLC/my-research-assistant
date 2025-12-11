"""
Tests for the models module configuration.

These tests verify that the LLM and embedding models are properly configured
and can successfully make API calls.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from llama_index.core import MockEmbedding


def test_llm():
    """Test that the default LLM model can be obtained and used successfully."""
    from my_research_assistant.models import get_default_model

    # Get the default model
    llm = get_default_model()

    # Make a simple completion call
    prompt = "What is 2+2? Answer with just the number."
    response = llm.complete(prompt)

    # Validate that we got a response
    assert response is not None, "LLM should return a response"
    assert hasattr(response, 'text'), "Response should have a text attribute"
    assert len(response.text) > 0, "Response text should not be empty"
    assert '4' in response.text, "Response should contain the answer"

    print(f"LLM test successful. Response: {response.text.strip()}")


def test_embedder():
    """Test that the default embedding model can be obtained and used successfully."""
    from llama_index.core import Settings

    # Get the embedding model from Settings
    embed_model = Settings.embed_model

    # Make a simple embedding call
    test_text = "This is a test sentence for embedding."
    embedding = embed_model.get_text_embedding(test_text)

    # Validate that we got an embedding
    assert embedding is not None, "Embedder should return an embedding"
    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) > 0, "Embedding should not be empty"

    # OpenAI embeddings are typically 1536 dimensions for text-embedding-ada-002
    # or other dimensions for different models
    assert len(embedding) >= 1024, "Embedding dimension should be reasonable (at least 1024)"

    # Check that the values are floats
    assert all(isinstance(val, float) for val in embedding[:10]), "Embedding values should be floats"

    print(f"Embedder test successful. Embedding dimension: {len(embedding)}")


def test_llm_caching():
    """Test that the LLM model caching works correctly."""
    from my_research_assistant.models import get_default_model

    # Get the default model twice with same kwargs
    llm1 = get_default_model()
    llm2 = get_default_model()

    # They should be the same object (cached)
    assert llm1 is llm2, "Same model should be returned from cache"

    # Get with different kwargs
    llm3 = get_default_model(temperature=0.5)

    # This should be a different object
    assert llm1 is not llm3, "Different kwargs should return a new model instance"

    print("LLM caching test successful")


def test_embedder_batch():
    """Test that the embedding model can handle batch processing."""
    from llama_index.core import Settings

    # Get the embedding model from Settings
    embed_model = Settings.embed_model

    # Make a batch embedding call
    test_texts = [
        "First test sentence.",
        "Second test sentence.",
        "Third test sentence."
    ]
    embeddings = embed_model.get_text_embedding_batch(test_texts)

    # Validate that we got embeddings for all texts
    assert embeddings is not None, "Embedder should return embeddings"
    assert isinstance(embeddings, list), "Embeddings should be a list"
    assert len(embeddings) == len(test_texts), "Should get one embedding per input text"

    # Check each embedding
    for i, embedding in enumerate(embeddings):
        assert isinstance(embedding, list), f"Embedding {i} should be a list"
        assert len(embedding) > 0, f"Embedding {i} should not be empty"
        assert len(embedding) >= 1024, f"Embedding {i} dimension should be reasonable"

    print(f"Embedder batch test successful. Processed {len(test_texts)} texts")


# Helper class for testing embedding failures
class FailingEmbedding(MockEmbedding):
    """MockEmbedding that raises an exception when get_text_embedding is called."""

    _error_message: str = "Embedding error"  # Class variable to store error message

    def __init__(self, error_message="Embedding error"):
        super().__init__(embed_dim=1536)
        FailingEmbedding._error_message = error_message

    def get_text_embedding(self, text):
        raise Exception(FailingEmbedding._error_message)


# Tests for the check-models command (main function)

def test_check_models_success(capsys):
    """Test check-models command when both models work correctly."""
    from my_research_assistant.check_models import main
    from llama_index.core import Settings, MockEmbedding

    # Mock successful LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.text = "test"

    mock_llm = MagicMock()
    mock_llm.complete.return_value = mock_llm_response

    # Use MockEmbedding from LlamaIndex (valid BaseEmbedding)
    mock_embed = MockEmbedding(embed_dim=1536)

    # Save original embed_model to restore later
    original_embed_model = Settings.embed_model

    try:
        Settings.embed_model = mock_embed

        with patch('sys.argv', ['check-models']):
            with patch('my_research_assistant.models.get_default_model', return_value=mock_llm):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with 0 (success)
                assert exc_info.value.code == 0

                # Check output
                captured = capsys.readouterr()
                assert "✓ LLM is working correctly" in captured.out
                assert "✓ Embedding model is working correctly" in captured.out
                assert "✓ All model checks passed!" in captured.out
    finally:
        Settings.embed_model = original_embed_model


def test_check_models_llm_failure(capsys):
    """Test check-models command when LLM fails."""
    from my_research_assistant.check_models import main
    from llama_index.core import Settings, MockEmbedding

    # Use MockEmbedding from LlamaIndex (valid BaseEmbedding)
    mock_embed = MockEmbedding(embed_dim=1536)

    # Save original embed_model to restore later
    original_embed_model = Settings.embed_model

    try:
        Settings.embed_model = mock_embed

        with patch('sys.argv', ['check-models']):
            with patch('my_research_assistant.models.get_default_model') as mock_llm:
                # Simulate API key error
                mock_llm.side_effect = Exception("Invalid API key")

                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with 1 (failure)
                assert exc_info.value.code == 1

                # Check output
                captured = capsys.readouterr()
                assert "❌ LLM test failed" in captured.out
                assert "Suggestions:" in captured.out
                # Embedding model should still be tested and succeed
                assert "Testing embedding model" in captured.out
                assert "✓ Embedding model is working correctly" in captured.out
    finally:
        Settings.embed_model = original_embed_model


def test_check_models_embedding_failure(capsys):
    """Test check-models command when embedding model fails."""
    from my_research_assistant.check_models import main
    from llama_index.core import Settings

    # Mock successful LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.text = "test"

    mock_llm = MagicMock()
    mock_llm.complete.return_value = mock_llm_response

    # Use FailingEmbedding that raises error
    failing_embed = FailingEmbedding("Connection timeout")

    # Save original embed_model to restore later
    original_embed_model = Settings.embed_model

    try:
        Settings.embed_model = failing_embed

        with patch('sys.argv', ['check-models']):
            with patch('my_research_assistant.models.get_default_model', return_value=mock_llm):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with 1 (failure)
                assert exc_info.value.code == 1

                # Check output
                captured = capsys.readouterr()
                assert "❌ Embedding model test failed" in captured.out
                assert "Suggestions:" in captured.out
                # LLM should succeed
                assert "✓ LLM is working correctly" in captured.out
    finally:
        Settings.embed_model = original_embed_model


def test_check_models_both_failure(capsys):
    """Test check-models command when both models fail."""
    from my_research_assistant.check_models import main
    from llama_index.core import Settings

    # Use FailingEmbedding that raises error
    failing_embed = FailingEmbedding("Embedding error")

    # Save original embed_model to restore later
    original_embed_model = Settings.embed_model

    try:
        Settings.embed_model = failing_embed

        with patch('sys.argv', ['check-models']):
            with patch('my_research_assistant.models.get_default_model') as mock_llm:
                # Both fail
                mock_llm.side_effect = Exception("LLM error")

                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with 1 (failure)
                assert exc_info.value.code == 1

                # Check output
                captured = capsys.readouterr()
                assert "❌ LLM test failed" in captured.out
                assert "❌ Embedding model test failed" in captured.out
                assert "❌ Some model checks failed" in captured.out
    finally:
        Settings.embed_model = original_embed_model


def test_check_models_verbose_flag(capsys):
    """Test check-models command with --verbose flag."""
    from my_research_assistant.check_models import main
    from llama_index.core import Settings

    # Use MockEmbedding from LlamaIndex (valid BaseEmbedding)
    mock_embed = MockEmbedding(embed_dim=1536)

    # Save original embed_model to restore later
    original_embed_model = Settings.embed_model

    try:
        Settings.embed_model = mock_embed

        with patch('sys.argv', ['check-models', '--verbose']):
            with patch('my_research_assistant.models.get_default_model') as mock_llm:
                # Simulate error to test verbose output
                mock_llm.side_effect = Exception("Test error")

                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Check output includes traceback
                captured = capsys.readouterr()
                assert "Full traceback:" in captured.out
                assert "Traceback" in captured.out or "traceback" in captured.out.lower()
    finally:
        Settings.embed_model = original_embed_model


def test_error_suggestions_api_key():
    """Test error suggestions for API key issues."""
    from my_research_assistant.check_models import _get_error_suggestions

    error = Exception("Invalid API key provided")
    suggestions = _get_error_suggestions(error, 'https://api.openai.com/v1')

    assert "OPENAI_API_KEY" in suggestions
    assert "API key" in suggestions or "api key" in suggestions.lower()


def test_error_suggestions_connection():
    """Test error suggestions for connection issues."""
    from my_research_assistant.check_models import _get_error_suggestions

    error = Exception("Connection timeout occurred")
    suggestions = _get_error_suggestions(error, 'https://api.openai.com/v1')

    assert "connection" in suggestions.lower() or "internet" in suggestions.lower()


def test_error_suggestions_rate_limit():
    """Test error suggestions for rate limit issues."""
    from my_research_assistant.check_models import _get_error_suggestions

    error = Exception("Rate limit exceeded")
    suggestions = _get_error_suggestions(error, 'https://api.openai.com/v1')

    assert "rate limit" in suggestions.lower() or "quota" in suggestions.lower()


def test_error_suggestions_timeout():
    """Test error suggestions for timeout issues."""
    from my_research_assistant.check_models import _get_error_suggestions, TimeoutError

    error = TimeoutError("Operation timed out after 20 seconds")
    suggestions = _get_error_suggestions(error, 'https://api.openai.com/v1')

    assert "timeout" in suggestions.lower() or "timed out" in suggestions.lower()
    assert "--timeout" in suggestions


def test_check_models_timeout_option(capsys):
    """Test check-models command with custom timeout."""
    from my_research_assistant.check_models import main
    from llama_index.core import Settings

    # Mock successful LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.text = "test"

    mock_llm = MagicMock()
    mock_llm.complete.return_value = mock_llm_response

    # Use MockEmbedding from LlamaIndex (valid BaseEmbedding)
    mock_embed = MockEmbedding(embed_dim=1536)

    # Save original embed_model to restore later
    original_embed_model = Settings.embed_model

    try:
        Settings.embed_model = mock_embed

        with patch('sys.argv', ['check-models', '--timeout', '5']):
            with patch('my_research_assistant.models.get_default_model', return_value=mock_llm):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with 0 (success)
                assert exc_info.value.code == 0

                # Check output includes timeout value
                captured = capsys.readouterr()
                assert "timeout: 5" in captured.out or "timeout: 5.0" in captured.out
    finally:
        Settings.embed_model = original_embed_model


def test_run_with_timeout_success():
    """Test _run_with_timeout with a function that completes."""
    from my_research_assistant.check_models import _run_with_timeout

    def quick_func():
        return "success"

    result = _run_with_timeout(quick_func, 1.0)
    assert result == "success"


def test_run_with_timeout_timeout():
    """Test _run_with_timeout with a function that times out."""
    import time
    from my_research_assistant.check_models import _run_with_timeout, TimeoutError

    def slow_func():
        time.sleep(10)
        return "too late"

    with pytest.raises(TimeoutError) as exc_info:
        _run_with_timeout(slow_func, 0.5)

    assert "timed out after 0.5 seconds" in str(exc_info.value)


def test_run_with_timeout_exception():
    """Test _run_with_timeout with a function that raises an exception."""
    from my_research_assistant.check_models import _run_with_timeout

    def failing_func():
        raise ValueError("test error")

    with pytest.raises(ValueError) as exc_info:
        _run_with_timeout(failing_func, 1.0)

    assert "test error" in str(exc_info.value)


def test_reasoning_model():
    """Test that the reasoning model can be obtained and used successfully."""
    from my_research_assistant.models import get_reasoning_model

    # Get the reasoning model
    llm = get_reasoning_model()

    # Make a simple completion call
    prompt = "What is 2+2? Answer with just the number."
    response = llm.complete(prompt)

    # Validate that we got a response
    assert response is not None, "Reasoning model should return a response"
    assert hasattr(response, 'text'), "Response should have a text attribute"
    assert len(response.text) > 0, "Response text should not be empty"
    assert '4' in response.text, "Response should contain the answer"

    print(f"Reasoning model test successful. Response: {response.text.strip()}")


def test_reasoning_model_caching():
    """Test that the reasoning model caching works correctly."""
    from my_research_assistant.models import get_reasoning_model

    # Get the reasoning model twice with same kwargs
    llm1 = get_reasoning_model()
    llm2 = get_reasoning_model()

    # They should be the same object (cached)
    assert llm1 is llm2, "Same reasoning model should be returned from cache"

    # Get with different kwargs
    llm3 = get_reasoning_model(temperature=0.5)

    # This should be a different object
    assert llm1 is not llm3, "Different kwargs should return a new reasoning model instance"

    print("Reasoning model caching test successful")


def test_reasoning_model_default():
    """Test that the reasoning model uses the correct default."""
    from my_research_assistant.models import DEFAULT_REASONING_MODEL
    import os

    # Check that the default is gpt-5.1 (unless overridden by env var)
    if 'DEFAULT_REASONING_MODEL' not in os.environ:
        assert DEFAULT_REASONING_MODEL == 'gpt-5.1', "Default reasoning model should be gpt-5.1"

    print(f"Reasoning model default test successful. Default: {DEFAULT_REASONING_MODEL}")


def test_reasoning_model_env_var():
    """Test that the reasoning model respects the environment variable."""
    import os
    from unittest.mock import patch
    import importlib
    import my_research_assistant.models as models_module

    # Test with custom environment variable
    with patch.dict(os.environ, {'DEFAULT_REASONING_MODEL': 'gpt-4o'}):
        # Need to reload the module to pick up the new env var
        importlib.reload(models_module)

        from my_research_assistant.models import DEFAULT_REASONING_MODEL
        assert DEFAULT_REASONING_MODEL == 'gpt-4o', "Should use environment variable value"

    # Reload again OUTSIDE the patch context to restore original state
    importlib.reload(models_module)

    print("Reasoning model environment variable test successful")


def test_check_models_loglevel_option(capsys):
    """Test check-models command with --loglevel option."""
    from my_research_assistant.check_models import main
    from llama_index.core import Settings

    # Mock successful LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.text = "test"

    mock_llm = MagicMock()
    mock_llm.complete.return_value = mock_llm_response

    # Use MockEmbedding from LlamaIndex (valid BaseEmbedding)
    mock_embed = MockEmbedding(embed_dim=1536)

    # Save original embed_model to restore later
    original_embed_model = Settings.embed_model

    try:
        Settings.embed_model = mock_embed

        with patch('sys.argv', ['check-models', '--loglevel', 'DEBUG']):
            with patch('my_research_assistant.models.get_default_model', return_value=mock_llm):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with 0 (success)
                assert exc_info.value.code == 0

                # Check that the command still works with logging enabled
                captured = capsys.readouterr()
                assert "✓ LLM is working correctly" in captured.out
                assert "✓ Embedding model is working correctly" in captured.out
    finally:
        Settings.embed_model = original_embed_model
