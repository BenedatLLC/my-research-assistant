"""Test the search_arxiv_papers function."""

import pytest
from my_research_assistant.arxiv_downloader import search_arxiv_papers


def test_search_arxiv_papers_basic():
    """Test basic functionality of search_arxiv_papers."""
    
    # Test with a specific query
    results = search_arxiv_papers("machine learning", k=2, candidate_limit=5)
    
    # Should return results
    assert len(results) > 0, "Expected at least one result"
    assert len(results) <= 2, "Should not return more than k results"
    
    # Check that results are properly formatted
    for paper in results:
        assert hasattr(paper, 'title'), "Paper should have title"
        assert hasattr(paper, 'authors'), "Paper should have authors"
        assert hasattr(paper, 'paper_id'), "Paper should have paper_id"
        assert hasattr(paper, 'abstract'), "Paper should have abstract"
        assert paper.title, "Title should not be empty"
        assert paper.authors, "Authors should not be empty"
        assert paper.paper_id, "Paper ID should not be empty"


def test_search_arxiv_papers_edge_cases():
    """Test edge cases for search_arxiv_papers."""
    
    # Test when candidate_limit is smaller than k
    results = search_arxiv_papers("neural networks", k=5, candidate_limit=2)
    assert len(results) <= 2, "Should not return more results than candidates found"
    
    # Test with k=1 (default)
    results = search_arxiv_papers("artificial intelligence")
    assert len(results) == 1, "Should return exactly 1 result when k=1"


def test_search_arxiv_papers_fallback():
    """Test that the function works even without OpenAI embeddings."""
    import os
    
    # Temporarily remove OpenAI API key to test fallback
    original_key = os.environ.get('OPENAI_API_KEY')
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    try:
        results = search_arxiv_papers("deep learning", k=1, candidate_limit=3)
        
        # Should still work with text-based fallback
        assert len(results) >= 1, "Fallback should still return results"
        assert results[0].title, "Result should have a title"
        
    finally:
        # Restore the original API key
        if original_key is not None:
            os.environ['OPENAI_API_KEY'] = original_key
