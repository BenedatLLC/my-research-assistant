"""
Command-line tool for testing search APIs in vector_store.py.

This script provides a testing interface for the three search functions:
- search_index: Search the content index
- search_content_index_filtered: Search content index filtered by paper IDs
- search_summary_index: Search the summary index

The script accepts various command-line arguments to control search parameters
and displays paginated results with rich formatting.
"""
import argparse
import sys
from typing import List
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from . import constants
from .file_locations import FILE_LOCATIONS
from .pagination import TextPaginator
from .project_types import SearchResult
from .vector_store import (
    IndexError as CustomIndexError,
    RetrievalError,
    search_index,
    search_content_index_filtered,
    search_summary_index,
)


def parse_arguments(args: List[str] = None) -> argparse.Namespace:
    """
    Parse command-line arguments for search tester.

    Args:
        args: List of command-line arguments (for testing). If None, uses sys.argv.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Test search APIs in vector_store.py with rich output formatting"
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Search the summary index (via search_summary_index)'
    )

    parser.add_argument(
        '--papers',
        type=str,
        help='Comma-separated paper IDs to filter by (uses search_content_index_filtered). Not valid with --summary'
    )

    parser.add_argument(
        '-k', '--num-chunks',
        type=int,
        default=constants.CONTENT_SEARCH_K,
        help=f'Number of chunks to return (default: {constants.CONTENT_SEARCH_K})'
    )

    parser.add_argument(
        '--content-similarity-threshold',
        type=float,
        default=constants.CONTENT_SEARCH_SIMILARITY_CUTOFF,
        help=f'Minimum similarity score threshold (0.0-1.0, default: {constants.CONTENT_SEARCH_SIMILARITY_CUTOFF})'
    )

    parser.add_argument(
        '--use-mmr',
        action='store_true',
        help='Use Maximum Marginal Relevance (MMR) for reranking'
    )

    parser.add_argument(
        '--mmr-alpha',
        type=float,
        default=constants.CONTENT_SEARCH_MMR_ALPHA,
        help=f'MMR alpha parameter (0.0-1.0, default: {constants.CONTENT_SEARCH_MMR_ALPHA}). Only valid with --use-mmr'
    )

    parser.add_argument(
        '--papers-only',
        action='store_true',
        help='Display results as a simple table with paper ID, chunk length, and title (no content)'
    )

    parser.add_argument(
        'query',
        type=str,
        help='Search query text'
    )

    return parser.parse_args(args)


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate parsed command-line arguments.

    Args:
        args: Parsed arguments namespace

    Raises:
        SystemExit: If validation fails (exits with status 1)
    """
    # Check for mutually exclusive flags
    if args.summary and args.papers:
        print("❌ Error: --summary and --papers cannot both be specified", file=sys.stderr)
        sys.exit(1)

    # Check mmr-alpha requires --use-mmr (only if non-default value)
    if not args.use_mmr and args.mmr_alpha != constants.CONTENT_SEARCH_MMR_ALPHA:
        print("❌ Error: --mmr-alpha requires --use-mmr flag", file=sys.stderr)
        sys.exit(1)

    # Validate similarity threshold range
    if not (0.0 <= args.content_similarity_threshold <= 1.0):
        print("❌ Error: --content-similarity-threshold must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    # Validate mmr-alpha range
    if not (0.0 <= args.mmr_alpha <= 1.0):
        print("❌ Error: --mmr-alpha must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)


def format_summary_header(
    query: str,
    function_name: str,
    k: int,
    similarity_threshold: float,
    use_mmr: bool,
    mmr_alpha: float | None,
    num_results: int,
    num_unique_papers: int
) -> str:
    """
    Format the summary header section of the output.

    Args:
        query: Original search query
        function_name: Name of search function used
        k: Number of chunks requested
        similarity_threshold: Similarity threshold value
        use_mmr: Whether MMR was used
        mmr_alpha: MMR alpha value (None if not applicable)
        num_results: Number of results returned
        num_unique_papers: Number of unique papers in results

    Returns:
        Formatted header string
    """
    header_lines = [
        "# Search Results Summary",
        "",
        f"**Query:** {query}",
        f"**Function:** `{function_name}`",
        f"**Parameters:**",
        f"  - k={k}",
        f"  - similarity_threshold={similarity_threshold}",
        f"  - use_mmr={use_mmr}",
    ]

    if mmr_alpha is not None:
        header_lines.append(f"  - mmr_alpha={mmr_alpha}")

    header_lines.extend([
        "",
        f"**Results:** {num_results} results returned",
        f"**Unique papers:** {num_unique_papers}",
        "",
        "---",
        ""
    ])

    return '\n'.join(header_lines)


def format_papers_only_table(results: List[SearchResult]) -> Table:
    """
    Format search results as a simple table showing paper metadata only.

    Args:
        results: List of SearchResult objects to format

    Returns:
        Rich Table with result number, paper ID, chunk number (page), chunk length, and title
    """
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Paper ID", style="cyan")
    table.add_column("Chunk #", justify="right", style="yellow")
    table.add_column("Chunk Length", justify="right", style="magenta")
    table.add_column("Title", style="green")

    for i, result in enumerate(results, start=1):
        table.add_row(
            str(i),
            result.paper_id,
            str(result.page),
            str(len(result.chunk)),
            result.paper_title
        )

    return table


def format_search_result(result: SearchResult, result_number: int, search_type: str) -> str:
    """
    Format a single search result for display.

    Args:
        result: SearchResult object to format
        result_number: Sequential number for this result (1-indexed)
        search_type: Type of search ('content', 'filtered', or 'summary')

    Returns:
        Formatted result string
    """
    # Determine which filename to show based on search type
    filename = result.summary_filename if search_type == 'summary' else result.pdf_filename

    result_lines = [
        f"## Result {result_number}",
        "",
        f"**Paper ID:** {result.paper_id}",
        f"**Title:** {result.paper_title}",
        f"**File:** {filename}",
        f"**Page:** {result.page}",
        f"**Size:** {len(result.chunk)} characters",
        "",
        "**Content:**",
        "",
        result.chunk,
        "",
        "---",
        ""
    ]

    return '\n'.join(result_lines)


def main() -> None:
    """
    Main entry point for search tester script.

    Parses arguments, validates them, performs the appropriate search,
    and displays paginated results.
    """
    # Parse and validate arguments
    args = parse_arguments()
    validate_arguments(args)

    # Determine which search function to use and adjust parameters
    if args.summary:
        function_name = "search_summary_index"
        search_type = "summary"
        # Use summary-specific default for k if not explicitly provided
        k = args.num_chunks if args.num_chunks != constants.CONTENT_SEARCH_K else constants.SUMMARY_SEARCH_K
    elif args.papers:
        function_name = "search_content_index_filtered"
        search_type = "filtered"
        k = args.num_chunks
    else:
        function_name = "search_index"
        search_type = "content"
        k = args.num_chunks

    # Call the appropriate search function
    try:
        if args.summary:
            results = search_summary_index(
                query=args.query,
                k=k,
                file_locations=FILE_LOCATIONS,
                use_mmr=args.use_mmr,
                similarity_cutoff=args.content_similarity_threshold
            )
            mmr_alpha = None  # Not applicable for summary search
        elif args.papers:
            paper_ids = [pid.strip() for pid in args.papers.split(',')]
            results = search_content_index_filtered(
                query=args.query,
                paper_ids=paper_ids,
                k=k,
                file_locations=FILE_LOCATIONS,
                similarity_cutoff=args.content_similarity_threshold
            )
            mmr_alpha = None  # Not used in filtered search
        else:
            results = search_index(
                query=args.query,
                k=k,
                file_locations=FILE_LOCATIONS,
                use_mmr=args.use_mmr,
                similarity_cutoff=args.content_similarity_threshold,
                mmr_alpha=args.mmr_alpha
            )
            mmr_alpha = args.mmr_alpha if args.use_mmr else None

    except (CustomIndexError, RetrievalError) as e:
        print(f"❌ Search error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

    console = Console()

    # Check if papers-only mode is enabled
    if args.papers_only:
        # Display results as a simple table
        table = format_papers_only_table(results)
        console.print(f"\n🔍 Search Results: {args.query}")
        console.print(f"Found {len(results)} results\n")
        console.print(table)
    else:
        # Format results for paginated display
        output_lines = []

        # Calculate unique papers
        unique_papers = len(set(result.paper_id for result in results))

        # Add summary header
        header = format_summary_header(
            query=args.query,
            function_name=function_name,
            k=k,
            similarity_threshold=args.content_similarity_threshold,
            use_mmr=args.use_mmr,
            mmr_alpha=mmr_alpha,
            num_results=len(results),
            num_unique_papers=unique_papers
        )
        output_lines.extend(header.split('\n'))

        # Add formatted results
        for i, result in enumerate(results, start=1):
            formatted_result = format_search_result(result, i, search_type)
            output_lines.extend(formatted_result.split('\n'))

        # Display with pagination
        paginator = TextPaginator(console)
        title = f"🔍 Search Results: {args.query}"
        paginator.paginate_lines(output_lines, title=title)


if __name__ == '__main__':
    main()
