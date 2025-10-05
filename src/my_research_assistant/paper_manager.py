"""Utilities for managing paper collections and resolving paper references."""

import os
import re
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


def is_arxiv_id_format(text: str) -> bool:
    """Check if text looks like an ArXiv paper ID.

    Args:
        text: The text to check

    Returns:
        True if text matches ArXiv ID pattern, False otherwise
    """
    # ArXiv IDs are typically YYMM.NNNNN or YYMM.NNNNNvN
    # Also support newer format: YYMM.NNNNN[vN]
    pattern = r'^\d{4}\.\d{4,5}(v\d+)?$'
    return bool(re.match(pattern, text.strip()))


def get_all_downloaded_papers(file_locations: FileLocations) -> List[PaperMetadata]:
    """Get all papers that have been downloaded (have PDFs).

    Args:
        file_locations: File locations configuration

    Returns:
        List of PaperMetadata objects for all downloaded papers
    """
    from .arxiv_downloader import get_paper_metadata

    papers = []
    if not os.path.exists(file_locations.pdfs_dir):
        return papers

    # Get all PDF files
    for filename in os.listdir(file_locations.pdfs_dir):
        if filename.endswith('.pdf'):
            # Extract paper ID from filename (remove .pdf extension)
            paper_id = filename[:-4]
            try:
                paper = get_paper_metadata(paper_id.split('v')[0], file_locations)
                if paper:
                    # Use the specific version from filename
                    paper.paper_id = paper_id
                    papers.append(paper)
            except Exception:
                # Skip papers that can't be loaded
                continue

    return papers


def find_downloaded_papers_by_base_id(base_id: str, file_locations: FileLocations) -> List[str]:
    """Find all downloaded versions of a paper by its base ID.

    Args:
        base_id: Base ArXiv ID without version (e.g., "2107.03374")
        file_locations: File locations configuration

    Returns:
        List of full paper IDs (with versions) that have been downloaded
    """
    if not os.path.exists(file_locations.pdfs_dir):
        return []

    matches = []
    for filename in os.listdir(file_locations.pdfs_dir):
        if filename.endswith('.pdf'):
            paper_id = filename[:-4]
            # Check if this paper ID starts with the base ID
            if paper_id.startswith(base_id):
                # Ensure it's an exact match or includes version
                if paper_id == base_id or (len(paper_id) > len(base_id) and paper_id[len(base_id)] == 'v'):
                    matches.append(paper_id)

    return sorted(matches)


def parse_paper_argument(
    command_name: str,
    argument: str,
    last_query_set: List[str],
    file_locations: FileLocations
) -> Tuple[Optional[PaperMetadata], str]:
    """Parse and validate a paper argument for commands.

    This function implements the design specified in designs/command-arguments.md.
    It handles both integer references (to last_query_set) and ArXiv ID references
    (to entire repository) with comprehensive error handling.

    Args:
        command_name: Name of the command for error messages
        argument: The paper argument string to parse
        last_query_set: List of paper IDs from last query
        file_locations: File locations configuration

    Returns:
        Tuple of (PaperMetadata if found, error_message if not found)
    """
    from .arxiv_downloader import get_paper_metadata

    if not argument or not argument.strip():
        return None, f"❌ {command_name} failed: Please provide a paper number or ID"

    argument = argument.strip()

    # Check for multiple arguments (split by whitespace)
    if len(argument.split()) > 1:
        return None, f"❌ {command_name} failed: Please provide exactly one paper number or ID"

    # Try parsing as integer first (1-indexed reference to last_query_set)
    try:
        paper_num = int(argument)
        if not last_query_set:
            return None, f"❌ {command_name} failed: No papers in current list. Use 'find' or 'list' to populate papers first"

        if 1 <= paper_num <= len(last_query_set):
            paper_id = last_query_set[paper_num - 1]
            try:
                paper = get_paper_metadata(paper_id.split('v')[0], file_locations)
                if paper:
                    paper.paper_id = paper_id
                    # Verify PDF exists
                    pdf_path = paper.get_local_pdf_path(file_locations)
                    if not os.path.exists(pdf_path):
                        return None, f"❌ {command_name} failed: Paper {paper_id} PDF not found at {pdf_path}"
                    return paper, ""
                else:
                    return None, f"❌ {command_name} failed: Could not load metadata for paper {paper_id}"
            except Exception as e:
                return None, f"❌ {command_name} failed: Error loading paper {paper_id}: {str(e)}"
        else:
            return None, f"❌ {command_name} failed: Invalid paper number '{argument}'. Choose 1-{len(last_query_set)}"

    except ValueError:
        pass

    # Not an integer, check if it looks like an ArXiv ID
    if not is_arxiv_id_format(argument):
        return None, f"❌ {command_name} failed: '{argument}' is not a valid paper number or ArXiv ID"

    # Handle ArXiv ID (search entire repository)
    if 'v' in argument:
        # Specific version provided
        paper_id = argument
        base_id = argument.split('v')[0]
    else:
        # No version provided, need to find downloaded versions
        base_id = argument
        downloaded_versions = find_downloaded_papers_by_base_id(base_id, file_locations)

        if not downloaded_versions:
            return None, f"❌ {command_name} failed: Paper {base_id} has not been downloaded"

        if len(downloaded_versions) == 1:
            paper_id = downloaded_versions[0]
        else:
            versions_str = ', '.join(downloaded_versions)
            return None, f"❌ {command_name} failed: Multiple versions found for {base_id} ({versions_str}). Please specify version"

    # Load the paper metadata
    try:
        paper = get_paper_metadata(base_id, file_locations)
        if paper:
            paper.paper_id = paper_id
            # Verify PDF exists
            pdf_path = paper.get_local_pdf_path(file_locations)
            if not os.path.exists(pdf_path):
                return None, f"❌ {command_name} failed: Paper {paper_id} has not been downloaded. PDF not found at {pdf_path}"
            return paper, ""
        else:
            return None, f"❌ {command_name} failed: Could not load metadata for paper {paper_id}"
    except Exception as e:
        return None, f"❌ {command_name} failed: Error loading paper {paper_id}: {str(e)}"


def parse_paper_argument_enhanced(
    command_name: str,
    argument: str,
    last_query_set: List[str],
    file_locations: FileLocations
) -> Tuple[Optional[PaperMetadata], str, bool]:
    """Enhanced version of parse_paper_argument that also returns resolution method.

    This function implements the design specified in designs/command-arguments.md.
    It handles both integer references (to last_query_set) and ArXiv ID references
    (to entire repository) with comprehensive error handling.

    Args:
        command_name: Name of the command for error messages
        argument: The paper argument string to parse
        last_query_set: List of paper IDs from last query
        file_locations: File locations configuration

    Returns:
        Tuple of (PaperMetadata if found, error_message if not found, was_resolved_by_integer)
        The third element is True if resolved by integer reference, False if by ArXiv ID
    """
    from .arxiv_downloader import get_paper_metadata

    if not argument or not argument.strip():
        return None, f"❌ {command_name} failed: Please provide a paper number or ID", False

    argument = argument.strip()

    # Check for multiple arguments (split by whitespace)
    if len(argument.split()) > 1:
        return None, f"❌ {command_name} failed: Please provide exactly one paper number or ID", False

    # Commands that will download the paper (don't require PDF to exist)
    download_commands = {"summarize"}
    require_pdf = command_name not in download_commands

    # Try parsing as integer first (1-indexed reference to last_query_set)
    try:
        paper_num = int(argument)
        if not last_query_set:
            return None, f"❌ {command_name} failed: No papers in current list. Use 'find' or 'list' to populate papers first", False

        if 1 <= paper_num <= len(last_query_set):
            paper_id = last_query_set[paper_num - 1]
            try:
                paper = get_paper_metadata(paper_id.split('v')[0], file_locations)
                if paper:
                    paper.paper_id = paper_id
                    # Verify PDF exists (only for commands that require it)
                    if require_pdf:
                        pdf_path = paper.get_local_pdf_path(file_locations)
                        if not os.path.exists(pdf_path):
                            return None, f"❌ {command_name} failed: Paper {paper_id} PDF not found at {pdf_path}", False
                    return paper, "", True  # True = resolved by integer
                else:
                    return None, f"❌ {command_name} failed: Could not load metadata for paper {paper_id}", False
            except Exception as e:
                return None, f"❌ {command_name} failed: Error loading paper {paper_id}: {str(e)}", False
        else:
            return None, f"❌ {command_name} failed: Invalid paper number '{argument}'. Choose 1-{len(last_query_set)}", False

    except ValueError:
        pass

    # Not an integer, check if it looks like an ArXiv ID
    if not is_arxiv_id_format(argument):
        return None, f"❌ {command_name} failed: '{argument}' is not a valid paper number or ArXiv ID", False

    # Handle ArXiv ID (search entire repository)
    if 'v' in argument:
        # Specific version provided
        paper_id = argument
        base_id = argument.split('v')[0]
    else:
        # No version provided, need to find downloaded versions
        base_id = argument
        downloaded_versions = find_downloaded_papers_by_base_id(base_id, file_locations)

        if not downloaded_versions:
            return None, f"❌ {command_name} failed: Paper {base_id} has not been downloaded", False

        if len(downloaded_versions) == 1:
            paper_id = downloaded_versions[0]
        else:
            versions_str = ', '.join(downloaded_versions)
            return None, f"❌ {command_name} failed: Multiple versions found for {base_id} ({versions_str}). Please specify version", False

    # Load the paper metadata
    try:
        paper = get_paper_metadata(base_id, file_locations)
        if paper:
            paper.paper_id = paper_id
            # Verify PDF exists (only for commands that require it)
            if require_pdf:
                pdf_path = paper.get_local_pdf_path(file_locations)
                if not os.path.exists(pdf_path):
                    return None, f"❌ {command_name} failed: Paper {paper_id} has not been downloaded. PDF not found at {pdf_path}", False
            return paper, "", False  # False = resolved by ArXiv ID
        else:
            return None, f"❌ {command_name} failed: Could not load metadata for paper {paper_id}", False
    except Exception as e:
        return None, f"❌ {command_name} failed: Error loading paper {paper_id}: {str(e)}", False