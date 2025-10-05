"""Tests to ensure the find command (start_add_paper_workflow) displays papers in ascending paper_id order.

This guards against regressions of the bug where papers were displayed in relevance
order while the internal state stored sorted paper ids, causing mismatched numeric
selection for summarize commands.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from my_research_assistant.workflow import WorkflowRunner
from my_research_assistant.project_types import PaperMetadata
from my_research_assistant.interface_adapter import InterfaceAdapter


def make_paper(paper_id: str, title: str) -> PaperMetadata:
    return PaperMetadata(
        paper_id=paper_id,
        title=title,
        authors=["Author One", "Author Two"],
        abstract=f"Abstract for {title}",
        published=datetime(2025, 1, 1),
        updated=None,
        paper_abs_url=f"https://arxiv.org/abs/{paper_id}",
        paper_pdf_url=f"https://arxiv.org/pdf/{paper_id}.pdf",
        categories=["Artificial Intelligence"],
        doi=None,
        journal_ref=None,
    )


@pytest.mark.asyncio
async def test_find_results_are_sorted_by_paper_id(tmp_path, monkeypatch):
    """The papers returned from start_add_paper_workflow must be sorted by paper_id ascending.

    We simulate search_arxiv_papers returning papers in relevance order (unsorted ids)
    and assert that the interface receives them sorted, and the QueryResult ordering matches.
    """
    mock_llm = Mock()

    # Mock interface adapter
    mock_interface = Mock(spec=InterfaceAdapter)
    mock_interface.display_papers = Mock()
    mock_interface.progress_context = Mock()
    mock_interface.progress_context.return_value.__enter__ = Mock()
    mock_interface.progress_context.return_value.__exit__ = Mock()

    # Create isolated file locations rooted at tmp_path
    from my_research_assistant.file_locations import FileLocations, FILE_LOCATIONS as GLOBAL_FL
    test_fl = FileLocations.get_locations(str(tmp_path))
    # Monkeypatch the global FILE_LOCATIONS used by workflow components
    monkeypatch.setattr("my_research_assistant.file_locations.FILE_LOCATIONS", test_fl, raising=True)
    runner = WorkflowRunner(mock_llm, mock_interface, file_locations=test_fl)

    # Relevance order (unsorted lexicographically by id)
    unsorted_papers = [
        make_paper("2507.20534v1", "Kimi K2: Open Agentic Intelligence"),
        make_paper("2412.19437v2", "DeepSeek-V3 Technical Report"),
        make_paper("2503.22738v1", "ShieldAgent: Safety Reasoning"),
    ]

    with patch("my_research_assistant.workflow.search_arxiv_papers") as mock_search:
        mock_search.return_value = unsorted_papers

        result = await runner.start_add_paper_workflow("agent intelligence")

        # Ensure success and same number of papers
        assert result.success is True
        assert len(result.papers) == 3

        # Verify interface.display_papers called once
        mock_interface.display_papers.assert_called_once()
        displayed = mock_interface.display_papers.call_args[0][0]

        # Ascending by paper_id expected
        expected_ids = sorted([p.paper_id for p in unsorted_papers])
        displayed_ids = [p.paper_id for p in displayed]
        result_ids = [p.paper_id for p in result.papers]

        assert displayed_ids == expected_ids, "Displayed ordering must be ascending by paper_id"
        assert result_ids == expected_ids, "Returned QueryResult.papers ordering must match ascending paper_id"
        assert result.paper_ids == expected_ids, "QueryResult.paper_ids must be ascending and consistent"

        # Confirm no in-place modification side-effects beyond sorting
        # (i.e., all original objects still present)
        assert set(displayed_ids) == set(p.paper_id for p in unsorted_papers)
