"""Tests for correct ordering between list and summary commands."""

import pytest
from unittest.mock import Mock, patch
from my_research_assistant.workflow import WorkflowRunner
from my_research_assistant.paper_manager import resolve_paper_reference
from my_research_assistant.project_types import PaperMetadata
from datetime import datetime


def create_test_paper(paper_id: str, title: str, authors: list[str] = None) -> PaperMetadata:
    """Helper to create test paper metadata with required fields."""
    if authors is None:
        authors = ["Test Author"]

    return PaperMetadata(
        paper_id=paper_id,
        title=title,
        authors=authors,
        abstract=f"Abstract for {title}",
        published=datetime(2025, 1, 1),
        updated=datetime(2025, 1, 1),
        paper_abs_url=f"https://arxiv.org/abs/{paper_id}",
        paper_pdf_url=f"https://arxiv.org/pdf/{paper_id}.pdf",
        categories=["cs.AI"],
        doi=None,
        journal_ref=None
    )


class TestListSummaryOrdering:
    """Test that summary command uses the same ordering as list command."""

    def test_resolve_paper_reference_with_numbers(self):
        """Test that paper numbers resolve to the correct papers in order."""
        # Create test papers in a specific order
        papers = [
            create_test_paper("2507.20534v1", "Kimi K2: Open Agentic Intelligence", ["Author A"]),
            create_test_paper("2412.19437v2", "DeepSeek-V3 Technical Report", ["Author B"])
        ]

        # Test that paper number 1 returns the first paper
        paper, error = resolve_paper_reference("1", papers, "test")
        assert error == ""
        assert paper is not None
        assert paper.paper_id == "2507.20534v1"

        # Test that paper number 2 returns the second paper
        paper, error = resolve_paper_reference("2", papers, "test")
        assert error == ""
        assert paper is not None
        assert paper.paper_id == "2412.19437v2"

    def test_resolve_paper_reference_with_paper_ids(self):
        """Test that exact paper IDs work correctly."""
        papers = [
            create_test_paper("2507.20534v1", "Kimi K2", ["Author A"]),
            create_test_paper("2412.19437v2", "DeepSeek-V3", ["Author B"])
        ]

        # Test exact paper ID match
        paper, error = resolve_paper_reference("2507.20534v1", papers, "test")
        assert error == ""
        assert paper is not None
        assert paper.paper_id == "2507.20534v1"

        paper, error = resolve_paper_reference("2412.19437v2", papers, "test")
        assert error == ""
        assert paper is not None
        assert paper.paper_id == "2412.19437v2"

    @pytest.mark.asyncio
    async def test_list_workflow_returns_sorted_paper_ids(self):
        """Test that list workflow returns paper IDs in the same order as display."""
        mock_llm = Mock()
        mock_interface = Mock()

        # Mock papers in download order (unsorted)
        download_order_ids = ["2507.20534v1", "2412.19437v2"]

        mock_papers = [
            create_test_paper("2507.20534v1", "Kimi K2", ["Author A"]),
            create_test_paper("2412.19437v2", "DeepSeek-V3", ["Author B"])
        ]

        runner = WorkflowRunner(mock_llm, mock_interface)

        # Mock the functions that get paper data
        with patch('my_research_assistant.arxiv_downloader.get_downloaded_paper_ids') as mock_get_ids, \
             patch('my_research_assistant.arxiv_downloader.get_paper_metadata') as mock_get_metadata:

            # Return papers in download order
            mock_get_ids.return_value = download_order_ids

            # Return appropriate metadata for each ID
            def get_metadata_side_effect(paper_id):
                for paper in mock_papers:
                    if paper.paper_id == paper_id:
                        return paper
                return None

            mock_get_metadata.side_effect = get_metadata_side_effect

            # Run the list workflow
            result = await runner.get_list_of_papers()

            # Verify success
            assert result.success is True
            assert len(result.papers) == 2
            assert len(result.paper_ids) == 2

            # Verify papers are sorted by paper ID (alphabetically)
            assert result.papers[0].paper_id == "2412.19437v2"  # DeepSeek comes first alphabetically
            assert result.papers[1].paper_id == "2507.20534v1"  # Kimi comes second

            # CRITICAL: Verify paper_ids are in the same order as sorted papers
            assert result.paper_ids[0] == "2412.19437v2"  # First in display = first in paper_ids
            assert result.paper_ids[1] == "2507.20534v1"  # Second in display = second in paper_ids

    def test_list_summary_consistency_scenario(self):
        """Test the exact scenario described in the issue."""
        # Simulate the problematic scenario:
        # 1. Papers downloaded in order: Kimi, DeepSeek
        # 2. List shows them sorted: 1. DeepSeek, 2. Kimi
        # 3. summary 1 should get DeepSeek (first in list), not Kimi (first downloaded)

        # Papers in the order they would be displayed (sorted by ID)
        displayed_papers = [
            create_test_paper("2412.19437v2", "DeepSeek-V3 Technical Report", ["DeepSeek Team"]),  # DeepSeek - appears first in sorted list
            create_test_paper("2507.20534v1", "Kimi K2: Open Agentic Intelligence", ["Kimi Team"])  # Kimi - appears second in sorted list
        ]

        # Test that "summary 1" gets the first paper in the displayed list (DeepSeek)
        paper, error = resolve_paper_reference("1", displayed_papers, "summary")
        assert error == ""
        assert paper is not None
        assert paper.paper_id == "2412.19437v2"
        assert "DeepSeek" in paper.title

        # Test that "summary 2" gets the second paper in the displayed list (Kimi)
        paper, error = resolve_paper_reference("2", displayed_papers, "summary")
        assert error == ""
        assert paper is not None
        assert paper.paper_id == "2507.20534v1"
        assert "Kimi" in paper.title

    def test_out_of_range_paper_numbers(self):
        """Test error handling for invalid paper numbers."""
        papers = [
            create_test_paper("2507.20534v1", "Test Paper", ["Author"])
        ]

        # Test number too high
        paper, error = resolve_paper_reference("2", papers, "summary")
        assert paper is None
        assert "Invalid paper number '2'" in error
        assert "Choose 1-1" in error

        # Test number too low
        paper, error = resolve_paper_reference("0", papers, "summary")
        assert paper is None
        assert "Invalid paper number '0'" in error

        # Test negative number
        paper, error = resolve_paper_reference("-1", papers, "summary")
        assert paper is None
        assert "Invalid paper number '-1'" in error

    def test_nonexistent_paper_id(self):
        """Test error handling for nonexistent paper IDs."""
        papers = [
            create_test_paper("2507.20534v1", "Test Paper", ["Author"])
        ]

        # Test nonexistent paper ID
        paper, error = resolve_paper_reference("9999.99999", papers, "summary")
        assert paper is None
        assert "Paper '9999.99999' not found" in error