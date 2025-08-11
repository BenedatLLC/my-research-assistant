"""This is a LlamaIndex workflow for the Research Assistant.

The workflow supports multiple operations:

1. ADD PAPER WORKFLOW:
   - Find and add new papers to the research collection
   - Download, index, summarize, and refine summaries

2. SEMANTIC SEARCH WORKFLOW:
   - Search the indexed paper collection using semantic search
   - Summarize results with references and links to local files

The overall add paper flow:
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
from .vector_store import index_file, search_index
from .summarizer import summarize_paper, save_summary
from .types import PaperMetadata, SearchResult


# Define custom events for the workflow
class SearchResultsEvent(Event):
    """Event containing ArXiv search results"""
    papers: List[PaperMetadata]
    query: str


class SemanticSearchEvent(Event):
    """Event for semantic search in the local index"""
    query: str


class SemanticSearchResultsEvent(Event):
    """Event containing semantic search results from the local index"""
    results: List[SearchResult]
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


class ResearchAssistantWorkflow(Workflow):
    """
    LlamaIndex Workflow for research assistant operations.
    
    Supports:
    - Adding new papers (search ArXiv, download, index, summarize)
    - Semantic search of existing indexed papers
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
            "search_index": FunctionTool.from_defaults(fn=search_index),
            "summarize_paper": FunctionTool.from_defaults(fn=summarize_paper),
            "save_summary": FunctionTool.from_defaults(fn=save_summary),
        }
    
    # === WORKFLOW ROUTING ===
    
    @step
    async def route_workflow(self, ctx: Context, ev: StartEvent) -> SearchResultsEvent | SemanticSearchEvent | StopEvent:
        """Route to the appropriate workflow based on parameters"""
        workflow_type = getattr(ev, 'workflow_type', 'add_paper')
        query = str(ev.query)
        
        if workflow_type == 'semantic_search':
            return SemanticSearchEvent(query=query)
        else:
            # Default to add paper workflow
            return await self.search_papers_impl(ctx, query)
    
    # === ADD PAPER WORKFLOW ===
    
    async def search_papers_impl(self, ctx: Context, query: str) -> SearchResultsEvent | StopEvent:
        """Implementation of paper search"""
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

    # === SEMANTIC SEARCH WORKFLOW ===
    
    @step
    async def semantic_search(self, ctx: Context, ev: SemanticSearchEvent) -> SemanticSearchResultsEvent | StopEvent:
        """Perform semantic search on the indexed paper collection"""
        query = ev.query
        
        ctx.write_event_to_stream(
            StopEvent(result=f"🔍 Searching local paper index for: '{query}'...")
        )
        
        try:
            # Search the local index
            results = search_index(query, k=10, file_locations=self.file_locations)
            
            if not results:
                return StopEvent(result=f"❌ No results found in local index for '{query}'. Try adding more papers or using different search terms.")
            
            ctx.write_event_to_stream(
                StopEvent(result=f"✅ Found {len(results)} relevant chunks from {len(set(r.paper_id for r in results))} paper(s)")
            )
            
            return SemanticSearchResultsEvent(results=results, query=query)
        except Exception as e:
            return StopEvent(result=f"❌ Semantic search failed: {str(e)}")
    
    @step
    async def summarize_search_results(self, ctx: Context, ev: SemanticSearchResultsEvent) -> StopEvent:
        """Summarize semantic search results with references and links"""
        results = ev.results
        query = ev.query
        
        ctx.write_event_to_stream(
            StopEvent(result=f"📝 Generating summary of search results for: '{query}'...")
        )
        
        try:
            # Group results by paper
            papers_dict = {}
            for result in results:
                if result.paper_id not in papers_dict:
                    papers_dict[result.paper_id] = {
                        'title': result.paper_title,
                        'pdf_filename': result.pdf_filename,
                        'summary_filename': result.summary_filename,
                        'chunks': []
                    }
                papers_dict[result.paper_id]['chunks'].append({
                    'text': result.chunk,
                    'page': result.page
                })
            
            # Create context for LLM summarization
            context_text = ""
            for paper_id, paper_data in papers_dict.items():
                context_text += f"\n## Paper: {paper_data['title']} (ID: {paper_id})\n"
                for chunk in paper_data['chunks']:
                    context_text += f"[Page {chunk['page']}] {chunk['text']}\n\n"
            
            # Generate summary using LLM
            summary_prompt = f"""Based on the following search results for the query "{query}", provide a comprehensive summary that synthesizes the key insights and findings. Include relevant details and organize the information clearly.

Search Results:
{context_text}

Please provide a well-structured summary that addresses the query and highlights the most relevant information from these papers."""
            
            summary_response = await self.llm.acomplete(summary_prompt)
            summary_text = summary_response.text
            
            # Create final response with references and links
            final_response = f"# Search Results Summary: {query}\n\n"
            final_response += f"{summary_text}\n\n"
            
            # Add references section
            final_response += "## References and Sources\n\n"
            for paper_id, paper_data in papers_dict.items():
                final_response += f"### {paper_data['title']}\n"
                final_response += f"- **Paper ID**: {paper_id}\n"
                final_response += f"- **PDF File**: `{self.file_locations.pdfs_dir}/{paper_data['pdf_filename']}`\n"
                if paper_data['summary_filename']:
                    final_response += f"- **Summary File**: `{self.file_locations.summaries_dir}/{paper_data['summary_filename']}`\n"
                else:
                    final_response += f"- **Summary File**: Not available\n"
                
                # Show relevant pages
                pages = sorted(set(chunk['page'] for chunk in paper_data['chunks']))
                if len(pages) == 1:
                    final_response += f"- **Relevant Page**: {pages[0]}\n"
                else:
                    final_response += f"- **Relevant Pages**: {', '.join(map(str, pages))}\n"
                final_response += "\n"
            
            # Add search statistics
            final_response += f"## Search Statistics\n"
            final_response += f"- **Query**: {query}\n"
            final_response += f"- **Results**: {len(results)} relevant text chunks\n"
            final_response += f"- **Papers**: {len(papers_dict)} unique papers\n"
            final_response += f"- **Index Location**: `{self.file_locations.index_dir}`\n"
            
            return StopEvent(result=final_response)
            
        except Exception as e:
            return StopEvent(result=f"❌ Failed to summarize search results: {str(e)}")


class WorkflowRunner:
    """Helper class to run the ResearchAssistantWorkflow with user interaction"""
    
    def __init__(self, llm: LLM, file_locations: FileLocations = FILE_LOCATIONS):
        self.workflow = ResearchAssistantWorkflow(llm=llm, file_locations=file_locations)
        self.current_state = None
    
    async def start_add_paper_workflow(self, query: str):
        """Start the add paper workflow with a search query"""
        handler = self.workflow.run(query=query)
        
        async for event in handler.stream_events():
            if isinstance(event, StopEvent):
                print(event.result)
                return event.result
        
        return "Add paper workflow completed"
    
    async def start_semantic_search_workflow(self, query: str):
        """Start the semantic search workflow"""
        try:
            # Directly call the semantic search methods
            from .vector_store import search_index
            
            print(f"🔍 Searching local paper index for: '{query}'...")
            
            # Search the local index
            results = search_index(query, k=10, file_locations=self.workflow.file_locations)
            
            if not results:
                return f"❌ No results found in local index for '{query}'. Try adding more papers or using different search terms."
            
            print(f"✅ Found {len(results)} relevant chunks from {len(set(r.paper_id for r in results))} paper(s)")
            
            # Group results by paper
            papers_dict = {}
            for result in results:
                if result.paper_id not in papers_dict:
                    papers_dict[result.paper_id] = {
                        'title': result.paper_title,
                        'pdf_filename': result.pdf_filename,
                        'summary_filename': result.summary_filename,
                        'chunks': []
                    }
                papers_dict[result.paper_id]['chunks'].append({
                    'text': result.chunk,
                    'page': result.page
                })
            
            # Create context for LLM summarization
            context_text = ""
            for paper_id, paper_data in papers_dict.items():
                context_text += f"\n## Paper: {paper_data['title']} (ID: {paper_id})\n"
                for chunk in paper_data['chunks']:
                    context_text += f"[Page {chunk['page']}] {chunk['text']}\n\n"
            
            print(f"📝 Generating summary of search results for: '{query}'...")
            
            # Generate summary using LLM
            summary_prompt = f"""Based on the following search results for the query "{query}", provide a comprehensive summary that synthesizes the key insights and findings. Include relevant details and organize the information clearly.

Search Results:
{context_text}

Please provide a well-structured summary that addresses the query and highlights the most relevant information from these papers."""
            
            summary_response = await self.workflow.llm.acomplete(summary_prompt)
            summary_text = summary_response.text
            
            # Create final response with references and links
            final_response = f"# Search Results Summary: {query}\n\n"
            final_response += f"{summary_text}\n\n"
            
            # Add references section
            final_response += "## References and Sources\n\n"
            for paper_id, paper_data in papers_dict.items():
                final_response += f"### {paper_data['title']}\n"
                final_response += f"- **Paper ID**: {paper_id}\n"
                final_response += f"- **PDF File**: `{self.workflow.file_locations.pdfs_dir}/{paper_data['pdf_filename']}`\n"
                if paper_data['summary_filename']:
                    final_response += f"- **Summary File**: `{self.workflow.file_locations.summaries_dir}/{paper_data['summary_filename']}`\n"
                else:
                    final_response += f"- **Summary File**: Not available\n"
                
                # Show relevant pages
                pages = sorted(set(chunk['page'] for chunk in paper_data['chunks']))
                if len(pages) == 1:
                    final_response += f"- **Relevant Page**: {pages[0]}\n"
                else:
                    final_response += f"- **Relevant Pages**: {', '.join(map(str, pages))}\n"
                final_response += "\n"
            
            # Add search statistics
            final_response += f"## Search Statistics\n"
            final_response += f"- **Query**: {query}\n"
            final_response += f"- **Results**: {len(results)} relevant text chunks\n"
            final_response += f"- **Papers**: {len(papers_dict)} unique papers\n"
            final_response += f"- **Index Location**: `{self.workflow.file_locations.index_dir}`\n"
            
            return final_response
            
        except Exception as e:
            return f"❌ Semantic search failed: {str(e)}"
    
    async def continue_workflow(self, user_input: str, current_papers: Optional[List[PaperMetadata]] = None):
        """Continue the workflow based on user input"""
        # This would handle user selections and feedback
        # Implementation depends on how user interaction is managed
        pass