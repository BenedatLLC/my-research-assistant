"""
Tests for the models module configuration.

These tests verify that the LLM and embedding models are properly configured
and can successfully make API calls.
"""

import pytest


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
