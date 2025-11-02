"""Utilities for saving and managing search and research results."""

import os
import re
from datetime import datetime
from typing import Tuple
from .file_locations import FileLocations
from .models import get_default_model


async def generate_title_from_query(query: str, content_type: str = "search") -> str:
    """Generate a descriptive title for a file based on the user query using LLM.

    Args:
        query: The original user query/research topic
        content_type: Type of content ("search", "research")

    Returns:
        A filename-safe title summarizing the query
    """
    try:
        model = get_default_model()

        prompt = f"""Given the following {content_type} query, create a short, descriptive filename-safe title that summarizes what the user is asking about.

Requirements:
- Must be 3-8 words maximum
- Use only lowercase letters, numbers, and hyphens (no spaces or special characters)
- Should clearly indicate what the query is about
- Should be specific enough to be easily recognizable

Examples:
- Query: "What are some approaches to improve RAG?" → "approaches-to-improve-rag"
- Query: "Latest developments in transformer architectures" → "latest-transformer-architectures"
- Query: "How to fine-tune large language models efficiently" → "efficient-llm-fine-tuning"
- Query: "Comparison of different attention mechanisms" → "attention-mechanisms-comparison"

Query: "{query}"

Respond with just the filename (without .md extension):"""

        response = model.complete(prompt)
        title = response.text.strip()

        # Clean and validate the title
        title = re.sub(r'[^\w\s-]', '', title.lower())
        title = re.sub(r'\s+', '-', title)
        title = re.sub(r'-+', '-', title)
        title = title.strip('-')

        # Fallback if LLM response is invalid
        if not title or len(title) < 3:
            return generate_fallback_title(query, content_type)

        return title

    except Exception:
        # Fallback to deterministic title generation on any error
        return generate_fallback_title(query, content_type)


def generate_fallback_title(query: str, content_type: str = "search") -> str:
    """Generate a fallback title when LLM generation fails."""
    # Clean the query for use as filename
    clean_query = re.sub(r'[^\w\s-]', '', query.strip())
    clean_query = re.sub(r'\s+', '-', clean_query)
    clean_query = clean_query.lower()

    # Truncate if too long
    if len(clean_query) > 40:
        clean_query = clean_query[:40]

    return clean_query


def generate_unique_filename(query: str, content_type: str = "search") -> str:
    """Generate a unique filename for saved search/research results.

    Args:
        query: The search query or research topic
        content_type: Type of content ("search", "research")

    Returns:
        A unique filename based on the query and timestamp
    """
    # Clean the query for use as filename
    # Remove special characters and replace spaces with underscores
    clean_query = re.sub(r'[^\w\s-]', '', query.strip())
    clean_query = re.sub(r'\s+', '_', clean_query)
    clean_query = clean_query.lower()

    # Truncate if too long
    if len(clean_query) > 50:
        clean_query = clean_query[:50]

    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"{content_type}_{clean_query}_{timestamp}.md"


async def save_search_results(content: str, query: str, file_locations: FileLocations, content_type: str = "search") -> Tuple[str, str]:
    """Save search or research results to a file.

    Args:
        content: The search/research results content in markdown format
        query: The original query/research topic
        file_locations: File locations configuration
        content_type: Type of content ("search", "research")

    Returns:
        Tuple of (file_path, display_title)
    """
    # Ensure results directory exists
    file_locations.ensure_results_dir()

    # Generate descriptive title using simple deterministic approach (no LLM call)
    descriptive_title = generate_fallback_title(query, content_type)

    # Add timestamp for uniqueness and create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{descriptive_title}_{timestamp}.md"
    file_path = os.path.join(file_locations.results_dir, filename)

    # Create display title
    title = f"{content_type.title()} Results: {query}"

    # Prepare content with metadata header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_content = f"""---
title: {title}
query: {query}
type: {content_type}
created: {timestamp}
---

{content}
"""

    # Write to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_content)

    return file_path, title


def open_paper_content(paper_id: str, file_locations: FileLocations) -> Tuple[bool, str, str]:
    """Open and return the content of a paper.

    This function implements the open command design:
    - If PDF_VIEWER environment variable is set, launches external viewer
    - If PDF_VIEWER is not set, returns extracted markdown for paging display

    Args:
        paper_id: The paper ID to open
        file_locations: File locations configuration

    Returns:
        Tuple of (success, content_or_error_message, action_type)
        where action_type is "viewer" (PDF viewer launched), "markdown" (display text), or "error"
    """
    import subprocess
    import shutil

    # Check if PDF exists
    pdf_filename = f"{paper_id}.pdf"
    pdf_path = os.path.join(file_locations.pdfs_dir, pdf_filename)

    if not os.path.exists(pdf_path):
        error_msg = f"open failed: Paper {paper_id} has not been downloaded. PDF not found at {pdf_path}"
        return False, error_msg, "error"

    # Check for PDF_VIEWER environment variable
    pdf_viewer = os.environ.get('PDF_VIEWER')

    if pdf_viewer:
        # Verify the PDF viewer executable exists
        if not shutil.which(pdf_viewer) and not os.path.exists(pdf_viewer):
            error_msg = f"open failed: PDF_VIEWER is set to '{pdf_viewer}', which was not found."
            return False, error_msg, "error"

        # Try to launch the PDF viewer subprocess
        try:
            # Launch subprocess in detached mode (non-blocking)
            # Using Popen with specific flags to ensure it doesn't block the parent process
            subprocess.Popen(
                [pdf_viewer, pdf_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent session
            )

            # Return success message
            success_msg = f"""# Paper Content: {paper_id}

**PDF Location:** {pdf_path}

Paper has been opened using PDF viewer {pdf_viewer}
"""
            return True, success_msg, "viewer"

        except Exception as e:
            error_msg = f"open failed: Could not launch PDF viewer '{pdf_viewer}'. Error: {str(e)}"
            return False, error_msg, "error"

    else:
        # PDF_VIEWER not set - return extracted markdown text for paging
        # Check if extracted text exists
        extracted_filename = f"{paper_id}.md"
        extracted_path = os.path.join(file_locations.extracted_paper_text_dir, extracted_filename)

        if not os.path.exists(extracted_path):
            error_msg = f"open failed: Extracted text not found for paper {paper_id} at {extracted_path}"
            return False, error_msg, "error"

        # Read the extracted markdown content
        try:
            with open(extracted_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            return True, markdown_content, "markdown"

        except Exception as e:
            error_msg = f"open failed: Could not read extracted text for paper {paper_id}. Error: {str(e)}"
            return False, error_msg, "error"


def edit_notes_for_paper(paper_id: str, file_locations: FileLocations) -> Tuple[bool, str]:
    """Handle notes editing for a paper.

    Args:
        paper_id: The paper ID to edit notes for
        file_locations: File locations configuration

    Returns:
        Tuple of (success, message)
    """
    # Ensure notes directory exists
    file_locations.ensure_notes_dir()

    # Create notes filename
    notes_filename = f"{paper_id}_notes.md"
    notes_path = os.path.join(file_locations.notes_dir, notes_filename)

    # Check if notes file exists, create if not
    if not os.path.exists(notes_path):
        # Create initial notes file
        initial_content = f"""# Notes for Paper {paper_id}

Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary Notes


## Key Insights


## Questions/Follow-up


## Personal Comments

"""
        with open(notes_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)

    # Return success message with file path
    message = f"""📝 **Notes file ready for editing**

**File location:** {notes_path}

**Instructions:**
1. Open the notes file in your preferred editor
2. Add your notes, insights, and comments
3. The file is automatically saved when you edit it

**Example editors:**
- VS Code: `code "{notes_path}"`
- Vim: `vim "{notes_path}"`
- Nano: `nano "{notes_path}"`
- Any text editor of your choice

The notes file has been created with a template structure to get you started."""

    return True, message


def extract_paper_ids_from_content(content: str) -> list[str]:
    """Extract paper IDs from search/research result content.

    Args:
        content: The markdown content containing paper references

    Returns:
        List of paper IDs found in the content
    """
    # Look for patterns like "Paper ID: 2503.22738" or similar
    paper_id_pattern = r'(?:Paper ID|ID):\s*([0-9]+\.[0-9]+(?:v[0-9]+)?)'
    matches = re.findall(paper_id_pattern, content, re.IGNORECASE)

    # Also look for arxiv URLs
    arxiv_url_pattern = r'arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+(?:v[0-9]+)?)'
    url_matches = re.findall(arxiv_url_pattern, content, re.IGNORECASE)

    # Combine and deduplicate
    all_ids = matches + url_matches
    return list(dict.fromkeys(all_ids))  # Remove duplicates while preserving order