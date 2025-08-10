"""This is a LlamaIndex workflow for adding new papers.
The overall flow is:
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
"""

from pydantic import Field
from llama_index.core.workflow import (
    Event,
    Workflow,
    step,
    StartEvent,
    StopEvent,
    Context, # Context is available, but for this demo, simple self._state is used for clarity
)
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from .file_locations import FileLocations, FILE_LOCATIONS
from .arxiv_downloader import search_arxiv_papers, download_paper
from .vector_store import index_file
from .summarizer import summarize_paper, save_summary

class AddPaperWorkflow(Workflow):
    """
    LlamaIndex Workflow to guide a user through finding, downloading,
    indexing, summarizing, and refining summaries of Arxiv papers.
    """
    llm: LLM = Field(description="The LLM instance to use for summarization.")
    file_locations: FileLocations = Field(description="Locations for storing pdfs, summaries, and the document index.")

    def __init__(self, llm: LLM, file_locations:FileLocations=FILE_LOCATIONS, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.file_locations = file_locations
        # Register tools with the workflow
        self.tools = {
            "search_arxiv_papers": FunctionTool.from_defaults(fn=search_arxiv_papers),
            "download_paper": FunctionTool.from_defaults(fn=download_paper),
            "index_file": FunctionTool.from_defaults(fn=index_file),
            "summarize_paper": FunctionTool.from_defaults(fn=summarize_paper),
            "save_summary": FunctionTool.from_defaults(fn=save_summary),
        }
        # Internal state to store data across workflow steps for convenience
        self._workflow_data = {} 
        # TODO: implement the rest of the workflow