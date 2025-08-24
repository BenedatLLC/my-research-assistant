"""Tools to summarize papers"""

import textwrap
from os.path import join
from typing import Optional, Dict, Any
import io
import numpy as np
from llama_index.llms.openai import OpenAI
import asyncio
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI

from .project_types import PaperMetadata
from .file_locations import FILE_LOCATIONS
from .models import DEFAULT_MODEL_NAME
from .prompt import subst_prompt


class SummarizationError(Exception):
    pass


def extract_markdown(text:str) -> str:
    """Look to see if the response has a ``` block of type markdown. If so,
    extract that text and return it. Otherwise, return all of the text."""
    import re
    
    # Look for markdown code blocks with ```markdown
    markdown_pattern = r'```markdown\s*\n(.*?)\n```'
    match = re.search(markdown_pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # Also check for ```md as an alternative
    md_pattern = r'```md\s*\n(.*?)\n```'
    match = re.search(md_pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # If no markdown code block found, return the original text
    return text.strip()

def insert_metadata(markdown:str,
                    pmd:PaperMetadata) -> str:
    """We want to put the paper metadata just after the summary's title.
    """
    found_title = False
    result = []
    for line in markdown.splitlines(keepends=True):
        if (not found_title) and line.strip().startswith('# '):
            result.append(line)
            result.append("\n")
            result.append(f"* Paper id: {pmd.paper_id}\n")
            result.append(f"* Authors: {', '.join(pmd.authors)}\n")
            result.append(f"* Categories: {', '.join(pmd.categories)}\n")
            result.append(f"* Published: {pmd.published}\n")
            if pmd.updated is not None:
                result.append(f"* Updated: {pmd.updated}\n")
            result.append(f"* Paper URL: {pmd.paper_abs_url}\n")
            if pmd.abstract is not None:
                result.append("\n## Abstract\n")
                result.append(textwrap.fill(pmd.abstract) + '\n\n')
            found_title = True
        else:
            result.append(line)
    if found_title:
        return ''.join(result)
    else:
        raise SummarizationError("Generated markdown did not contain a title")


def summarize_paper(text: str, pmd: PaperMetadata, feedback: Optional[str] = None, previous_summary: Optional[str] = None) -> str:
    """
    Summarize a paper, optionally taking user feedback to improve an existing summary.
    
    Args:
        text: The full text of the paper to summarize
        pmd: Paper metadata
        feedback: Optional user feedback for improving the summary
        previous_summary: Optional previous summary to improve upon
    
    Returns:
        The markdown summary
    """
    print(f"Generating summary for text of {len(text)} characters...")
    
    # Build the prompt based on whether we have feedback
    if feedback and previous_summary:
        # We're improving an existing summary
        prompt = subst_prompt('improve-summary-v2', feedback=feedback,
                              previous_summary=previous_summary,
                              text_block=text)
    else:
        # Use the original summarization prompt
        prompt = subst_prompt('base-summary-v2', text_block=text)

    try:
        llm = OpenAI(model=DEFAULT_MODEL_NAME)
        response = llm.complete(prompt)
        markdown = insert_metadata(extract_markdown(response.text), pmd)
        return markdown
    except SummarizationError:
        raise
    except Exception as e:
        raise SummarizationError(f"An error occurred during summarizing: {e}") from e


def save_summary(markdown: str, paper_id: str) -> str:
    """
    Save a markdown summary to the filesystem.
    
    Parameters
    ----------
    markdown : str
        The markdown content to save. Should be a properly formatted markdown
        document containing the paper summary.
    paper_id : str
        The unique identifier for the paper. This will be used as the filename
        (with .md extension) for the saved summary.
    
    Returns
    -------
    str
        The absolute file path where the summary was saved.
        
    Notes
    -----
    This function automatically ensures that the summaries directory exists
    before attempting to save the file. The file will be saved as 
    "{paper_id}.md" in the configured summaries directory.
    
    Examples
    --------
    >>> summary_text = "# Paper Title\\n\\nThis is a summary..."
    >>> path = save_summary(summary_text, "2023.12345")
    >>> print(path)
    '/path/to/summaries/2023.12345.md'
    """
    FILE_LOCATIONS.ensure_summaries_dir()
    file_path = join(FILE_LOCATIONS.summaries_dir, paper_id + '.md')
    with open(file_path, 'w') as f:
        f.write(markdown)
    return file_path

