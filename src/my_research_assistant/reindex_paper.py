"""Reindex paper command implementation.

This module provides functionality to reindex a single paper through all processing steps:
1. Index the paper's content
2. Extract the markdown text from the paper
3. Summarize the paper
4. Index the summary

All steps are idempotent - if content already exists, that step is skipped.
"""

import os
from os.path import exists, join
from typing import Optional

from .file_locations import FileLocations, FILE_LOCATIONS
from .arxiv_downloader import get_paper_metadata
from .vector_store import index_file, index_summary
from .summarizer import summarize_paper, save_summary
from .project_types import PaperMetadata


class ReindexError(Exception):
    """Raised when there's an error during the reindexing process."""
    pass


def reindex_paper(paper_id: str, file_locations: FileLocations = FILE_LOCATIONS) -> str:
    """Reindex a single paper through all processing steps.

    This function performs the following steps:
    1. Validate that the paper has been downloaded (PDF exists)
    2. Index the paper's content (if not already indexed)
    3. Extract the markdown text from the paper (if not already extracted)
    4. Summarize the paper (if summary doesn't exist)
    5. Index the summary (if not already indexed)

    All steps are idempotent - if content for any step already exists, that step is skipped.

    Parameters
    ----------
    paper_id : str
        The ArXiv paper ID to reindex
    file_locations : FileLocations
        File locations configuration

    Returns
    -------
    str
        A summary message describing what was done

    Raises
    ------
    ReindexError
        If the paper hasn't been downloaded or other errors occur
    """
    # Clean the paper ID (remove version if present for metadata lookup)
    clean_paper_id = paper_id.split('v')[0] if 'v' in paper_id else paper_id

    try:
        # Get paper metadata
        pmd = get_paper_metadata(clean_paper_id, file_locations)
        # Use the specific version ID provided by user if it includes version
        pmd.paper_id = paper_id
    except Exception as e:
        raise ReindexError(f"Failed to get metadata for paper {paper_id}: {e}")

    # Check if PDF exists
    pdf_path = pmd.get_local_pdf_path(file_locations)
    if not exists(pdf_path):
        raise ReindexError(f"Paper {paper_id} has not been downloaded. PDF not found at {pdf_path}")

    results = []

    # Step 1: Index the paper's content and extract markdown text
    try:
        # The index_file function both indexes and extracts text, and is idempotent
        paper_text = index_file(pmd, file_locations)

        # Check if text was extracted or already existed
        extracted_text_path = join(file_locations.extracted_paper_text_dir, f"{pmd.paper_id}.md")
        if exists(extracted_text_path):
            results.append("✅ Content indexed and text extracted")
        else:
            results.append("⚠️ Content indexing completed but text extraction may have failed")

    except Exception as e:
        raise ReindexError(f"Failed to index content for paper {paper_id}: {e}")

    # Step 2: Summarize the paper (if summary doesn't exist)
    summary_path = join(file_locations.summaries_dir, f"{pmd.paper_id}.md")
    if exists(summary_path):
        results.append("⏭️ Summary already exists, skipping summarization")
        # Load existing summary for step 3
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_content = f.read()
    else:
        try:
            # Generate summary
            summary_content = summarize_paper(paper_text, pmd)
            # Save summary
            save_summary(summary_content, pmd.paper_id)
            results.append("✅ Paper summarized and saved")
        except Exception as e:
            raise ReindexError(f"Failed to summarize paper {paper_id}: {e}")

    # Step 3: Index the summary (if not already indexed)
    try:
        index_summary(pmd, file_locations)
        results.append("✅ Summary indexed")
    except Exception as e:
        raise ReindexError(f"Failed to index summary for paper {paper_id}: {e}")

    # Create final summary message
    message = f"Reindexing completed for paper {paper_id}:\n" + "\n".join(f"  {result}" for result in results)
    return message