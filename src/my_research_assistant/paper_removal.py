"""Paper removal functionality for the research assistant.

This module provides functions to remove papers from the local store,
including deleting files and removing entries from vector indexes.
"""

import os
import logging
from os.path import exists, join
from typing import Tuple, Optional
import chromadb

from .file_locations import FileLocations, FILE_LOCATIONS
from .project_types import PaperMetadata
from .arxiv_downloader import get_downloaded_paper_ids, get_paper_metadata

logger = logging.getLogger(__name__)


def remove_paper_from_indexes(paper_id: str, file_locations: FileLocations = FILE_LOCATIONS) -> Tuple[int, int]:
    """Remove all chunks for a paper from both content and summary indexes.

    This function uses ChromaDB's delete() method with metadata filters to remove
    all chunks associated with the specified paper ID from both the content and
    summary vector stores.

    Parameters
    ----------
    paper_id : str
        The ArXiv paper ID to remove from indexes (e.g., "2107.03374v2")
    file_locations : FileLocations, optional
        File locations configuration

    Returns
    -------
    Tuple[int, int]
        A tuple of (content_chunks_removed, summary_chunks_removed)

    Raises
    ------
    Exception
        If there's an error accessing or deleting from the indexes
    """
    content_chunks_removed = 0
    summary_chunks_removed = 0

    # Remove from content index
    content_db_path = join(file_locations.index_dir, "content_chroma_db")
    if exists(content_db_path):
        try:
            chroma_client = chromadb.PersistentClient(path=content_db_path)
            collection = chroma_client.get_collection("content_index")

            # Get count before deletion for reporting
            results = collection.get(where={"paper_id": paper_id})
            content_chunks_removed = len(results['ids']) if results and 'ids' in results else 0

            # Delete all chunks with this paper_id
            if content_chunks_removed > 0:
                collection.delete(where={"paper_id": paper_id})
        except Exception as e:
            # If collection doesn't exist or other error, just continue
            print(f"Note: Could not access content index: {e}")

    # Remove from summary index
    summary_db_path = join(file_locations.index_dir, "summary_chroma_db")
    if exists(summary_db_path):
        try:
            chroma_client = chromadb.PersistentClient(path=summary_db_path)
            collection = chroma_client.get_collection("summary_index")

            # Get count before deletion for reporting
            results = collection.get(where={"paper_id": paper_id})
            summary_chunks_removed = len(results['ids']) if results and 'ids' in results else 0

            # Delete all chunks with this paper_id
            if summary_chunks_removed > 0:
                collection.delete(where={"paper_id": paper_id})
        except Exception as e:
            # If collection doesn't exist or other error, just continue
            print(f"Note: Could not access summary index: {e}")

    return content_chunks_removed, summary_chunks_removed


def find_matching_papers(paper_ref: str, file_locations: FileLocations = FILE_LOCATIONS) -> list[str]:
    """Find all downloaded papers matching a paper reference.

    This handles the case where a user provides a paper ID without a version number.
    For example, "2107.03374" might match "2107.03374v1" and "2107.03374v2".

    Parameters
    ----------
    paper_ref : str
        The paper reference, which may or may not include a version number
    file_locations : FileLocations, optional
        File locations configuration

    Returns
    -------
    list[str]
        List of matching paper IDs
    """
    all_papers = get_downloaded_paper_ids(file_locations)

    # Check for exact match first
    if paper_ref in all_papers:
        return [paper_ref]

    # Check for prefix match (handles version-less IDs)
    matches = [p for p in all_papers if p.startswith(paper_ref)]
    return matches


def remove_paper(paper_id: str, file_locations: FileLocations = FILE_LOCATIONS,
                 confirm_callback: Optional[callable] = None,
                 notes_confirm_callback: Optional[callable] = None) -> Tuple[bool, str]:
    """Remove a paper from the local store.

    This function orchestrates the complete removal of a paper, including:
    - Confirmation prompts
    - Deleting PDF file
    - Deleting paper metadata
    - Deleting extracted text
    - Deleting summary
    - Removing from vector indexes
    - Deleting notes (with additional confirmation)

    The function reports each deletion and continues even if some files don't exist.

    Parameters
    ----------
    paper_id : str
        The ArXiv paper ID to remove (e.g., "2107.03374v2")
    file_locations : FileLocations, optional
        File locations configuration
    confirm_callback : callable, optional
        Function that returns True/False for confirmation. If None, uses input().
        Signature: confirm_callback(paper_metadata: PaperMetadata) -> bool
    notes_confirm_callback : callable, optional
        Function that returns True/False for notes deletion confirmation.
        If None, uses input(). Signature: notes_confirm_callback(notes_path: str) -> bool

    Returns
    -------
    Tuple[bool, str]
        (success, message) - success is True if removal completed, message describes the result

    Raises
    ------
    ValueError
        If the paper ID is ambiguous (multiple versions found)
    FileNotFoundError
        If the paper metadata cannot be found
    """
    # Check for ambiguous paper reference
    matching_papers = find_matching_papers(paper_id, file_locations)

    if len(matching_papers) == 0:
        return False, f"Paper {paper_id} not found in the store."
    elif len(matching_papers) > 1:
        versions_str = " and ".join(matching_papers)
        return False, f"Ambiguous removal request: there are multiple versions of that paper in the store: {versions_str}\nSkipping removal."

    # Use the exact paper ID
    paper_id = matching_papers[0]

    # Get paper metadata for confirmation
    try:
        paper_metadata = get_paper_metadata(paper_id, file_locations)
    except Exception as e:
        return False, f"Could not load metadata for paper {paper_id}: {e}"

    # Build removal messages
    messages = []

    # Initial confirmation
    if confirm_callback:
        confirmed = confirm_callback(paper_metadata)
    else:
        # Default: use input()
        print(f"🗑️ Removing paper {paper_id}")
        print(f"   title:     {paper_metadata.title}")
        print(f"   published: {paper_metadata.published.strftime('%Y-%m-%d')}")
        print("⚠️ This will delete all indexes from PDFs, extracted content, summaries, and notes.")
        response = input("Are you sure you want to continue? [y/n]: ").strip().lower()
        confirmed = response == 'y'

    if not confirmed:
        return False, "Removal cancelled by user."

    # Remove PDF
    pdf_path = join(file_locations.pdfs_dir, f"{paper_id}.pdf")
    if exists(pdf_path):
        os.remove(pdf_path)
        messages.append(f"❌ Removed downloaded paper '{pdf_path}'")
    else:
        messages.append(f"No downloaded paper found at '{pdf_path}'.")

    # Remove from indexes
    content_chunks, summary_chunks = remove_paper_from_indexes(paper_id, file_locations)
    if content_chunks > 0:
        messages.append(f"❌ Removed {content_chunks} chunks from the content index.")
    else:
        messages.append("No content index chunks found for this paper.")

    # Remove extracted text
    extracted_text_path = join(file_locations.extracted_paper_text_dir, f"{paper_id}.md")
    if exists(extracted_text_path):
        os.remove(extracted_text_path)
        messages.append(f"❌ Removed extracted paper text '{extracted_text_path}'")
    else:
        messages.append(f"No extracted paper text found at '{extracted_text_path}'.")

    # Remove summary
    summary_path = join(file_locations.summaries_dir, f"{paper_id}.md")
    if exists(summary_path):
        os.remove(summary_path)
        messages.append(f"❌ Removed summary '{summary_path}'")
    else:
        messages.append(f"No summary found at '{summary_path}'.")

    if summary_chunks > 0:
        messages.append(f"❌ Removed {summary_chunks} chunks from the summary index.")
    else:
        messages.append("No summary index chunks found for this paper.")

    # Remove paper metadata
    metadata_path = join(file_locations.paper_metadata_dir, f"{paper_id}.json")
    if exists(metadata_path):
        os.remove(metadata_path)
        messages.append(f"❌ Removed paper metadata '{metadata_path}'")
    else:
        messages.append(f"No paper metadata found at '{metadata_path}'.")

    # Remove notes (with additional confirmation)
    notes_path = join(file_locations.notes_dir, f"{paper_id}.md")
    if exists(notes_path):
        if notes_confirm_callback:
            notes_confirmed = notes_confirm_callback(notes_path)
        else:
            # Default: use input() with separate confirmation
            response = input(f"Are you sure you want to delete the notes file '{notes_path}' [y/n]: ").strip().lower()
            notes_confirmed = response == 'y'

        if notes_confirmed:
            os.remove(notes_path)
            messages.append(f"❌ Removed paper notes found at '{notes_path}'.")
        else:
            messages.append(f"Kept notes file at '{notes_path}' (user chose not to delete).")
    else:
        messages.append(f"No paper notes found at '{notes_path}'.")

    # Build final message
    result_message = "\n".join(messages)
    result_message += f"\nRemoval of content for paper {paper_id} completed successfully."

    return True, result_message
