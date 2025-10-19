"""Test the search_arxiv_papers function."""

import pytest
from unittest.mock import patch, MagicMock
from my_research_assistant.arxiv_downloader import (
    search_arxiv_papers,
    _google_search_arxiv_papers,
    get_paper_metadata
)
from my_research_assistant.project_types import PaperMetadata
import datetime


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


class TestGoogleSearchArxivPapers:
    """Tests for the _google_search_arxiv_papers function"""

    def create_mock_metadata(self, paper_id: str, title: str) -> PaperMetadata:
        """Helper to create mock paper metadata"""
        return PaperMetadata(
            paper_id=paper_id,
            title=title,
            published=datetime.datetime(2024, 1, 1),
            updated=datetime.datetime(2024, 1, 1),
            paper_abs_url=f"https://arxiv.org/abs/{paper_id}",
            paper_pdf_url=f"https://arxiv.org/pdf/{paper_id}",
            authors=["Test Author"],
            abstract="Test abstract",
            categories=["Machine Learning"],
            doi=None,
            journal_ref=None,
        )

    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_google_search_arxiv_papers_basic(self, mock_get_metadata, mock_google_search):
        """Test basic functionality of _google_search_arxiv_papers"""
        # Mock Google search to return 3 paper IDs
        mock_google_search.return_value = ["2107.03374", "2308.03873", "2412.19437"]

        # Mock metadata fetching
        mock_get_metadata.side_effect = [
            self.create_mock_metadata("2107.03374", "Paper 1"),
            self.create_mock_metadata("2308.03873", "Paper 2"),
            self.create_mock_metadata("2412.19437", "Paper 3"),
        ]

        # Call the function
        result = _google_search_arxiv_papers("test query")

        # Verify Google search was called with correct parameters
        mock_google_search.assert_called_once_with("test query", k=10)

        # Verify metadata was fetched for each ID
        assert mock_get_metadata.call_count == 3

        # Verify results
        assert len(result) == 3
        assert all(isinstance(paper, PaperMetadata) for paper in result)

    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_google_search_arxiv_papers_deduplication(self, mock_get_metadata, mock_google_search):
        """Test that version deduplication is integrated correctly"""
        # Mock Google search to return multiple versions of same paper
        mock_google_search.return_value = [
            "2107.03374", "2107.03374v1", "2107.03374v2", "2308.03873"
        ]

        # Mock metadata fetching - should only be called for deduplicated IDs
        mock_get_metadata.side_effect = [
            self.create_mock_metadata("2107.03374v2", "Paper 1 v2"),
            self.create_mock_metadata("2308.03873", "Paper 2"),
        ]

        # Call the function
        result = _google_search_arxiv_papers("test query")

        # Should only fetch metadata for 2 papers (deduplicated)
        assert mock_get_metadata.call_count == 2

        # Verify results
        assert len(result) == 2

    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_google_search_arxiv_papers_partial_metadata_failure(
        self, mock_get_metadata, mock_google_search
    ):
        """Test graceful handling when some metadata fetches fail"""
        # Mock Google search to return 3 IDs
        mock_google_search.return_value = ["2107.03374", "2308.03873", "2412.19437"]

        # Mock metadata fetching - one succeeds, two fail
        def metadata_side_effect(paper_id, file_locations=None):
            if paper_id == "2308.03873":
                raise Exception("Paper withdrawn")
            return self.create_mock_metadata(paper_id, f"Paper {paper_id}")

        mock_get_metadata.side_effect = metadata_side_effect

        # Call the function
        result = _google_search_arxiv_papers("test query")

        # Should return 2 papers (the ones that succeeded)
        assert len(result) == 2
        assert all(paper.paper_id in ["2107.03374", "2412.19437"] for paper in result)

    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_google_search_arxiv_papers_all_metadata_failures(
        self, mock_get_metadata, mock_google_search
    ):
        """Test that exception is raised when all metadata fetches fail"""
        # Mock Google search to return 3 IDs
        mock_google_search.return_value = ["2107.03374", "2308.03873", "2412.19437"]

        # Mock all metadata fetches to fail
        mock_get_metadata.side_effect = Exception("Paper withdrawn")

        # Should raise exception when all fail
        with pytest.raises(Exception) as exc_info:
            _google_search_arxiv_papers("test query")

        assert "Failed to fetch metadata for any papers" in str(exc_info.value)

    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_google_search_arxiv_papers_empty_results(
        self, mock_get_metadata, mock_google_search
    ):
        """Test handling of empty results from Google search"""
        # Mock Google search to return empty list
        mock_google_search.return_value = []

        # Call the function
        result = _google_search_arxiv_papers("test query")

        # Should return empty list
        assert result == []

        # Metadata should not be fetched
        mock_get_metadata.assert_not_called()

    @patch('my_research_assistant.google_search.google_search_arxiv')
    def test_google_search_arxiv_papers_google_api_exception(self, mock_google_search):
        """Test that Google API exceptions are propagated"""
        # Mock Google search to raise exception
        mock_google_search.side_effect = Exception("API request failed with status code 429")

        # Should propagate the exception
        with pytest.raises(Exception) as exc_info:
            _google_search_arxiv_papers("test query")

        assert "429" in str(exc_info.value)

    @patch('my_research_assistant.google_search.google_search_arxiv')
    @patch('my_research_assistant.arxiv_downloader.get_paper_metadata')
    def test_google_search_arxiv_papers_calls_google_once(
        self, mock_get_metadata, mock_google_search
    ):
        """Test that Google search is called only once with k=10"""
        # Mock Google search
        mock_google_search.return_value = ["2107.03374"]

        # Mock metadata
        mock_get_metadata.return_value = self.create_mock_metadata("2107.03374", "Paper 1")

        # Call the function
        _google_search_arxiv_papers("test query")

        # Verify single call with k=10
        mock_google_search.assert_called_once_with("test query", k=10)


class TestSearchArxivPapersRouting:
    """Tests for Google search routing in search_arxiv_papers()"""

    def create_mock_metadata(self, paper_id: str, title: str) -> PaperMetadata:
        """Helper to create mock paper metadata"""
        return PaperMetadata(
            paper_id=paper_id,
            title=title,
            published=datetime.datetime(2024, 1, 1),
            updated=datetime.datetime(2024, 1, 1),
            paper_abs_url=f"https://arxiv.org/abs/{paper_id}",
            paper_pdf_url=f"https://arxiv.org/pdf/{paper_id}",
            authors=["Test Author"],
            abstract="Test abstract",
            categories=["Machine Learning"],
            doi=None,
            journal_ref=None,
        )

    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.arxiv_downloader._google_search_arxiv_papers')
    @patch('my_research_assistant.arxiv_downloader._arxiv_keyword_search')
    def test_search_with_google_configured(
        self, mock_arxiv_search, mock_google_search_papers
    ):
        """Test that Google search is used when credentials are configured"""
        # Mock Google search to return papers (already reranked, not sorted yet)
        papers = [
            self.create_mock_metadata("2412.19437", "Paper 3"),
            self.create_mock_metadata("2107.03374", "Paper 1"),
            self.create_mock_metadata("2308.03873", "Paper 2"),
        ]
        mock_google_search_papers.return_value = papers

        # Call search_arxiv_papers
        result = search_arxiv_papers("test query", k=3)

        # Google search should be called
        mock_google_search_papers.assert_called_once_with("test query")

        # ArXiv search should NOT be called
        mock_arxiv_search.assert_not_called()

        # Results should be sorted by paper ID
        assert len(result) == 3
        assert result[0].paper_id == "2107.03374"
        assert result[1].paper_id == "2308.03873"
        assert result[2].paper_id == "2412.19437"

    @patch('my_research_assistant.google_search.API_KEY', None)
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.arxiv_downloader._google_search_arxiv_papers')
    @patch('my_research_assistant.arxiv_downloader._arxiv_keyword_search')
    def test_search_without_google_api_key(
        self, mock_arxiv_search, mock_google_search_papers
    ):
        """Test that ArXiv search is used when API key is not configured"""
        # Mock ArXiv search to return papers
        papers = [
            self.create_mock_metadata("2412.19437", "Paper 3"),
            self.create_mock_metadata("2107.03374", "Paper 1"),
        ]
        mock_arxiv_search.return_value = papers

        # Call search_arxiv_papers
        result = search_arxiv_papers("test query", k=2, candidate_limit=50)

        # ArXiv search should be called
        mock_arxiv_search.assert_called_once_with("test query", max_results=50)

        # Google search should NOT be called
        mock_google_search_papers.assert_not_called()

        # Results should be sorted by paper ID
        assert len(result) == 2
        assert result[0].paper_id == "2107.03374"
        assert result[1].paper_id == "2412.19437"

    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', '')
    @patch('my_research_assistant.arxiv_downloader._google_search_arxiv_papers')
    @patch('my_research_assistant.arxiv_downloader._arxiv_keyword_search')
    def test_search_without_google_engine_id(
        self, mock_arxiv_search, mock_google_search_papers
    ):
        """Test that ArXiv search is used when engine ID is empty"""
        # Mock ArXiv search
        papers = [self.create_mock_metadata("2107.03374", "Paper 1")]
        mock_arxiv_search.return_value = papers

        # Call search_arxiv_papers
        result = search_arxiv_papers("test query", k=1)

        # ArXiv search should be called
        mock_arxiv_search.assert_called_once()

        # Google search should NOT be called
        mock_google_search_papers.assert_not_called()

    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.arxiv_downloader._google_search_arxiv_papers')
    def test_search_google_returns_more_than_k(self, mock_google_search_papers):
        """Test that results are limited to k even with Google search"""
        # Mock Google search to return 5 papers
        papers = [
            self.create_mock_metadata("2107.03374", "Paper 1"),
            self.create_mock_metadata("2202.00001", "Paper 2"),
            self.create_mock_metadata("2308.03873", "Paper 3"),
            self.create_mock_metadata("2401.12345", "Paper 4"),
            self.create_mock_metadata("2412.19437", "Paper 5"),
        ]
        mock_google_search_papers.return_value = papers

        # Request only 3 papers
        result = search_arxiv_papers("test query", k=3)

        # Should return only 3 papers (first 3 after sorting by ID)
        assert len(result) == 3
        assert result[0].paper_id == "2107.03374"
        assert result[1].paper_id == "2202.00001"
        assert result[2].paper_id == "2308.03873"

    @patch('my_research_assistant.google_search.API_KEY', 'test_key')
    @patch('my_research_assistant.google_search.SEARCH_ENGINE_ID', 'test_engine_id')
    @patch('my_research_assistant.arxiv_downloader._google_search_arxiv_papers')
    def test_search_google_returns_empty(self, mock_google_search_papers):
        """Test handling of empty results from Google search"""
        # Mock Google search to return empty list
        mock_google_search_papers.return_value = []

        # Call search_arxiv_papers
        result = search_arxiv_papers("test query", k=5)

        # Should return empty list
        assert result == []
