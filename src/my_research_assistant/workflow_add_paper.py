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
from typing import List, Optional
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
from .types import PaperMetadata


# Define custom events for the workflow
class SearchResultsEvent(Event):
    """Event containing search results"""
    papers: List[PaperMetadata]
    query: str


class PaperSelectedEvent(Event):
    """Event when a paper is selected by the user"""
    paper: PaperMetadata


class PaperDownloadedEvent(Event):
    """Event when paper is successfully downloaded"""
    paper: PaperMetadata
    local_path: str


class PaperIndexedEvent(Event):
    """Event when paper is successfully indexed"""
    paper: PaperMetadata
    paper_text: str


class SummaryGeneratedEvent(Event):
    """Event when summary is generated"""
    paper: PaperMetadata
    summary: str
    paper_text: str


class SummaryImproveEvent(Event):
    """Event to improve the summary based on user feedback"""
    paper: PaperMetadata
    current_summary: str
    paper_text: str
    feedback: str


class SummarySavedEvent(Event):
    """Event when summary is saved to filesystem"""
    paper: PaperMetadata
    summary: str
    file_path: str

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
    
    @step
    async def search_papers(self, ctx: Context, ev: StartEvent) -> SearchResultsEvent | StopEvent:
        """Step 1: Search for papers matching user criteria"""
        query = str(ev.query)
        ctx.write_event_to_stream(
            StopEvent(result=f"🔍 Searching for papers matching: '{query}'...")
        )
        
        try:
            # Search for papers (default k=5 for initial search to show options)
            papers = search_arxiv_papers(query, k=5)
            
            if not papers:
                return StopEvent(result=f"❌ No papers found matching '{query}'. Please try a different search term.")
            
            # Present results to user
            result_text = f"📄 Found {len(papers)} paper(s):\n\n"
            for i, paper in enumerate(papers, 1):
                result_text += f"{i}. **{paper.title}**\n"
                result_text += f"   - Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}\n"
                result_text += f"   - Categories: {', '.join(paper.categories[:2])}{'...' if len(paper.categories) > 2 else ''}\n"
                result_text += f"   - Published: {paper.published.strftime('%Y-%m-%d')}\n"
                result_text += f"   - Paper ID: {paper.paper_id}\n\n"
            
            if len(papers) == 1:
                result_text += "This is the best match. Would you like to proceed with this paper? (Reply 'yes' to continue or provide more specific search terms)"
            else:
                result_text += "Please select a paper by number (1-5) or provide more specific search terms if none match what you're looking for."
            
            ctx.write_event_to_stream(StopEvent(result=result_text))
            return SearchResultsEvent(papers=papers, query=query)
        except Exception as e:
            return StopEvent(result=f"❌ Search failed: {str(e)}")
    
    @step
    async def handle_paper_selection(self, ctx: Context, ev: SearchResultsEvent) -> PaperSelectedEvent | StopEvent:
        """Step 2: Handle user paper selection or refined search"""
        # This step would typically wait for user input in an interactive setting
        # For now, we'll assume the first paper is selected
        # In a real implementation, this would need to handle user input
        
        try:
            if not ev.papers:
                return StopEvent(result="❌ No papers available to select")
            
            selected_paper = ev.papers[0]  # Default to first paper
            
            ctx.write_event_to_stream(
                StopEvent(result=f"✅ Selected paper: '{selected_paper.title}' by {', '.join(selected_paper.authors[:2])}{'...' if len(selected_paper.authors) > 2 else ''}")
            )
            
            return PaperSelectedEvent(paper=selected_paper)
        except Exception as e:
            return StopEvent(result=f"❌ Paper selection failed: {str(e)}")
    
    @step
    async def download_paper_step(self, ctx: Context, ev: PaperSelectedEvent) -> PaperDownloadedEvent | StopEvent:
        """Step 3: Download the selected paper"""
        paper = ev.paper
        
        ctx.write_event_to_stream(
            StopEvent(result=f"📥 Downloading paper: '{paper.title}'...")
        )
        
        try:
            local_path = download_paper(paper, self.file_locations)
            ctx.write_event_to_stream(
                StopEvent(result=f"✅ Paper downloaded successfully to: {local_path}")
            )
            return PaperDownloadedEvent(paper=paper, local_path=local_path)
        except Exception as e:
            return StopEvent(result=f"❌ Download failed: {str(e)}")
    
    @step
    async def index_paper_step(self, ctx: Context, ev: PaperDownloadedEvent) -> PaperIndexedEvent | StopEvent:
        """Step 4: Index the downloaded paper"""
        paper = ev.paper
        
        ctx.write_event_to_stream(
            StopEvent(result=f"🔍 Indexing paper: '{paper.title}'...")
        )
        
        try:
            paper_text = index_file(paper)
            ctx.write_event_to_stream(
                StopEvent(result=f"✅ Paper indexed successfully. Extracted {len(paper_text)} characters of text.")
            )
            return PaperIndexedEvent(paper=paper, paper_text=paper_text)
        except Exception as e:
            return StopEvent(result=f"❌ Indexing failed: {str(e)}")
    
    @step
    async def generate_summary_step(self, ctx: Context, ev: PaperIndexedEvent) -> SummaryGeneratedEvent | StopEvent:
        """Step 5: Generate initial summary"""
        paper = ev.paper
        paper_text = ev.paper_text
        
        ctx.write_event_to_stream(
            StopEvent(result=f"📝 Generating summary for: '{paper.title}'...")
        )
        
        try:
            summary = summarize_paper(paper_text, paper)
            ctx.write_event_to_stream(
                StopEvent(result=f"✅ Summary generated successfully!\n\n{summary}\n\n---\nWould you like any changes to this summary? If so, please provide your feedback.")
            )
            return SummaryGeneratedEvent(paper=paper, summary=summary, paper_text=paper_text)
        except Exception as e:
            return StopEvent(result=f"❌ Summary generation failed: {str(e)}")
    
    @step
    async def improve_summary_step(self, ctx: Context, ev: SummaryImproveEvent) -> SummaryGeneratedEvent | StopEvent:
        """Step 6-7: Improve summary based on user feedback"""
        paper = ev.paper
        current_summary = ev.current_summary
        paper_text = ev.paper_text
        feedback = ev.feedback
        
        ctx.write_event_to_stream(
            StopEvent(result=f"🔄 Improving summary based on feedback: '{feedback}'...")
        )
        
        try:
            improved_summary = summarize_paper(paper_text, paper, feedback=feedback, previous_summary=current_summary)
            ctx.write_event_to_stream(
                StopEvent(result=f"✅ Summary improved!\n\n{improved_summary}\n\n---\nWould you like any further changes? If not, reply 'save' to save the summary.")
            )
            return SummaryGeneratedEvent(paper=paper, summary=improved_summary, paper_text=paper_text)
        except Exception as e:
            return StopEvent(result=f"❌ Summary improvement failed: {str(e)}")
    
    @step
    async def save_summary_step(self, ctx: Context, ev: SummaryGeneratedEvent) -> StopEvent:
        """Step 8: Save the final summary"""
        paper = ev.paper
        summary = ev.summary
        
        ctx.write_event_to_stream(
            StopEvent(result=f"💾 Saving summary for: '{paper.title}'...")
        )
        
        try:
            file_path = save_summary(summary, paper.paper_id)
            result_message = f"✅ Summary saved successfully!\n\n**File location**: {file_path}\n\n**Process completed successfully!**\n\nThe paper '{paper.title}' has been:\n- Downloaded\n- Indexed for search\n- Summarized\n- Saved to your summaries directory"
            
            return StopEvent(result=result_message)
        except Exception as e:
            return StopEvent(result=f"❌ Summary save failed: {str(e)}")


class WorkflowRunner:
    """Helper class to run the AddPaperWorkflow with user interaction"""
    
    def __init__(self, llm: LLM, file_locations: FileLocations = FILE_LOCATIONS):
        self.workflow = AddPaperWorkflow(llm=llm, file_locations=file_locations)
        self.current_state = None
    
    async def start_workflow(self, query: str):
        """Start the workflow with a search query"""
        handler = self.workflow.run(query=query)
        
        async for event in handler.stream_events():
            if isinstance(event, StopEvent):
                print(event.result)
                return event.result
        
        return "Workflow completed"
    
    async def continue_workflow(self, user_input: str, current_papers: Optional[List[PaperMetadata]] = None):
        """Continue the workflow based on user input"""
        # This would handle user selections and feedback
        # Implementation depends on how user interaction is managed
        pass