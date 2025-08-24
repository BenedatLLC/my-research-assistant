"""UI-agnostic workflow system for the Research Assistant.

This module implements a LlamaIndex-based workflow architecture that separates 
business logic from UI presentation. The system supports multiple interface types 
(terminal, web, API) through the InterfaceAdapter pattern.

## Architecture Overview

The workflow system is built on three main components:

1. **ResearchAssistantWorkflow**: Core LlamaIndex workflow containing business logic
2. **WorkflowRunner**: High-level interface for executing workflows with user interaction
3. **InterfaceAdapter**: Abstract interface for UI-agnostic user interaction

## Supported Workflows

### ADD PAPER WORKFLOW:
- Search ArXiv for papers matching user criteria
- User selection of preferred paper from results
- Download paper to local filesystem  
- Index paper content for semantic search
- Generate AI-powered summary
- Allow iterative summary refinement
- Save final summary to filesystem

### SEMANTIC SEARCH WORKFLOW:
- Search indexed paper collection using semantic similarity
- Aggregate and summarize relevant content chunks
- Provide references with page numbers and file paths
- Display search statistics and metadata

## Interface Compatibility

The workflow system is designed to work with multiple interface types:

- **Terminal**: Rich console interface with progress indicators and formatting
- **Web**: Future HTTP/WebSocket interface for web applications
- **API**: Future RESTful API for programmatic access

## Key Design Principles

- **Separation of Concerns**: UI logic separated from business logic
- **Extensibility**: Easy to add new interface types or workflow steps
- **Testability**: Business logic can be tested independently of UI
- **Consistency**: Same behavior across all interface types
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
from .project_types import PaperMetadata, SearchResult
from .interface_adapter import InterfaceAdapter


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
    Core LlamaIndex workflow for research assistant operations.
    
    This class implements the business logic for paper management and search
    operations using the LlamaIndex workflow framework. It handles:
    
    - ArXiv paper search and selection
    - PDF download and local storage
    - Content indexing for semantic search
    - AI-powered summarization with iterative refinement
    - Semantic search across indexed papers with result aggregation
    
    The workflow is UI-agnostic and communicates through an InterfaceAdapter
    to support multiple interface types (terminal, web, API).
    
    Attributes:
        llm: Language model instance for summarization tasks
        interface: UI adapter for user interaction and feedback
        file_locations: Configuration for file storage locations
        tools: Registered function tools for workflow operations
    """
    llm: LLM = Field(description="The LLM instance to use for summarization.")
    file_locations: FileLocations = Field(description="Locations for storing pdfs, summaries, and the document index.")
    interface: InterfaceAdapter = Field(description="Interface adapter for UI-agnostic operations.")

    def __init__(self, llm: LLM, interface: InterfaceAdapter, file_locations:FileLocations=FILE_LOCATIONS, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.interface = interface
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
        elif workflow_type == 'add_paper':
            return await self.search_papers_impl(ctx, query)
        else:
            return StopEvent(result=f"❌ Unknown workflow type: {workflow_type}")
    
    # === ADD PAPER WORKFLOW ===
    
    async def search_papers_impl(self, ctx: Context, query: str) -> SearchResultsEvent | StopEvent:
        """Implementation of paper search"""
        try:
            ctx.write_event_to_stream(
                StopEvent(result=f"🔍 Searching for papers matching: '{query}'...")
            )
            
            with self.interface.progress_context(f"🔍 Searching for papers matching: '{query}'..."):
                # Search for papers (default k=5 for initial search to show options)
                try:
                    papers = search_arxiv_papers(query, k=5)
                except Exception as e:
                    # Immediately handle search API exceptions
                    self.interface.show_error(f"Search failed: {str(e)}")
                    return StopEvent(result=f"Search failed: {str(e)}")
            
            if not papers:
                self.interface.show_error(f"No papers found matching '{query}'. Please try a different search term.")
                return StopEvent(result="No papers found")
            
            # Display papers using the interface adapter
            self.interface.display_papers(papers)
            
            ctx.write_event_to_stream(
                SearchResultsEvent(papers=papers, query=query)
            )
            
            return SearchResultsEvent(papers=papers, query=query)
        except Exception as e:
            self.interface.show_error(f"Search failed: {str(e)}")
            return StopEvent(result=f"Search failed: {str(e)}")
    
    
    @step
    async def handle_paper_selection(self, ctx: Context, ev: SearchResultsEvent) -> PaperSelectedEvent | StopEvent:
        """Step 2: Handle user paper selection or refined search"""
        try:
            if not ev.papers:
                self.interface.show_error("No papers available to select")
                return StopEvent(result="No papers available to select")
            
            # In interactive mode, this would get user input
            # For now, auto-select first paper for single results
            if len(ev.papers) == 1:
                selected_paper = ev.papers[0]
                self.interface.show_success(
                    f"Selected paper: '{selected_paper.title}' by {', '.join(selected_paper.authors[:2])}{'...' if len(selected_paper.authors) > 2 else ''}"
                )
                return PaperSelectedEvent(paper=selected_paper)
            else:
                # Multiple papers - wait for selection (handled by interface layer)
                return StopEvent(result="Multiple papers found - awaiting selection")
                
        except Exception as e:
            self.interface.show_error(f"Paper selection failed: {str(e)}")
            return StopEvent(result=f"Paper selection failed: {str(e)}")
    
    @step
    async def download_paper_step(self, ctx: Context, ev: PaperSelectedEvent) -> PaperDownloadedEvent | StopEvent:
        """Step 3: Download the selected paper"""
        paper = ev.paper
        
        try:
            with self.interface.progress_context(f"📥 Downloading paper: '{paper.title}'..."):
                local_path = download_paper(paper, self.file_locations)
            
            self.interface.show_success(f"Paper downloaded successfully to: {local_path}")
            return PaperDownloadedEvent(paper=paper, local_path=local_path)
        except Exception as e:
            self.interface.show_error(f"Download failed: {str(e)}")
            return StopEvent(result=f"Download failed: {str(e)}")
    
    @step
    async def index_paper_step(self, ctx: Context, ev: PaperDownloadedEvent) -> PaperIndexedEvent | StopEvent:
        """Step 4: Index the downloaded paper"""
        paper = ev.paper
        
        try:
            with self.interface.progress_context(f"🔍 Indexing paper: '{paper.title}'..."):
                paper_text = index_file(paper)
            
            self.interface.show_success(f"Paper indexed successfully. Extracted {len(paper_text)} characters of text.")
            return PaperIndexedEvent(paper=paper, paper_text=paper_text)
        except Exception as e:
            self.interface.show_error(f"Indexing failed: {str(e)}")
            return StopEvent(result=f"Indexing failed: {str(e)}")
    
    @step
    async def generate_summary_step(self, ctx: Context, ev: PaperIndexedEvent) -> SummaryGeneratedEvent | StopEvent:
        """Step 5: Generate initial summary"""
        paper = ev.paper
        paper_text = ev.paper_text
        
        try:
            with self.interface.progress_context(f"📝 Generating summary for: '{paper.title}'..."):
                summary = summarize_paper(paper_text, paper)
            
            self.interface.show_success("Summary generated successfully!")
            self.interface.render_content(summary, "markdown", "📝 Summary")
            self.interface.show_info("Would you like any changes to this summary? If so, please provide your feedback.")
            
            return SummaryGeneratedEvent(paper=paper, summary=summary, paper_text=paper_text)
        except Exception as e:
            self.interface.show_error(f"Summary generation failed: {str(e)}")
            return StopEvent(result=f"Summary generation failed: {str(e)}")
    
    @step
    async def improve_summary_step(self, ctx: Context, ev: SummaryImproveEvent) -> SummaryGeneratedEvent | StopEvent:
        """Step 6-7: Improve summary based on user feedback"""
        paper = ev.paper
        current_summary = ev.current_summary
        paper_text = ev.paper_text
        feedback = ev.feedback
        
        try:
            with self.interface.progress_context(f"🔄 Improving summary based on feedback: '{feedback}'..."):
                improved_summary = summarize_paper(paper_text, paper, feedback=feedback, previous_summary=current_summary)
            
            self.interface.show_success("Summary improved!")
            self.interface.render_content(improved_summary, "markdown", "📝 Improved Summary")
            self.interface.show_info("Would you like any further changes? If not, reply 'save' to save the summary.")
            
            return SummaryGeneratedEvent(paper=paper, summary=improved_summary, paper_text=paper_text)
        except Exception as e:
            self.interface.show_error(f"Summary improvement failed: {str(e)}")
            return StopEvent(result=f"Summary improvement failed: {str(e)}")
    
    @step
    async def save_summary_step(self, ctx: Context, ev: SummaryGeneratedEvent) -> StopEvent:
        """Step 8: Save the final summary"""
        paper = ev.paper
        summary = ev.summary
        
        try:
            with self.interface.progress_context(f"💾 Saving summary for: '{paper.title}'..."):
                file_path = save_summary(summary, paper.paper_id)
            
            completion_message = f"""🎉 **Process Complete!**

**Paper:** {paper.title}
**Actions Completed:**
  • Downloaded PDF
  • Indexed for search
  • Generated summary
  • Saved to filesystem

**Summary Location:** {file_path}

You can now find another paper or start a new search."""
            
            self.interface.render_content(completion_message, "markdown", "✅ Success")
            return StopEvent(result=f"Summary saved successfully: {file_path}")
        except Exception as e:
            self.interface.show_error(f"Summary save failed: {str(e)}")
            return StopEvent(result=f"Summary save failed: {str(e)}")

    # === SEMANTIC SEARCH WORKFLOW ===
    
    @step
    async def semantic_search(self, ctx: Context, ev: SemanticSearchEvent) -> SemanticSearchResultsEvent | StopEvent:
        """Perform semantic search on the indexed paper collection"""
        query = ev.query
        
        try:
            with self.interface.progress_context(f"🔍 Searching local paper index for: '{query}'..."):
                # Search the local index
                results = search_index(query, k=10, file_locations=self.file_locations)
            
            if not results:
                self.interface.show_error(f"No results found in local index for '{query}'. Try adding more papers or using different search terms.")
                return StopEvent(result=f"No results found for '{query}'")
            
            self.interface.show_success(f"Found {len(results)} relevant chunks from {len(set(r.paper_id for r in results))} paper(s)")
            
            return SemanticSearchResultsEvent(results=results, query=query)
        except Exception as e:
            self.interface.show_error(f"Semantic search failed: {str(e)}")
            return StopEvent(result=f"Semantic search failed: {str(e)}")
    
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
    """
    High-level interface for executing research workflows with user interaction.
    
    This class provides a simplified API for running complex research workflows
    while handling the intricacies of the LlamaIndex workflow system. It serves
    as the primary entry point for UI layers and abstracts away workflow
    event handling and state management.
    
    Key responsibilities:
    - Execute complete paper processing workflows (search → download → index → summarize)
    - Handle semantic search operations with result aggregation
    - Manage workflow state and user interaction flows
    - Provide methods for summary refinement and saving
    - Bridge between UI layer and core workflow logic
    
    This class works with any InterfaceAdapter implementation, making it suitable
    for terminal applications, web interfaces, or programmatic API access.
    
    Attributes:
        workflow: Core ResearchAssistantWorkflow instance
        interface: UI adapter for user interaction
        current_state: Current workflow state for interaction tracking
    """
    
    def __init__(self, llm: LLM, interface: InterfaceAdapter, file_locations: FileLocations = FILE_LOCATIONS):
        self.workflow = ResearchAssistantWorkflow(llm=llm, interface=interface, file_locations=file_locations)
        self.interface = interface
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
                
                # Create plain text file paths
                pdf_path = f"{self.workflow.file_locations.pdfs_dir}/{paper_data['pdf_filename']}"
                final_response += f"- **PDF File**: {pdf_path}\n"
                
                if paper_data['summary_filename']:
                    summary_path = f"{self.workflow.file_locations.summaries_dir}/{paper_data['summary_filename']}"
                    final_response += f"- **Summary File**: {summary_path}\n"
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