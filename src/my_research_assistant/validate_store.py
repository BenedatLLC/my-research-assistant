"""Validation utilities for the research assistant data store.

This module provides functions to validate and report on the status of
downloaded papers across different storage locations and indexes.
"""

import os
from os.path import join, exists
from typing import List, Dict, Any, NamedTuple
from rich.table import Table
from rich.console import Console

from .file_locations import FILE_LOCATIONS, FileLocations
from .arxiv_downloader import get_downloaded_paper_ids
from .vector_store import _get_or_initialize_index


class PaperStoreStatus(NamedTuple):
    """Status information for a single paper in the store."""
    paper_id: str
    has_metadata: bool
    content_index_chunks: int
    has_summary: bool
    has_extracted_paper_text: bool
    summary_index_chunks: int
    has_notes: bool


def _count_chunks_for_paper(paper_id: str, index_type: str, file_locations: FileLocations) -> int:
    """Count the number of chunks for a paper in the specified index.

    Parameters
    ----------
    paper_id : str
        The ArXiv paper ID
    index_type : str
        Either "content" or "summary"
    file_locations : FileLocations
        File locations configuration

    Returns
    -------
    int
        Number of chunks for this paper in the index, 0 if none found
    """
    try:
        import chromadb
        from .vector_store import _get_chroma_db_path

        # Get the ChromaDB path for the specified index type
        db_path = _get_chroma_db_path(file_locations, index_type)

        if not os.path.exists(db_path):
            return 0

        # Initialize ChromaDB client and get collection
        chroma_client = chromadb.PersistentClient(path=db_path)
        collection_name = f"{index_type}_index"

        try:
            collection = chroma_client.get_collection(collection_name)
        except Exception:
            return 0

        # Get all documents and count those with matching paper_id
        docs = collection.get()
        count = 0

        if docs['metadatas']:
            for metadata in docs['metadatas']:
                if metadata and metadata.get('paper_id') == paper_id:
                    count += 1

        return count
    except Exception:
        # If there's any error (index doesn't exist, etc.), return 0
        return 0


def get_paper_store_status(paper_id: str, file_locations: FileLocations = FILE_LOCATIONS) -> PaperStoreStatus:
    """Get the complete store status for a single paper.

    Parameters
    ----------
    paper_id : str
        The ArXiv paper ID to check
    file_locations : FileLocations
        File locations configuration

    Returns
    -------
    PaperStoreStatus
        Complete status information for the paper
    """
    # Check file existence
    metadata_path = join(file_locations.paper_metadata_dir, f"{paper_id}.json")
    summary_path = join(file_locations.summaries_dir, f"{paper_id}.md")
    extracted_text_path = join(file_locations.extracted_paper_text_dir, f"{paper_id}.md")
    notes_path = join(file_locations.notes_dir, f"{paper_id}.md")

    has_metadata = exists(metadata_path)
    has_summary = exists(summary_path)
    has_extracted_paper_text = exists(extracted_text_path)
    has_notes = exists(notes_path)

    # Count chunks in indexes
    content_index_chunks = _count_chunks_for_paper(paper_id, "content", file_locations)
    summary_index_chunks = _count_chunks_for_paper(paper_id, "summary", file_locations)

    return PaperStoreStatus(
        paper_id=paper_id,
        has_metadata=has_metadata,
        content_index_chunks=content_index_chunks,
        has_summary=has_summary,
        has_extracted_paper_text=has_extracted_paper_text,
        summary_index_chunks=summary_index_chunks,
        has_notes=has_notes
    )


def validate_store(file_locations: FileLocations = FILE_LOCATIONS) -> List[PaperStoreStatus]:
    """Validate the store for all downloaded papers.

    Parameters
    ----------
    file_locations : FileLocations
        File locations configuration

    Returns
    -------
    List[PaperStoreStatus]
        Status information for all downloaded papers
    """
    # Get all downloaded paper IDs
    paper_ids = get_downloaded_paper_ids(file_locations)

    # Get status for each paper
    statuses = []
    for paper_id in sorted(paper_ids):  # Sort for consistent output
        status = get_paper_store_status(paper_id, file_locations)
        statuses.append(status)

    return statuses


def format_store_validation_table(statuses: List[PaperStoreStatus]) -> Table:
    """Format store validation results as a Rich table.

    Parameters
    ----------
    statuses : List[PaperStoreStatus]
        List of paper store statuses

    Returns
    -------
    Table
        Rich table ready for display
    """
    table = Table(title="Store Validation Results")

    # Add columns as specified in the design
    table.add_column("Paper ID", style="cyan", no_wrap=True)
    table.add_column("Has\nMetadata", style="white", justify="center")
    table.add_column("Content\nindex chunks", style="white", justify="center")
    table.add_column("Has\nsummary", style="white", justify="center")
    table.add_column("Has extracted\npaper text", style="white", justify="center")
    table.add_column("Summary\nindex chunks", style="white", justify="center")
    table.add_column("Has\nnotes", style="white", justify="center")

    for status in statuses:
        # Format values according to design spec
        has_metadata = "✅" if status.has_metadata else "❌"
        content_chunks = str(status.content_index_chunks) if status.content_index_chunks > 0 else "❌"
        summary_chunks = str(status.summary_index_chunks) if status.summary_index_chunks > 0 else "❌"
        has_summary = "✅" if status.has_summary else "❌"
        has_extracted_text = "✅" if status.has_extracted_paper_text else "❌"
        has_notes = "✅" if status.has_notes else "❌"

        table.add_row(
            status.paper_id,
            has_metadata,
            content_chunks,
            has_summary,
            has_extracted_text,
            summary_chunks,
            has_notes
        )

    return table


def print_store_validation(console: Console, file_locations: FileLocations = FILE_LOCATIONS) -> None:
    """Print store validation results to console.

    Parameters
    ----------
    console : Console
        Rich console for output
    file_locations : FileLocations
        File locations configuration
    """
    statuses = validate_store(file_locations)

    if not statuses:
        console.print("📄 [yellow]No downloaded papers found in the store.[/yellow]")
        return

    table = format_store_validation_table(statuses)
    console.print(table)

    # Print summary statistics
    total_papers = len(statuses)
    papers_with_content = sum(1 for s in statuses if s.content_index_chunks > 0)
    papers_with_summaries = sum(1 for s in statuses if s.has_summary)
    papers_with_extracted_text = sum(1 for s in statuses if s.has_extracted_paper_text)
    papers_with_summary_index = sum(1 for s in statuses if s.summary_index_chunks > 0)
    papers_with_notes = sum(1 for s in statuses if s.has_notes)

    console.print(f"\n📊 [bold]Summary:[/bold]")
    console.print(f"• Total papers: {total_papers}")
    console.print(f"• With content index: {papers_with_content} ({papers_with_content/total_papers*100:.1f}%)")
    console.print(f"• With summaries: {papers_with_summaries} ({papers_with_summaries/total_papers*100:.1f}%)")
    console.print(f"• With extracted text: {papers_with_extracted_text} ({papers_with_extracted_text/total_papers*100:.1f}%)")
    console.print(f"• With summary index: {papers_with_summary_index} ({papers_with_summary_index/total_papers*100:.1f}%)")
    console.print(f"• With notes: {papers_with_notes} ({papers_with_notes/total_papers*100:.1f}%)")