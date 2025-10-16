import pytest
import os
from my_research_assistant.google_search import (
    extract_arxiv_id,
    google_search_arxiv,
    GoogleSearchNotConfigured
)


class TestExtractArxivId:
    """Tests for the extract_arxiv_id function"""
    
    def test_modern_identifier_abs(self):
        """Test extraction from abs URL with modern identifier"""
        url = "https://arxiv.org/abs/2510.11694"
        assert extract_arxiv_id(url) == "2510.11694"
    
    def test_modern_identifier_pdf(self):
        """Test extraction from PDF URL with modern identifier"""
        url = "https://arxiv.org/pdf/2510.11694"
        assert extract_arxiv_id(url) == "2510.11694"
    
    def test_modern_identifier_html_with_version(self):
        """Test extraction from HTML URL with version"""
        url = "https://arxiv.org/html/2510.11694v1"
        assert extract_arxiv_id(url) == "2510.11694v1"
    
    def test_modern_identifier_abs_with_version(self):
        """Test extraction from abs URL with version"""
        url = "https://arxiv.org/abs/2504.16736v3"
        assert extract_arxiv_id(url) == "2504.16736v3"
    
    def test_modern_identifier_with_extension(self):
        """Test extraction with .pdf extension"""
        url = "https://arxiv.org/pdf/2107.03374v2.pdf"
        assert extract_arxiv_id(url) == "2107.03374v2"
    
    def test_modern_identifier_4_digits(self):
        """Test extraction with 4-digit sequence number (pre-2015)"""
        url = "https://arxiv.org/abs/0704.0001"
        assert extract_arxiv_id(url) == "0704.0001"
    
    def test_modern_identifier_4_digits_with_version(self):
        """Test extraction with 4-digit sequence number and version"""
        url = "https://arxiv.org/abs/1412.9999v2"
        assert extract_arxiv_id(url) == "1412.9999v2"
    
    def test_legacy_identifier_simple(self):
        """Test extraction with legacy identifier format"""
        url = "https://arxiv.org/abs/hep-th/9901001"
        assert extract_arxiv_id(url) == "hep-th/9901001"
    
    def test_legacy_identifier_with_subject_class(self):
        """Test extraction with legacy identifier with subject class"""
        url = "https://arxiv.org/abs/math.GT/0601001"
        assert extract_arxiv_id(url) == "math.GT/0601001"
    
    def test_invalid_url(self):
        """Test that invalid URLs return None"""
        url = "https://example.com/not-an-arxiv-url"
        assert extract_arxiv_id(url) is None
    
    def test_empty_string(self):
        """Test that empty string returns None"""
        assert extract_arxiv_id("") is None


class TestGoogleSearchArxiv:
    """Tests for the google_search_arxiv function"""
    
    @pytest.fixture
    def api_keys_available(self):
        """Check if API keys are available"""
        return (
            os.environ.get("GOOGLE_SEARCH_API_KEY") is not None and
            os.environ.get("GOOGLE_SEARCH_ENGINE_ID") is not None
        )
    
    @pytest.mark.skipif(
        os.environ.get("GOOGLE_SEARCH_API_KEY") is None or
        os.environ.get("GOOGLE_SEARCH_ENGINE_ID") is None,
        reason="Google Search API keys not configured"
    )
    def test_search_returns_paper_ids(self):
        """Test that search returns arXiv paper IDs"""
        query = "Evaluating Large Language Models Trained on Code"
        results = google_search_arxiv(query, k=10, verbose=False)
        
        # Should return a list
        assert isinstance(results, list)
        
        # Should have results
        assert len(results) > 0
        
        # All results should be strings
        assert all(isinstance(paper_id, str) for paper_id in results)
        
        # Should contain the expected paper (2107.03374 or with version)
        assert any(
            paper_id in ["2107.03374", "2107.03374v2"] or paper_id.startswith("2107.03374")
            for paper_id in results
        ), f"Expected paper 2107.03374 not found in results: {results}"
    
    @pytest.mark.skipif(
        os.environ.get("GOOGLE_SEARCH_API_KEY") is None or
        os.environ.get("GOOGLE_SEARCH_ENGINE_ID") is None,
        reason="Google Search API keys not configured"
    )
    def test_search_with_limit(self):
        """Test that search respects the k parameter"""
        query = "Evaluating Large Language Models Trained on Code"
        results = google_search_arxiv(query, k=5, verbose=False)
        
        # Should return at most k results
        assert len(results) <= 5
    
    @pytest.mark.skipif(
        os.environ.get("GOOGLE_SEARCH_API_KEY") is None or
        os.environ.get("GOOGLE_SEARCH_ENGINE_ID") is None,
        reason="Google Search API keys not configured"
    )
    def test_search_verbose_mode(self, capsys):
        """Test that verbose mode prints output"""
        query = "Evaluating Large Language Models Trained on Code"
        results = google_search_arxiv(query, k=3, verbose=True)
        
        # Should still return results
        assert len(results) > 0
        
        # Check that output was printed
        captured = capsys.readouterr()
        assert "Search Results for:" in captured.out
        assert query in captured.out
        assert "URL:" in captured.out
    
    def test_missing_api_key_raises_exception(self, monkeypatch):
        """Test that missing API keys raise GoogleSearchNotConfigured"""
        # Remove API keys from environment
        monkeypatch.delenv("GOOGLE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)
        
        # Need to reload the module to pick up the None values
        import importlib
        import my_research_assistant.google_search as gs_module
        importlib.reload(gs_module)
        
        query = "test query"
        with pytest.raises(GoogleSearchNotConfigured) as exc_info:
            gs_module.google_search_arxiv(query)
        
        assert "credentials not configured" in str(exc_info.value).lower()


