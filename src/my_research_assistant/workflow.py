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
import os
from dataclasses import dataclass
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


# Define result classes for structured workflow returns
@dataclass
class QueryResult:
    """Result from a query operation (find, sem-search, research, list)."""
    success: bool
    papers: List[PaperMetadata]
    paper_ids: List[str]
    message: str
    content: Optional[str] = None  # For search/research results


@dataclass
class ProcessingResult:
    """Result from a processing operation (summarize, improve, etc.)."""
    success: bool
    paper: Optional[PaperMetadata]
    content: str
    message: str


@dataclass
class SaveResult:
    """Result from a save operation."""
    success: bool
    file_path: Optional[str]
    title: Optional[str]
    message: str


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
            
            # IMPORTANT ORDERING FIX:
            # The chat state machine stores last_query_set as a list of paper_ids sorted ascending.
            # Previously, we displayed papers in relevance (similarity) order while storing
            # sorted IDs, causing numbering mismatches (e.g., 'summarize 1' acted on a different paper).
            # To ensure numeric references map correctly, we now sort the PaperMetadata objects
            # themselves by paper_id ascending before display so the UI numbering matches the
            # internal state ordering.
            papers.sort(key=lambda p: p.paper_id)
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
    async def save_summary_step(self, ctx: Context, ev: SummaryGeneratedEvent) -> StopEvent:
        """Step 8: Save the final summary"""
        paper = ev.paper
        summary = ev.summary

        try:
            with self.interface.progress_context(f"💾 Saving summary for: '{paper.title}'..."):
                file_path = save_summary(summary, paper.paper_id)

            # Index the summary for semantic search
            with self.interface.progress_context(f"📚 Indexing summary for: '{paper.title}'..."):
                from .vector_store import index_summary
                index_summary(paper, self.file_locations)

            completion_message = f"""🎉 **Process Complete!**

**Paper:** {paper.title}
**Actions Completed:**
  • Downloaded PDF
  • Indexed for search
  • Generated summary
  • Saved to filesystem
  • Indexed summary for search

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
                # Search the local index with enhanced retrieval for better compound query handling
                # Use MMR with higher k and moderate similarity filtering for diverse, quality results
                results = search_index(
                    query,
                    k=20,  # Increased for compound queries
                    file_locations=self.file_locations,
                    use_mmr=True,  # Enable MMR for diversity
                    similarity_cutoff=0.6,  # Filter low-quality matches
                    mmr_alpha=0.5  # Balance relevance and diversity
                )
            
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
    
    async def start_add_paper_workflow(self, query: str) -> QueryResult:
        """Start the add paper workflow with a search query"""
        handler = self.workflow.run(query=query)

        found_papers = None
        result_message = ""

        async for event in handler.stream_events():
            # Capture papers when search results are found
            if isinstance(event, SearchResultsEvent):
                found_papers = event.papers

            if isinstance(event, StopEvent):
                result_message = event.result
                print(event.result)

        # Create structured result
        if found_papers:
            paper_ids = [paper.paper_id for paper in found_papers]
            return QueryResult(
                success=True,
                papers=found_papers,
                paper_ids=paper_ids,
                message=result_message,
                content=None
            )
        else:
            return QueryResult(
                success=False,
                papers=[],
                paper_ids=[],
                message=result_message or "No papers found",
                content=None
            )
    
    async def start_semantic_search_workflow(self, query: str) -> QueryResult:
        """Start the enhanced semantic search workflow with RAG summarization"""
        try:
            # Directly call the semantic search methods
            from .vector_store import search_index

            print(f"🔍 Searching local paper index for: '{query}'...")

            # Search the local index with enhanced retrieval for better compound query handling
            results = search_index(
                query,
                k=20,
                file_locations=self.workflow.file_locations,
                use_mmr=True,
                similarity_cutoff=0.6,
                mmr_alpha=0.5
            )

            if not results:
                no_results_message = f"""❌ **No relevant passages found**

I couldn't find any passages in the indexed papers that are relevant to your query: "{query}"

**Possible reasons:**
- No papers have been indexed yet
- The query terms don't match content in the indexed papers
- Try rephrasing your query with different keywords

**Suggestions:**
- Use the `list` command to see what papers are available
- Try broader search terms
- Use the `find` command to search for and download more papers on this topic"""
                return QueryResult(
                    success=False,
                    papers=[],
                    paper_ids=[],
                    message="No relevant passages found",
                    content=no_results_message
                )

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

            print(f"📝 Generating RAG summary for: '{query}'...")

            # Enhanced RAG prompt that focuses on answering the specific question
            rag_prompt = f"""You are a research assistant tasked with answering a specific question based on retrieved passages from academic papers.

QUESTION: {query}

RETRIEVED PASSAGES:
{context_text}

INSTRUCTIONS:
1. Carefully analyze the retrieved passages to determine if they contain information relevant to answering the question
2. If the passages contain relevant information, provide a comprehensive answer that:
   - Directly addresses the question
   - Synthesizes information from multiple sources when applicable
   - Cites specific findings or claims from the papers
   - Maintains scientific accuracy and nuance
3. If the passages do NOT contain sufficient information to answer the question, clearly state this limitation
4. Focus on answering the specific question rather than providing a general summary of the papers

RESPONSE FORMAT:
Provide your answer in a clear, well-structured format. Be specific about what the research shows and acknowledge any limitations in the available information."""

            rag_response = await self.workflow.llm.acomplete(rag_prompt)
            answer_text = rag_response.text

            print(f"🤖 LLM Response preview: {answer_text[:200]}...")

            # Check if the LLM indicated insufficient information (common patterns)
            # Only trigger if the response explicitly starts with insufficient information
            insufficient_patterns = [
                "the retrieved passages do not contain sufficient information",
                "cannot be answered based on",
                "not enough information to answer",
                "insufficient evidence to",
                "passages do not provide enough information",
                "cannot determine from the provided passages"
            ]

            answer_lower = answer_text.lower()
            if any(pattern in answer_lower for pattern in insufficient_patterns):
                # Return a response indicating insufficient information
                final_response = f"""❌ **Insufficient information to answer the question**

**Your Question:** {query}

**Analysis:** The retrieved passages from {len(papers_dict)} paper(s) do not contain sufficient information to adequately answer your question.

**What was found:** {len(results)} relevant text chunks were retrieved, but they don't provide enough context or specific information to address your query.

**Suggestions:**
- Try rephrasing your question with different keywords
- Search for more specific terms related to your question
- Use the `find` command to download more papers on this topic
- Consider breaking down complex questions into simpler parts"""

                # Still include the paper list for reference
                if papers_dict:
                    final_response += f"\n\n**Papers searched:**\n"
                    for i, (paper_id, paper_data) in enumerate(papers_dict.items(), 1):
                        final_response += f"{i}. {paper_data['title']} (ID: {paper_id})\n"

                return QueryResult(
                    success=False,
                    papers=[],
                    paper_ids=list(papers_dict.keys()),
                    message="Insufficient information to answer",
                    content=final_response
                )

            # Create final response with answer and numbered paper references
            final_response = f"# Answer: {query}\n\n"
            final_response += f"{answer_text}\n\n"

            # Add numbered references section
            final_response += "## Papers Used in This Answer\n\n"
            for i, (paper_id, paper_data) in enumerate(papers_dict.items(), 1):
                final_response += f"{i}. **{paper_data['title']}**\n"
                final_response += f"   - Paper ID: {paper_id}\n"

                # Show relevant pages for this paper
                pages = sorted(set(chunk['page'] for chunk in paper_data['chunks']))
                if len(pages) == 1:
                    final_response += f"   - Relevant page: {pages[0]}\n"
                else:
                    final_response += f"   - Relevant pages: {', '.join(map(str, pages))}\n"

                # Add file paths
                pdf_path = f"{self.workflow.file_locations.pdfs_dir}/{paper_data['pdf_filename']}"
                final_response += f"   - PDF: `{pdf_path}`\n"

                if paper_data['summary_filename']:
                    summary_path = f"{self.workflow.file_locations.summaries_dir}/{paper_data['summary_filename']}"
                    final_response += f"   - Summary: `{summary_path}`\n"

                final_response += "\n"

            # Add search metadata
            final_response += f"---\n\n"
            final_response += f"*Search details: Found {len(results)} relevant chunks across {len(papers_dict)} papers*"

            # Extract paper IDs from results
            paper_ids = list(papers_dict.keys())

            print(f"✅ Semantic search summary generated ({len(final_response)} characters)")

            return QueryResult(
                success=True,
                papers=[],  # Could populate with actual paper metadata if needed
                paper_ids=paper_ids,
                message="Semantic search completed successfully",
                content=final_response
            )

        except Exception as e:
            error_message = f"❌ Semantic search failed: {str(e)}"
            return QueryResult(
                success=False,
                papers=[],
                paper_ids=[],
                message=error_message,
                content=error_message
            )
    
    async def process_paper_selection(self, selected_paper: PaperMetadata):
        """Process a selected paper through the complete workflow"""
        try:
            from .arxiv_downloader import download_paper
            from .vector_store import index_file
            from .summarizer import summarize_paper, save_summary
            from .paper_manager import load_paper_summary

            # Step 1: Download the paper
            print(f"📥 Downloading paper: '{selected_paper.title}'...")
            local_path = download_paper(selected_paper, self.workflow.file_locations)
            print(f"✅ Paper downloaded successfully to: {local_path}")

            # Step 2: Index the paper
            print(f"🔍 Indexing paper: '{selected_paper.title}'...")
            paper_text = index_file(selected_paper)
            print(f"✅ Paper indexed successfully. Extracted {len(paper_text)} characters of text.")

            # Step 3: Check if summary already exists
            success, existing_summary = load_paper_summary(selected_paper.paper_id, self.workflow.file_locations)

            if success:
                # Summary already exists - return it
                print(f"📄 Summary already exists for: '{selected_paper.title}'")
                print("✅ Using existing summary.")
                summary = existing_summary
            else:
                # Generate new summary
                print(f"📝 Generating summary for: '{selected_paper.title}'...")
                summary = summarize_paper(paper_text, selected_paper)
                print("✅ Summary generated successfully!")

                # Save the summary
                print(f"💾 Saving summary...")
                save_summary(summary, selected_paper.paper_id)
                print("✅ Summary saved successfully!")

            # Return an object with the expected attributes
            class ProcessingResult:
                def __init__(self, paper, summary, paper_text):
                    self.paper = paper
                    self.summary = summary
                    self.paper_text = paper_text

            return ProcessingResult(selected_paper, summary, paper_text)

        except Exception as e:
            return f"❌ Paper processing failed: {str(e)}"

    async def improve_summary(self, paper: PaperMetadata, current_summary: str, paper_text: str, feedback: str):
        """Improve a summary based on user feedback"""
        try:
            from .summarizer import summarize_paper

            print(f"🔄 Improving summary based on feedback: '{feedback}'...")
            improved_summary = summarize_paper(paper_text, paper, feedback=feedback, previous_summary=current_summary)

            print("✅ Summary improved!")

            # Return an object with the summary attribute that chat.py expects
            class SummaryResult:
                def __init__(self, summary):
                    self.summary = summary

            return SummaryResult(improved_summary)
        except Exception as e:
            raise Exception(f"Summary improvement failed: {str(e)}")

    async def save_summary(self, paper: PaperMetadata, summary: str, paper_text: str):
        """Save a summary to the filesystem"""
        try:
            from .summarizer import save_summary
            from .vector_store import index_summary

            print(f"💾 Saving summary for: '{paper.title}'...")
            file_path = save_summary(summary, paper.paper_id)

            # Index the summary for semantic search
            print(f"📚 Indexing summary for: '{paper.title}'...")
            index_summary(paper, self.workflow.file_locations)

            completion_message = f"""🎉 **Summary Saved Successfully!**

**Paper:** {paper.title}
**Summary Location:** {file_path}

You can now find another paper or start a new search."""

            print(completion_message)
            return f"Summary saved successfully: {file_path}"
        except Exception as e:
            raise Exception(f"Summary save failed: {str(e)}")

    async def save_search_results(self, content: str, query: str, content_type: str = "search") -> SaveResult:
        """Save search or research results to a file with LLM-generated title."""
        try:
            # Generate a short title using LLM
            title_prompt = f"""Generate a short, descriptive title (3-6 words) for this {content_type} query: "{query}"

The title should:
- Be suitable for a filename
- Capture the main topic/concept
- Be concise and clear
- Use title case

Return only the title, nothing else."""

            title_response = await self.workflow.llm.acomplete(title_prompt)
            raw_title = title_response.text.strip()

            # Clean the title for filename use
            import re
            clean_title = re.sub(r'[^\w\s-]', '', raw_title)
            clean_title = re.sub(r'\s+', '-', clean_title)
            clean_title = clean_title.lower()

            # Create filename
            filename = f"{clean_title}.md"
            file_path = os.path.join(self.workflow.file_locations.results_dir, filename)

            # Ensure results directory exists
            self.workflow.file_locations.ensure_results_dir()

            # Create content with metadata
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            full_content = f"""---
title: {raw_title}
query: {query}
type: {content_type}
created: {timestamp}
---

{content}
"""

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            return SaveResult(
                success=True,
                file_path=file_path,
                title=raw_title,
                message=f"{content_type.title()} results saved to: {file_path}"
            )

        except Exception as e:
            return SaveResult(
                success=False,
                file_path=None,
                title=None,
                message=f"Failed to save {content_type} results: {str(e)}"
            )

    async def improve_content(self, current_content: str, feedback: str, content_type: str) -> ProcessingResult:
        """Improve content (summary, search results, research results) based on feedback."""
        try:
            improve_prompt = f"""Improve the following {content_type} based on the user's feedback.

Current {content_type}:
{current_content}

User feedback: "{feedback}"

Please provide an improved version that addresses the feedback while maintaining the same format and structure."""

            response = await self.workflow.llm.acomplete(improve_prompt)
            improved_content = response.text.strip()

            return ProcessingResult(
                success=True,
                paper=None,
                content=improved_content,
                message=f"{content_type.title()} improved successfully"
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                paper=None,
                content=current_content,
                message=f"Failed to improve {content_type}: {str(e)}"
            )

    async def get_list_of_papers(self) -> QueryResult:
        """Get list of all downloaded papers."""
        try:
            from .arxiv_downloader import get_downloaded_paper_ids, get_paper_metadata
            from .paper_manager import format_paper_list

            paper_ids = get_downloaded_paper_ids(self.workflow.file_locations)
            papers = []

            for paper_id in paper_ids:
                try:
                    paper_metadata = get_paper_metadata(paper_id)
                    if paper_metadata:
                        papers.append(paper_metadata)
                except Exception:
                    continue

            # Sort papers by paper ID ascending
            papers.sort(key=lambda p: p.paper_id)

            if not papers:
                content = """# Downloaded Papers

📭 **No papers have been downloaded yet.**

💡 **Get started by finding papers:**
- Use `find <query>` to search ArXiv and download papers
- Example: `find machine learning transformers`
- Papers will be indexed automatically for semantic search"""

                return QueryResult(
                    success=True,
                    papers=[],
                    paper_ids=[],
                    message="No papers downloaded yet",
                    content=content
                )

            # Format the papers list
            content = format_paper_list(papers, "Downloaded Papers")

            # Add summary information
            content += f"\n\n## Summary\n\n"
            content += f"- **Total Papers**: {len(papers)}\n"
            content += f"- **Storage Location**: `{self.workflow.file_locations.pdfs_dir}`\n"
            content += f"- **Summaries Location**: `{self.workflow.file_locations.summaries_dir}`\n"
            content += f"- **Index Location**: `{self.workflow.file_locations.index_dir}`\n\n"
            content += "💡 **Next steps:**\n"
            content += "- Use `summary <number|id>` to view existing summaries\n"
            content += "- Use `open <number|id>` to view paper content\n"
            content += "- Use `sem-search <query>` to search across papers\n"

            return QueryResult(
                success=True,
                papers=papers,
                paper_ids=[paper.paper_id for paper in papers],  # Extract IDs from sorted papers
                message=f"Found {len(papers)} downloaded papers",
                content=content
            )

        except Exception as e:
            return QueryResult(
                success=False,
                papers=[],
                paper_ids=[],
                message=f"Failed to list papers: {str(e)}",
                content=f"❌ **Error listing papers**: {str(e)}"
            )

    async def research_query(self, query: str, num_summary_papers: int = 5, num_detail_chunks: int = 10) -> QueryResult:
        """
        Perform deep research query using two-stage approach.

        Stage 1: Search summary index to identify relevant papers
        Stage 2: Search content index within those papers for specific details
        Stage 3: Synthesize findings into comprehensive research answer

        Args:
            query: Research question to answer
            num_summary_papers: Number of papers to identify from summary search (default: 5)
            num_detail_chunks: Number of detailed chunks to retrieve from papers (default: 10)

        Returns:
            QueryResult with synthesized research findings and paper references
        """
        try:
            from .vector_store import search_summary_index, search_content_index_filtered
            from .paper_manager import format_research_result, get_papers_by_ids

            print(f"🔬 Starting research query: '{query}'...")

            # Stage 1: Search summary index to identify relevant papers
            print(f"📚 Stage 1: Searching summaries and notes to identify relevant papers...")
            summary_results = search_summary_index(
                query,
                k=num_summary_papers,
                file_locations=self.workflow.file_locations,
                use_mmr=True,  # Diverse papers
                similarity_cutoff=0.5  # Moderate threshold
            )

            if not summary_results:
                no_results_message = f"""❌ **No relevant papers found for research query**

**Your Question:** {query}

**Analysis:** No papers in the summary index were found to be relevant to this research question.

**Possible reasons:**
- No papers have been summarized yet
- The query terms don't match any summarized paper topics
- Try rephrasing your query with different keywords

**Suggestions:**
- Use the `list` command to see what papers have been summarized
- Use the `find` command to search for and download papers on this topic
- Try broader search terms
- Use `sem-search` to search the full content index instead"""

                return QueryResult(
                    success=False,
                    papers=[],
                    paper_ids=[],
                    message="No relevant papers found",
                    content=no_results_message
                )

            # Extract unique paper IDs from summary results
            paper_ids = list(set(result.paper_id for result in summary_results))
            print(f"✅ Found {len(paper_ids)} relevant papers from summary search")

            # Stage 2: Search content index within identified papers for specific details
            print(f"🔍 Stage 2: Searching detailed content within {len(paper_ids)} papers...")
            detail_results = search_content_index_filtered(
                query,
                paper_ids=paper_ids,
                k=num_detail_chunks,
                file_locations=self.workflow.file_locations,
                similarity_cutoff=0.5
            )

            if not detail_results:
                # Fall back to summary results if no detail chunks found
                print("⚠️  No detailed chunks found, using summary-level information...")
                detail_results = summary_results[:num_detail_chunks]

            print(f"✅ Found {len(detail_results)} detailed chunks")

            # Prepare context for synthesis
            # Group chunks by paper for better organization
            papers_context = {}
            for result in detail_results:
                if result.paper_id not in papers_context:
                    papers_context[result.paper_id] = {
                        'title': result.paper_title,
                        'chunks': []
                    }
                papers_context[result.paper_id]['chunks'].append({
                    'text': result.chunk,
                    'page': result.page
                })

            # Format context for the synthesis prompt
            context_text = ""
            for paper_id, paper_data in papers_context.items():
                context_text += f"\n### Paper: {paper_data['title']} (ArXiv ID: {paper_id})\n\n"
                for i, chunk in enumerate(paper_data['chunks'], 1):
                    context_text += f"**Excerpt {i}** (Page {chunk['page']}):\n{chunk['text']}\n\n"

            # Stage 3: Synthesize findings using LLM
            print(f"🤖 Stage 3: Synthesizing research findings...")

            # Load the research synthesis prompt template and substitute variables
            from .prompt import subst_prompt

            synthesis_prompt = subst_prompt(
                "research_synthesis_v1",
                query=query,
                context=context_text
            )

            # Generate synthesis
            synthesis_response = await self.workflow.llm.acomplete(synthesis_prompt)
            synthesis_text = synthesis_response.text.strip()

            print(f"✅ Research synthesis generated")

            # Load full paper metadata for the papers used
            papers = get_papers_by_ids(list(papers_context.keys()), self.workflow.file_locations)

            # Format the final research result
            final_content = format_research_result(query, synthesis_text, papers)

            # Add detailed references section with page numbers
            final_content += "\n\n## Detailed References\n\n"
            for paper_id, paper_data in papers_context.items():
                final_content += f"### {paper_data['title']}\n"
                final_content += f"- **ArXiv ID**: {paper_id}\n"

                # List all referenced pages
                pages = sorted(set(chunk['page'] for chunk in paper_data['chunks']))
                if len(pages) == 1:
                    final_content += f"- **Referenced Page**: {pages[0]}\n"
                else:
                    final_content += f"- **Referenced Pages**: {', '.join(map(str, pages))}\n"

                # Add file paths
                pdf_path = f"{self.workflow.file_locations.pdfs_dir}/{paper_id}.pdf"
                summary_path = f"{self.workflow.file_locations.summaries_dir}/{paper_id}.md"
                final_content += f"- **PDF**: `{pdf_path}`\n"
                final_content += f"- **Summary**: `{summary_path}`\n\n"

            # Add research statistics
            final_content += f"---\n\n"
            final_content += f"*Research details: Analyzed {len(papers)} papers, "
            final_content += f"synthesized {len(detail_results)} detailed excerpts*\n"

            print(f"✅ Research query completed successfully")

            return QueryResult(
                success=True,
                papers=papers,
                paper_ids=[paper.paper_id for paper in papers],
                message="Research query completed successfully",
                content=final_content
            )

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Research query failed: {str(e)}\n{error_details}")

            error_message = f"""❌ **Research query failed**

**Error:** {str(e)}

**Possible reasons:**
- Index may not be initialized
- Papers may not be indexed yet
- Issue with LLM synthesis

**Suggestions:**
- Use `validate-store` to check index status
- Use `rebuild-index` if index is corrupted
- Try `sem-search` instead for simpler queries"""

            return QueryResult(
                success=False,
                papers=[],
                paper_ids=[],
                message=f"Research query failed: {str(e)}",
                content=error_message
            )

    async def continue_workflow(self, user_input: str, current_papers: Optional[List[PaperMetadata]] = None):
        """Continue the workflow based on user input"""
        # This would handle user selections and feedback
        # Implementation depends on how user interaction is managed
        pass