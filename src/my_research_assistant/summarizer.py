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

from .types import PaperMetadata
from .file_locations import FILE_LOCATIONS
from .models import DEFAULT_MODEL_NAME

# Define the prompt for summarization
# This prompt guides the LLM to produce the desired structured output in Markdown.
summarization_prompt = """
Please summarize the following text block into a markdown document.
The summary should include the following sections:

1.  **Key ideas of the paper**: Briefly describe the main contributions and core concepts.
2.  **Implementation approach**: Explain how the proposed method is built and works.
3.  **Experiments**: Detail the experimental setup, datasets used, and key results.
4.  **Related work**: Discuss how this work relates to and differs from previous research.

The title of the markdown summary should be the title of the paper using a markdown level 1 header
("#").

---
Text to summarize:
{{text_block}}
---

Markdown Summary:
"""

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
        improved_prompt = f"""
Please improve the following paper summary based on the user's feedback.

**User Feedback:** {feedback}

**Previous Summary:**
{previous_summary}

**Original Paper Text:**
{{text_block}}

Please provide an improved markdown summary that addresses the user's feedback while maintaining the following structure:

1.  **Key ideas of the paper**: Briefly describe the main contributions and core concepts.
2.  **Implementation approach**: Explain how the proposed method is built and works.
3.  **Experiments**: Detail the experimental setup, datasets used, and key results.
4.  **Related work**: Discuss how this work relates to and differs from previous research.

The title of the markdown summary should be the title of the paper using a markdown level 1 header ("#").

Improved Markdown Summary:
"""
        prompt = improved_prompt
    else:
        # Use the original summarization prompt
        prompt = summarization_prompt

    try:
        llm = OpenAI(model=DEFAULT_MODEL_NAME)
        # Make the LLM call to get the summary
        response = llm.complete(prompt.replace('{{text_block}}', text))
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

SUMMARIZER_AGENT_PROMPT=\
"""You are an expert Computer Science researcher who can find, index, and
summarize papers from arxiv.org. You are designed to have multiple interactions
with the user to refine and improve your work until they are satisfied.

Using the provided tools, do the following:

1. Find the paper most closely matching the criteria provided by the user,
   using the `search_arxiv_papers` tool.
2. Ask the user if the paper matches the one they want. If not, ask them to
   provide more details and show them the 5 most closely matching papers. Then
   ask them to pick among these papers.
3. When a paper has been selected, download the paper using `download_paper`.
   This will save the paper to the local filesystem in pdf format. Let the user
   know where the paper was saved to.
4. Now, index the paper using `index_file`. Save the returned paper text for the
   next step.
5. Next, use the text of the paper and call `summarize_paper` to get a summary of the
   paper. When you are done, pass that summary to the user (in markdown format).
6. Ask the user if they want any changes to the summary. If so, use the paper text,
   the original summary, and the requested changes to improve the summary by calling
   `summarize_paper` again with modified instructions.
7. Show the improved summary to the user and ask if they want further improvements. If so,
   repeat steps 6 and 7 until they are happy with the summary.
8. Save the final summary using the `save_summary` tool and let the user know where the
   summary was saved.

Remember to maintain conversation state and always ask the user for confirmation or
feedback before proceeding to the next step. Be conversational and helpful throughout
the process.
"""

class InteractiveSummarizerAgent:
    """A wrapper class that provides an interactive summarizer agent with conversation state."""
    
    def __init__(self):
        from .arxiv_downloader import search_arxiv_papers, download_paper
        from .vector_store import index_file
        
        # Create the FunctionAgent with better conversational capabilities
        self.agent = FunctionAgent(
            tools=[search_arxiv_papers, download_paper, index_file, summarize_paper, save_summary],
            llm=OpenAI(model=DEFAULT_MODEL_NAME),
            system_prompt=SUMMARIZER_AGENT_PROMPT,
        )
        
        # Track conversation state
        self.conversation_state = {
            'current_paper': None,
            'paper_text': None,
            'current_summary': None,
            'step': 'search'
        }
        
        # Store conversation history
        self.conversation_history = []
    
    def run(self, message: str) -> str:
        """Send a message to the agent and get a response."""
        import asyncio
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})
        
        # The FunctionAgent.run() method expects to be run in an async context
        # Let's create a proper async runner
        async def async_runner():
            return await self.agent.run(message)
        
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in a loop, we need to run in a thread with a new loop
            import concurrent.futures
            import threading
            
            def run_in_new_thread():
                # Create a new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(async_runner())
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_thread)
                response = future.result()
        except RuntimeError:
            # No event loop running, we can create one
            response = asyncio.run(async_runner())
        
        # Add response to conversation history
        self.conversation_history.append({"role": "assistant", "content": str(response)})
        
        return str(response)
    
    async def arun(self, message: str) -> str:
        """Async version of run method."""
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Run the agent with the message asynchronously
        response = await self.agent.run(message)
        
        # Add response to conversation history
        self.conversation_history.append({"role": "assistant", "content": str(response)})
        
        return str(response)
    
    def reset(self):
        """Reset the conversation state and history."""
        self.conversation_state = {
            'current_paper': None,
            'paper_text': None,
            'current_summary': None,
            'step': 'search'
        }
        self.conversation_history = []
    
    def get_conversation_history(self):
        """Get the conversation history."""
        return self.conversation_history.copy()
    
    def get_state(self):
        """Get the current conversation state."""
        return self.conversation_state.copy()


def make_summarizer_agent():
    """Create an interactive summarizer agent that supports multiple user interactions."""
    return InteractiveSummarizerAgent()
