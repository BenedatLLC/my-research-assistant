"""Utilities for managing paper collections and resolving paper references."""

import os
from typing import List, Optional, Tuple
from .project_types import PaperMetadata
from .file_locations import FileLocations


def get_papers_by_ids(paper_ids: List[str], file_locations: FileLocations) -> List[PaperMetadata]:
    """Get paper metadata objects for a list of paper IDs.

    Args:
        paper_ids: List of paper IDs to retrieve
        file_locations: File locations configuration

    Returns:
        List of PaperMetadata objects for found papers
    """
    from .arxiv_downloader import get_paper_metadata

    papers = []
    for paper_id in paper_ids:
        try:
            paper = get_paper_metadata(paper_id)
            if paper:
                papers.append(paper)
        except Exception:
            # Skip papers that can't be loaded
            continue

    return papers


def resolve_paper_reference(
    reference: str,
    available_papers: List[PaperMetadata],
    context: str = "selection"
) -> Tuple[Optional[PaperMetadata], str]:
    """Resolve a paper reference (number or ID) to a paper.

    Args:
        reference: User input - either a number (1, 2, 3...) or paper ID
        available_papers: List of papers currently available
        context: Context for error messages ("selection", "summary", etc.)

    Returns:
        Tuple of (PaperMetadata if found, error_message if not found)
    """
    if not available_papers:
        return None, f"No papers available for {context}. Run a query first."

    reference = reference.strip()

    # Try parsing as a number first (1-indexed)
    try:
        paper_num = int(reference)
        if 1 <= paper_num <= len(available_papers):
            return available_papers[paper_num - 1], ""
        else:
            return None, f"Invalid paper number '{reference}'. Choose 1-{len(available_papers)}."
    except ValueError:
        pass

    # Try matching as paper ID (exact match first)
    for paper in available_papers:
        if paper.paper_id == reference:
            return paper, ""

    # Try partial match on paper ID
    matches = []
    for paper in available_papers:
        if paper.paper_id.startswith(reference):
            matches.append(paper)

    if len(matches) == 1:
        return matches[0], ""
    elif len(matches) > 1:
        match_ids = [p.paper_id for p in matches]
        return None, f"Ambiguous paper ID '{reference}'. Matches: {', '.join(match_ids)}"

    # No matches found
    return None, f"Paper '{reference}' not found in current list. Use paper number (1-{len(available_papers)}) or exact paper ID."


def get_paper_summary_path(paper_id: str, file_locations: FileLocations) -> Optional[str]:
    """Get the path to a paper's summary file if it exists.

    Args:
        paper_id: The paper ID
        file_locations: File locations configuration

    Returns:
        Path to summary file if it exists, None otherwise
    """
    summary_filename = f"{paper_id}.md"
    summary_path = os.path.join(file_locations.summaries_dir, summary_filename)

    if os.path.exists(summary_path):
        return summary_path
    return None


def load_paper_summary(paper_id: str, file_locations: FileLocations) -> Tuple[bool, str]:
    """Load a paper's summary content.

    Args:
        paper_id: The paper ID
        file_locations: File locations configuration

    Returns:
        Tuple of (success, summary_content_or_error_message)
    """
    summary_path = get_paper_summary_path(paper_id, file_locations)

    if not summary_path:
        return False, f"No summary found for paper {paper_id}. Generate one first with 'summarize'."

    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return True, content
    except Exception as e:
        return False, f"Error reading summary for paper {paper_id}: {str(e)}"


def get_available_papers_from_query_set(
    paper_ids: List[str],
    file_locations: FileLocations
) -> List[PaperMetadata]:
    """Get paper metadata for papers in the current query set.

    This function attempts to load paper metadata for papers that are
    currently in the query result set.

    Args:
        paper_ids: List of paper IDs from last query
        file_locations: File locations configuration

    Returns:
        List of available PaperMetadata objects
    """
    return get_papers_by_ids(paper_ids, file_locations)


def format_paper_list(papers: List[PaperMetadata], title: str = "Papers") -> str:
    """Format a list of papers for display.

    Args:
        papers: List of paper metadata objects
        title: Title for the paper list

    Returns:
        Formatted string representation of the papers
    """
    if not papers:
        return f"**{title}:** No papers available"

    lines = [f"**{title}:**", ""]

    for i, paper in enumerate(papers, 1):
        # Truncate long titles
        title_display = paper.title
        if len(title_display) > 60:
            title_display = title_display[:57] + "..."

        # Show first few authors
        authors_display = ", ".join(paper.authors[:2])
        if len(paper.authors) > 2:
            authors_display += f" + {len(paper.authors) - 2} more"

        lines.append(f"{i}. **{title_display}**")
        lines.append(f"   - Authors: {authors_display}")
        lines.append(f"   - Paper ID: {paper.paper_id}")
        lines.append("")

    return "\n".join(lines)