"""Interactive chat interface for the research assistant.

This module provides a terminal-based chat interface using the rich library
for enhanced display and the WorkflowRunner for processing research tasks.
"""

import asyncio
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.columns import Columns
from rich.layout import Layout

from .workflow import WorkflowRunner, ResearchAssistantWorkflow
from .models import get_default_model
from .file_locations import FILE_LOCATIONS
from .project_types import PaperMetadata
from .interface_adapter import TerminalAdapter
from .validate_store import print_store_validation


class ChatInterface:
    """Interactive chat interface for the research assistant.
    
    This class provides a Rich terminal-based interface that integrates with
    the workflow system through the TerminalAdapter. It handles user commands,
    displays formatted output, and manages conversation state while delegating
    business logic to the workflow layer.
    """
    
    def __init__(self):
        self.console = Console()
        self.interface_adapter = TerminalAdapter(self.console)
        self.llm = None
        self.workflow_runner = None
        self.conversation_history = []

        # Initialize state machine
        from .state_machine import StateMachine
        self.state_machine = StateMachine()

        # For backward compatibility during transition
        self.current_papers = []
        
    def initialize(self):
        """Initialize the LLM and workflow components."""
        try:
            self.console.print("🚀 [bold blue]Initializing Research Assistant...[/bold blue]")
            
            # Initialize LLM
            with self.console.status("[bold green]Loading language model..."):
                self.llm = get_default_model()
            
            # Initialize workflow runner with terminal adapter
            self.workflow_runner = WorkflowRunner(llm=self.llm, interface=self.interface_adapter, file_locations=FILE_LOCATIONS)
            
            self.console.print("✅ [bold green]Initialization complete![/bold green]")
            return True
            
        except Exception as e:
            self.console.print(f"❌ [bold red]Initialization failed:[/bold red] {str(e)}")
            self.console.print("\n[yellow]Please ensure you have:[/yellow]")
            self.console.print("• Valid OPENAI_API_KEY environment variable")
            self.console.print("• DOC_HOME environment variable set")
            self.console.print("• Internet connection for ArXiv access")
            return False
    
    def show_welcome(self):
        """Display welcome message and instructions."""
        welcome_text = """
# 🔬 Research Assistant Chat

Welcome to your interactive research assistant! I can help you:

* **Find** papers on ArXiv to download
* **Download** papers to your local library
* **Index** papers for semantic search
* **Search** your indexed papers semantically
* **List** all downloaded papers
* **Summarize** papers with AI-powered analysis
* **Refine** summaries based on your feedback

## Commands:
* `find <query>` - Find papers on ArXiv to download
* `sem-search <query>` - Search your indexed papers semantically
* `list` - Show all downloaded papers (with pagination)
* `summarize-all` - Generate summaries for all papers without them
* `rebuild-index` - Rebuild content and summary indexes from all files
* `reindex-paper <paper_id>` - Reindex a specific paper through all processing steps
* `validate-store` - Show status of all papers in the store
* `help` - Show this help message
* `status` - Show current status
* `history` - Show conversation history
* `clear` - Clear conversation history
* `quit` or `exit` - Exit the chat

## Getting Started:
* Find ArXiv papers: `find machine learning transformers`
* Search indexed papers: `sem-search agent safety`
        """
        
        self.console.print(Panel(
            Markdown(welcome_text),
            title="🎯 Research Assistant",
            title_align="left",
            border_style="blue"
        ))
    
    def show_help(self):
        """Display help information."""
        help_table = Table(title="Available Commands")
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        help_table.add_column("Example", style="green")
        help_table.add_column("States", style="yellow", no_wrap=True)

        # Core discovery commands
        help_table.add_row(
            "find <query>",
            "Find and download papers from ArXiv",
            "find neural networks",
            "initial"
        )
        help_table.add_row(
            "list",
            "Show all downloaded papers",
            "list",
            "any"
        )

        # Paper processing commands
        help_table.add_row(
            "summarize <id>",
            "Generate summary for a paper",
            "summarize 1",
            "select-*"
        )
        help_table.add_row(
            "summary <id>",
            "View existing paper summary",
            "summary 2503.22738",
            "select-view"
        )
        help_table.add_row(
            "open <id>",
            "View paper content (PDF location)",
            "open 1",
            "select-view"
        )

        # Search and research commands
        help_table.add_row(
            "sem-search <query>",
            "Semantic search across papers",
            "sem-search agent safety",
            "any"
        )
        help_table.add_row(
            "research <query>",
            "Deep research on indexed papers",
            "research transformer models",
            "any"
        )

        # Content management commands
        help_table.add_row(
            "improve <feedback>",
            "Improve current content with feedback",
            "improve add more details",
            "summarized, sem-search, research"
        )
        help_table.add_row(
            "notes",
            "Edit personal notes for selected paper",
            "notes",
            "summarized"
        )
        help_table.add_row(
            "save",
            "Save current content to file",
            "save",
            "summarized, sem-search, research"
        )

        # System commands
        help_table.add_row(
            "rebuild-index",
            "Rebuild all indexes from files",
            "rebuild-index",
            "any"
        )
        help_table.add_row(
            "reindex-paper <id>",
            "Reindex a specific paper through all steps",
            "reindex-paper 2503.22738",
            "any"
        )
        help_table.add_row(
            "summarize-all",
            "Generate summaries for all papers without them",
            "summarize-all",
            "any"
        )
        help_table.add_row(
            "validate-store",
            "Show status of all papers in the store",
            "validate-store",
            "any"
        )
        help_table.add_row(
            "status",
            "Show current workflow status",
            "status",
            "any"
        )
        help_table.add_row(
            "history",
            "Show conversation history",
            "history",
            "any"
        )
        help_table.add_row(
            "clear",
            "Clear history and reset state",
            "clear",
            "any"
        )
        help_table.add_row(
            "help",
            "Show this help message",
            "help",
            "any"
        )
        help_table.add_row(
            "quit/exit",
            "Exit the chat",
            "quit",
            "any"
        )

        self.console.print(help_table)

        # Show current state and valid commands
        current_state = self.state_machine.current_state.value
        valid_commands = [cmd.split()[0] for cmd in self.state_machine.get_valid_commands()[:8]]

        state_info = f"""
**Current State:** {current_state}
**Currently Valid Commands:** {', '.join(valid_commands)}{'...' if len(self.state_machine.get_valid_commands()) > 8 else ''}

Use 'status' for detailed state information.
        """

        self.console.print(Panel(
            state_info.strip(),
            title="🎯 Current Context",
            border_style="blue"
        ))
    
    def show_status(self):
        """Display current status."""
        # Get state machine info
        state_name = self.state_machine.current_state.value
        state_desc = self.state_machine.get_state_description()
        valid_commands = self.state_machine.get_valid_commands()

        # Get state variables info
        sv = self.state_machine.state_vars
        query_info = f"{len(sv.last_query_set)} papers" if sv.last_query_set else "None"
        selected_info = sv.selected_paper.title if sv.selected_paper else "None"
        draft_info = "Yes" if sv.draft else "None"

        status_panel = Panel(
            f"""
**Current State:** {state_name}
**State Description:** {state_desc}
**Query Results:** {query_info}
**Selected Paper:** {selected_info}
**Draft Content:** {draft_info}
**Conversation Messages:** {len(self.conversation_history)}

**Valid Commands:** {', '.join(valid_commands[:5])}{'...' if len(valid_commands) > 5 else ''}

**File Locations:**
  • PDFs: {FILE_LOCATIONS.pdfs_dir}
  • Summaries: {FILE_LOCATIONS.summaries_dir}
  • Index: {FILE_LOCATIONS.index_dir}
  • Notes: {FILE_LOCATIONS.notes_dir}
  • Results: {FILE_LOCATIONS.results_dir}
            """,
            title="📊 Current Status",
            border_style="yellow"
        )
        self.console.print(status_panel)
    
    def show_history(self):
        """Display conversation history."""
        if not self.conversation_history:
            self.console.print("📝 [yellow]No conversation history yet[/yellow]")
            return
        
        self.console.print("\n📝 [bold]Conversation History:[/bold]")
        for i, msg in enumerate(self.conversation_history[-10:], 1):  # Show last 10 messages
            timestamp = msg.get('timestamp', 'Unknown')
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            role_style = "blue" if role == "user" else "green"
            self.console.print(f"[{role_style}]{i}. [{role.upper()}][/{role_style}] ({timestamp})")
            self.console.print(f"   {content[:100]}{'...' if len(content) > 100 else ''}\n")
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        self.console.print("🗑️  [green]Conversation history cleared[/green]")
    
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    
    def display_papers(self, papers: List[PaperMetadata]):
        """Display paper search results using the interface adapter."""
        self.interface_adapter.display_papers(papers)
        self.current_papers = papers
    
    def render_markdown_response(self, content: str):
        """Render markdown content using the interface adapter."""
        self.interface_adapter.render_content(content, "markdown")
    
    async def process_search_command(self, query: str):
        """Process a search command using the workflow system."""
        self.current_state = "searching"

        try:
            # Use the workflow system for paper search
            result = await self.workflow_runner.start_add_paper_workflow(query)

            # Handle the new QueryResult format
            if hasattr(result, 'success'):
                if result.success and result.papers:
                    # Store papers for selection and update state machine
                    self.current_papers = result.papers
                    self.state_machine.transition_after_find(True)
                    self.state_machine.state_vars.set_query_results(result.paper_ids)
                    self.current_state = "paper_selection"
                else:
                    # Handle failure case
                    self.interface_adapter.show_error(result.message)
                    self.state_machine.transition_to_initial("No papers found")
                    self.current_state = "ready"
            else:
                # Backward compatibility for old format
                if hasattr(result, 'papers') and hasattr(result, 'message'):
                    self.current_papers = result.papers
                    self.current_state = "paper_selection"
                elif result and not result.startswith("❌") and not result.startswith("No papers"):
                    self.current_state = "paper_selection"
                else:
                    self.current_state = "ready"

        except Exception as e:
            self.interface_adapter.show_error(f"Search failed: {str(e)}")
            self.state_machine.transition_to_initial(f"Error: {str(e)}")
            self.current_state = "ready"
    
    
    async def process_improve_command(self, feedback: str):
        """Process a summary improvement command using the workflow system."""
        if self.current_state != "summary_ready":
            self.interface_adapter.show_error("No summary to improve. Process a paper first.")
            return
        
        try:
            result = await self.workflow_runner.improve_summary(
                self.current_paper,
                self.current_summary,
                self.current_paper_text,
                feedback
            )
            
            # Check if we got an improved summary back
            if hasattr(result, 'summary'):
                self.current_summary = result.summary
                self.interface_adapter.show_info("You can continue to improve or type 'save' to save.")
            
        except Exception as e:
            self.interface_adapter.show_error(f"Improvement failed: {str(e)}")
    
    async def process_save_command(self):
        """Process a save summary command using the workflow system."""
        if self.current_state != "summary_ready":
            self.interface_adapter.show_error("No summary to save. Process a paper first.")
            return
        
        try:
            result = await self.workflow_runner.save_summary(
                self.current_paper,
                self.current_summary,
                self.current_paper_text
            )
            
            # Reset state after successful save
            self.current_state = "ready"
            
        except Exception as e:
            self.interface_adapter.show_error(f"Save failed: {str(e)}")
    
    async def process_semantic_search_command(self, query: str):
        """Process a semantic search command using the workflow system."""
        self.current_state = "semantic_searching"

        try:
            result = await self.workflow_runner.start_semantic_search_workflow(query)

            # Handle the new QueryResult format
            if hasattr(result, 'success'):
                if result.success and result.content:
                    # Display the result to the user
                    self.render_markdown_response(result.content)
                    # Add to history
                    self.add_to_history("assistant", result.content)

                    # Update state machine
                    self.state_machine.transition_after_sem_search(
                        found_results=True,
                        search_results=result.content,
                        paper_ids=result.paper_ids,
                        original_query=query
                    )
                else:
                    # Handle failure case - show what we got for debugging
                    error_msg = f"Search failed - success: {result.success}, content length: {len(result.content) if result.content else 0}, message: {result.message}"
                    self.interface_adapter.show_error(error_msg)
                    self.state_machine.transition_to_initial("No search results")
            else:
                # Backward compatibility for old string format
                if result and not result.startswith("❌"):
                    self.render_markdown_response(result)
                    self.add_to_history("assistant", result)

            # Update current_state for backward compatibility
            self.current_state = "ready"

        except Exception as e:
            self.interface_adapter.show_error(f"Semantic search failed: {str(e)}")
            self.state_machine.transition_to_initial(f"Error: {str(e)}")
            self.current_state = "ready"
    
    async def process_list_command(self):
        """Process a list command to show all downloaded papers with pagination."""
        import math
        from rich.table import Table
        from rich.prompt import Prompt

        try:
            # Use the workflow to get the list of papers
            result = await self.workflow_runner.get_list_of_papers()

            if not (hasattr(result, 'success') and result.success):
                # Handle failure
                error_msg = result.message if hasattr(result, 'message') else "Failed to list papers"
                self.interface_adapter.show_error(error_msg)
                return

            # If no papers, show the simple message without pagination
            if not result.papers:
                self.render_markdown_response(result.content)
                self.add_to_history("assistant", result.content)
                self.state_machine.transition_after_list()
                self.state_machine.state_vars.set_query_results(result.paper_ids)
                return

            # Display papers with pagination
            self.console.print("📋 [bold blue]Downloaded Papers[/bold blue]\n")

            papers = result.papers
            papers_per_page = 10  # Show 10 papers per page
            total_papers = len(papers)
            total_pages = math.ceil(total_papers / papers_per_page) if total_papers > 0 else 1

            current_page = 1

            while True:
                # Calculate start and end indices for current page
                start_idx = (current_page - 1) * papers_per_page
                end_idx = min(start_idx + papers_per_page, total_papers)
                current_papers = papers[start_idx:end_idx]

                # Create table for current page
                table = Table(title=f"Page {current_page}/{total_pages}")
                table.add_column("#", style="cyan", no_wrap=True, width=4)
                table.add_column("Paper ID", style="yellow", no_wrap=True, width=14)
                table.add_column("Title", style="white", width=55)
                table.add_column("Authors", style="green", width=25)
                table.add_column("Published", style="blue", no_wrap=True, width=10)

                # Add papers to table
                for i, paper in enumerate(current_papers, start=start_idx + 1):
                    # Truncate long titles and author lists for display
                    title = paper.title if len(paper.title) <= 57 else paper.title[:54] + "..."
                    authors = ", ".join(paper.authors[:2])
                    if len(paper.authors) > 2:
                        authors += f" +{len(paper.authors) - 2} more"
                    if len(authors) > 27:
                        authors = authors[:24] + "..."

                    published_date = paper.published.strftime('%Y-%m-%d')

                    table.add_row(
                        str(i),
                        paper.paper_id,
                        title,
                        authors,
                        published_date
                    )

                # Display the table
                self.console.print(table)

                # Show pagination info and controls
                if total_pages > 1:
                    pagination_text = f"\n📄 Page {current_page} of {total_pages} • Total: {total_papers} papers"
                    self.console.print(pagination_text)

                    if current_page < total_pages:
                        self.console.print("[dim]Press Enter for next page, or type any other key to exit[/dim]")
                        user_input = Prompt.ask("", console=self.console, default="")
                        if user_input != "":
                            break
                        current_page += 1
                    else:
                        self.console.print("[dim]End of list[/dim]")
                        break
                else:
                    # Single page, just show total
                    total_text = f"\n📊 Total: {total_papers} paper{'s' if total_papers != 1 else ''}"
                    self.console.print(total_text)
                    break

            # Show summary information and next steps
            self.console.print(f"\n💾 **Storage Locations:**")
            self.console.print(f"• PDFs: `{self.workflow_runner.workflow.file_locations.pdfs_dir}`")
            self.console.print(f"• Summaries: `{self.workflow_runner.workflow.file_locations.summaries_dir}`")
            self.console.print(f"• Index: `{self.workflow_runner.workflow.file_locations.index_dir}`")

            self.console.print(f"\n💡 **Next steps:**")
            self.console.print("• Use `summary <number|id>` to view existing summaries")
            self.console.print("• Use `open <number|id>` to view paper content")
            self.console.print("• Use `sem-search <query>` to search across papers")

            # Update state machine
            self.state_machine.transition_after_list()
            self.state_machine.state_vars.set_query_results(result.paper_ids)

            # Add simplified content to history (for later reference)
            history_content = f"Listed {len(papers)} downloaded papers with pagination. Available paper IDs: {', '.join(result.paper_ids[:5])}{'...' if len(result.paper_ids) > 5 else ''}"
            self.add_to_history("assistant", history_content)

        except Exception as e:
            self.interface_adapter.show_error(f"List command failed: {str(e)}")

    async def process_rebuild_index_command(self):
        """Process a rebuild-index command to rebuild all indexes."""
        from .vector_store import rebuild_index

        try:
            self.console.print("🔄 [bold blue]Rebuilding content and summary indexes...[/bold blue]")
            self.console.print("⚠️ [yellow]This will clear and rebuild all indexes from PDFs, summaries, and notes.[/yellow]")

            # Ask for confirmation
            from rich.prompt import Confirm
            if not Confirm.ask("Are you sure you want to continue?", console=self.console):
                self.console.print("❌ [yellow]Rebuild canceled by user.[/yellow]")
                return

            # Run the rebuild with status updates
            with self.console.status("[bold green]Rebuilding indexes..."):
                rebuild_index(FILE_LOCATIONS)

            self.console.print("✅ [bold green]Index rebuild completed successfully![/bold green]")

        except Exception as e:
            self.interface_adapter.show_error(f"Index rebuild failed: {str(e)}")

    async def process_summarize_all_command(self):
        """Process a summarize-all command to generate summaries for all papers without them."""
        from .arxiv_downloader import get_downloaded_paper_ids, get_paper_metadata
        from .paper_manager import get_paper_summary_path
        from .vector_store import index_file
        from .summarizer import summarize_paper, save_summary
        from .vector_store import index_summary

        try:
            # Reset state machine to initial state
            self.state_machine.reset()

            # Get all downloaded papers
            self.console.print("🔍 [bold blue]Finding downloaded papers...[/bold blue]")
            paper_ids = get_downloaded_paper_ids(FILE_LOCATIONS)

            if not paper_ids:
                self.interface_adapter.show_info("No downloaded papers found. Download some papers first.")
                return

            # Filter to papers without summaries
            papers_without_summaries = []
            papers_with_summaries = 0

            for paper_id in paper_ids:
                if not get_paper_summary_path(paper_id, FILE_LOCATIONS):
                    try:
                        paper_metadata = get_paper_metadata(paper_id)
                        if paper_metadata:
                            papers_without_summaries.append(paper_metadata)
                    except Exception:
                        self.console.print(f"⚠️ [yellow]Could not load metadata for paper {paper_id}, skipping.[/yellow]")
                        continue
                else:
                    papers_with_summaries += 1

            total_papers = len(papers_without_summaries) + papers_with_summaries
            self.console.print(f"📊 [bold green]Found {total_papers} downloaded papers:[/bold green]")
            self.console.print(f"   • {papers_with_summaries} papers already have summaries")
            self.console.print(f"   • {len(papers_without_summaries)} papers need summaries")

            if not papers_without_summaries:
                self.interface_adapter.show_info("✅ All downloaded papers already have summaries!")
                return

            # Process each paper without a summary
            self.console.print(f"\n🚀 [bold blue]Starting summarization of {len(papers_without_summaries)} papers...[/bold blue]")

            successful_summaries = 0
            failed_summaries = 0

            for i, paper in enumerate(papers_without_summaries, 1):
                self.console.print(f"\n📝 [bold cyan]Processing paper {i}/{len(papers_without_summaries)}: {paper.paper_id}[/bold cyan]")
                self.console.print(f"    Title: {paper.title}")

                try:
                    # Step 1: Index the paper (this extracts and caches text)
                    with self.console.status(f"[bold green]Indexing paper {i}/{len(papers_without_summaries)}..."):
                        paper_text = index_file(paper, FILE_LOCATIONS)

                    self.console.print(f"    ✅ Indexed successfully ({len(paper_text):,} characters)")

                    # Step 2: Generate summary
                    with self.console.status(f"[bold green]Generating summary {i}/{len(papers_without_summaries)}..."):
                        summary = summarize_paper(paper_text, paper)

                    self.console.print(f"    ✅ Summary generated")

                    # Step 3: Save summary
                    summary_path = save_summary(summary, paper.paper_id)
                    self.console.print(f"    ✅ Summary saved to: {summary_path}")

                    # Step 4: Index the summary
                    try:
                        index_summary(paper, FILE_LOCATIONS)
                        self.console.print(f"    ✅ Summary indexed for search")
                    except Exception as e:
                        self.console.print(f"    ⚠️ [yellow]Summary indexing failed: {str(e)}[/yellow]")

                    successful_summaries += 1

                except Exception as e:
                    failed_summaries += 1
                    self.console.print(f"    ❌ [red]Failed to process paper: {str(e)}[/red]")
                    continue

            # Show final results
            self.console.print(f"\n🎉 [bold green]Summarization complete![/bold green]")
            self.console.print(f"   • ✅ Successfully processed: {successful_summaries} papers")
            if failed_summaries > 0:
                self.console.print(f"   • ❌ Failed: {failed_summaries} papers")

            self.console.print(f"   • 📚 Total papers with summaries: {papers_with_summaries + successful_summaries}")

            # Add to history
            summary_msg = f"Processed {successful_summaries} papers successfully"
            if failed_summaries > 0:
                summary_msg += f", {failed_summaries} failed"
            self.add_to_history("assistant", f"summarize-all completed: {summary_msg}")

        except Exception as e:
            self.interface_adapter.show_error(f"Summarize-all failed: {str(e)}")

    async def process_validate_store_command(self):
        """Process a validate-store command to show the status of all papers in the store."""
        try:
            self.console.print("🔍 [bold blue]Validating store status...[/bold blue]")

            # Call the validation function
            print_store_validation(self.console, FILE_LOCATIONS)

            # Add to history
            self.add_to_history("assistant", "validate-store completed: Displayed store validation results")

        except Exception as e:
            self.interface_adapter.show_error(f"Store validation failed: {str(e)}")

    async def process_reindex_paper_command(self, paper_id: str):
        """Process a reindex-paper command to reindex a specific paper."""
        from .paper_manager import parse_paper_argument_enhanced
        from .reindex_paper import reindex_paper, ReindexError

        try:
            # Parse paper argument using enhanced function
            paper, error_msg, was_resolved_by_integer = parse_paper_argument_enhanced(
                "reindex-paper",
                paper_id,
                self.state_machine.state_vars.last_query_set,
                FILE_LOCATIONS
            )
            if not paper:
                self.interface_adapter.show_error(error_msg)
                return

            self.console.print(f"🔄 [bold blue]Reindexing paper {paper.paper_id}...[/bold blue]")

            # Run the reindex operation with status updates
            with self.console.status(f"[bold green]Processing paper {paper.paper_id}..."):
                result_message = reindex_paper(paper.paper_id, FILE_LOCATIONS)

            # Display the results
            self.console.print(f"✅ [bold green]{result_message}[/bold green]")

            # Add to history
            self.add_to_history("assistant", f"reindex-paper {paper.paper_id} completed: {result_message}")

            # No state change for maintenance commands per design

        except ReindexError as e:
            self.interface_adapter.show_error(f"Reindex failed: {str(e)}")
        except Exception as e:
            self.interface_adapter.show_error(f"Reindex paper failed: {str(e)}")

    async def process_summarize_command(self, reference: str):
        """Process a summarize command for the new state machine workflow."""
        from .paper_manager import parse_paper_argument_enhanced

        try:
            # Parse paper argument using enhanced function
            paper, error_msg, was_resolved_by_integer = parse_paper_argument_enhanced(
                "summarize",
                reference,
                self.state_machine.state_vars.last_query_set,
                FILE_LOCATIONS
            )
            if not paper:
                self.interface_adapter.show_error(error_msg)
                return

            # Use the workflow system to process the paper
            result = await self.workflow_runner.process_paper_selection(paper)

            # Handle the result and update state machine
            if hasattr(result, 'paper') and hasattr(result, 'summary'):
                # Store the summary in state machine with new conditional logic
                self.state_machine.transition_after_summarize(result.paper, result.summary)

                # Display the summary
                self.render_markdown_response(result.summary)
                self.add_to_history("assistant", result.summary)

                self.interface_adapter.show_info("✨ You can now:")
                self.interface_adapter.show_info("• Use 'improve <feedback>' to refine the summary")
                self.interface_adapter.show_info("• Use 'notes' to edit your personal notes")
            else:
                self.interface_adapter.show_error("Failed to generate summary")

        except Exception as e:
            self.interface_adapter.show_error(f"Summarize failed: {str(e)}")

    async def process_summary_command(self, reference: str):
        """Process a summary command to view an existing paper summary."""
        from .paper_manager import parse_paper_argument_enhanced, load_paper_summary
        from rich.prompt import Confirm

        try:
            # Parse paper argument using enhanced function
            paper, error_msg, was_resolved_by_integer = parse_paper_argument_enhanced(
                "summary",
                reference,
                self.state_machine.state_vars.last_query_set,
                FILE_LOCATIONS
            )
            if not paper:
                self.interface_adapter.show_error(error_msg)
                return

            # Load existing summary
            success, content = load_paper_summary(paper.paper_id, FILE_LOCATIONS)
            if not success:
                # Summary is missing - offer to create one
                self.console.print(f"📄 [yellow]Summary not found for paper:[/yellow] {paper.title}")
                self.console.print(f"📋 [dim]Paper ID:[/dim] {paper.paper_id}")
                self.console.print()

                # Ask if user wants to create a summary
                create_summary = Confirm.ask(
                    "Would you like me to create a summary for this paper?",
                    console=self.console,
                    default=True
                )

                if create_summary:
                    self.console.print("🤖 [bold blue]Creating summary...[/bold blue]")
                    # Call the summarize command implementation
                    await self._create_summary_for_paper(paper)
                else:
                    self.interface_adapter.show_info("No summary created. You can create one later with 'summarize <number|id>'.")
                return

            # Update state machine and display summary
            self.state_machine.transition_after_summary_view(paper, content)
            self.render_markdown_response(content)
            self.add_to_history("assistant", content)

            self.interface_adapter.show_info("✨ You can now:")
            self.interface_adapter.show_info("• Use 'improve <feedback>' to refine the summary")
            self.interface_adapter.show_info("• Use 'notes' to edit your personal notes")
            self.interface_adapter.show_info("• Use 'open <number|id>' to view the full paper")

        except Exception as e:
            self.interface_adapter.show_error(f"Summary view failed: {str(e)}")

    async def _create_summary_for_paper(self, paper):
        """Helper method to create a summary for a paper (used by summary command when missing)."""
        try:
            # Use the workflow system to process the paper
            result = await self.workflow_runner.process_paper_selection(paper)

            # Handle the result and update state machine
            if hasattr(result, 'paper') and hasattr(result, 'summary'):
                # Store the summary in state machine
                self.state_machine.transition_after_summarize(result.paper, result.summary)

                # Display the summary
                self.render_markdown_response(result.summary)
                self.add_to_history("assistant", result.summary)

                self.interface_adapter.show_info("✅ [bold green]Summary created successfully![/bold green]")
                self.interface_adapter.show_info("✨ You can now:")
                self.interface_adapter.show_info("• Use 'improve <feedback>' to refine the summary")
                self.interface_adapter.show_info("• Use 'notes' to edit your personal notes")
            else:
                self.interface_adapter.show_error("Failed to generate summary")

        except Exception as e:
            self.interface_adapter.show_error(f"Summary creation failed: {str(e)}")

    async def process_open_command(self, reference: str):
        """Process an open command to view paper content."""
        from .paper_manager import parse_paper_argument_enhanced
        from .result_storage import open_paper_content
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.prompt import Prompt
        import math

        try:
            # Parse paper argument using enhanced function
            paper, error_msg, was_resolved_by_integer = parse_paper_argument_enhanced(
                "open",
                reference,
                self.state_machine.state_vars.last_query_set,
                FILE_LOCATIONS
            )
            if not paper:
                self.interface_adapter.show_error(error_msg)
                return

            # Open paper content - now returns (success, content, action_type)
            success, content, action_type = open_paper_content(paper.paper_id, FILE_LOCATIONS)

            if not success:
                self.interface_adapter.show_error(content)  # content contains error message
                return

            # Handle different action types
            if action_type == "viewer":
                # PDF viewer was launched - just display success message
                self.render_markdown_response(content)
                self.add_to_history("assistant", content)

            elif action_type == "markdown":
                # PDF_VIEWER not set - display markdown with pagination
                self.console.print("⚠️ [yellow]WARNING: PDF_VIEWER environment variable is not set, Rendering in terminal[/yellow]\n")

                # Split content into lines for pagination
                lines = content.split('\n')
                # Use 80% of terminal height for pagination
                terminal_height = self.console.height
                lines_per_page = int(terminal_height * 0.8)
                total_lines = len(lines)
                total_pages = math.ceil(total_lines / lines_per_page) if total_lines > 0 else 1

                current_page = 1

                while True:
                    # Calculate start and end indices for current page
                    start_idx = (current_page - 1) * lines_per_page
                    end_idx = min(start_idx + lines_per_page, total_lines)
                    page_lines = lines[start_idx:end_idx]
                    page_content = '\n'.join(page_lines)

                    # Display the page in a panel with markdown rendering
                    panel = Panel(
                        Markdown(page_content),
                        title=f"📝 {paper.title if hasattr(paper, 'title') else f'Paper {paper.paper_id}'}",
                        border_style="green"
                    )
                    self.console.print(panel)

                    # Show pagination info
                    pagination_text = f"\n📄 Page {current_page} of {total_pages}"
                    self.console.print(pagination_text)

                    if current_page < total_pages:
                        self.console.print("[dim]Press Enter for next page, or type any other key to exit[/dim]")
                        user_input = Prompt.ask("", console=self.console, default="")
                        if user_input != "":
                            break
                        current_page += 1
                    else:
                        break

                # Add simplified content to history
                history_content = f"Displayed paper content for {paper.paper_id} ({total_pages} pages)"
                self.add_to_history("assistant", history_content)

            # Update state machine according to design
            self.state_machine.transition_after_open(paper)

        except Exception as e:
            self.interface_adapter.show_error(f"Open failed: {str(e)}")

    async def process_notes_command(self):
        """Process a notes command to edit paper notes."""
        from .result_storage import edit_notes_for_paper

        try:
            # Check if we have a selected paper
            if not self.state_machine.state_vars.selected_paper:
                self.interface_adapter.show_error("No paper selected. Select a paper first with 'summarize' or 'summary'.")
                return

            # Get paper ID
            paper_id = self.state_machine.state_vars.selected_paper.paper_id

            # Handle notes editing
            success, message = edit_notes_for_paper(paper_id, FILE_LOCATIONS)
            if success:
                self.render_markdown_response(message)
            else:
                self.interface_adapter.show_error(message)

            # Stay in current state (notes doesn't change state)
            self.state_machine.stay_in_current_state()

        except Exception as e:
            self.interface_adapter.show_error(f"Notes failed: {str(e)}")

    async def process_save_workflow_command(self):
        """Process a save command for workflow results (semantic search/research)."""
        from .result_storage import save_search_results

        try:
            # Check if we have draft content to save
            if not self.state_machine.state_vars.draft:
                self.interface_adapter.show_error("No content to save. Run a semantic search or research query first.")
                return

            # Check if we have the original query
            if not self.state_machine.state_vars.original_query:
                self.interface_adapter.show_error("No original query found. Unable to generate proper title.")
                return

            # Determine content type based on current state
            content_type = "research" if self.state_machine.current_state.value == "research" else "search"

            # Save the content using the original query for title generation
            file_path, title = await save_search_results(
                content=self.state_machine.state_vars.draft,
                query=self.state_machine.state_vars.original_query,
                file_locations=FILE_LOCATIONS,
                content_type=content_type
            )

            # Show success message
            success_msg = f"""✅ **{content_type.title()} results saved successfully!**

**File:** {file_path}
**Title:** {title}

The content has been saved to your results directory and can be referenced later."""

            self.render_markdown_response(success_msg)
            self.add_to_history("assistant", success_msg)

            # Stay in current state (save doesn't change state)
            self.state_machine.stay_in_current_state()

        except Exception as e:
            self.interface_adapter.show_error(f"Save failed: {str(e)}")

    async def process_improve_workflow_command(self, feedback: str):
        """Process an improve command for workflow content."""
        try:
            # Check current state and available content
            if self.state_machine.current_state.value == "summarized":
                # Improve paper summary
                if not self.state_machine.state_vars.selected_paper or not self.state_machine.state_vars.draft:
                    self.interface_adapter.show_error("No summary to improve. Summarize a paper first.")
                    return

                # Use workflow to improve summary
                result = await self.workflow_runner.improve_summary(
                    self.state_machine.state_vars.selected_paper,
                    self.state_machine.state_vars.draft,
                    "",  # paper_text not needed for improvement
                    feedback
                )

                if hasattr(result, 'summary'):
                    # Update the draft content
                    self.state_machine.state_vars.set_draft(result.summary)
                    self.render_markdown_response(result.summary)
                    self.add_to_history("assistant", result.summary)

                    self.interface_adapter.show_info("✨ Summary improved! You can continue to improve or save.")

            elif self.state_machine.current_state.value in ["sem-search", "research"]:
                # Improve search/research results
                if not self.state_machine.state_vars.draft:
                    self.interface_adapter.show_error("No content to improve. Run a search or research query first.")
                    return

                # Use workflow to improve content
                result = await self.workflow_runner.improve_content(self.state_machine.state_vars.draft, feedback)

                if hasattr(result, 'content'):
                    # Update the draft content
                    self.state_machine.state_vars.set_draft(result.content)
                    self.render_markdown_response(result.content)
                    self.add_to_history("assistant", result.content)

                    self.interface_adapter.show_info("✨ Content improved! You can continue to improve or save.")
            else:
                self.interface_adapter.show_error("Nothing to improve in current state. Summarize a paper or run a search first.")

            # Stay in current state
            self.state_machine.stay_in_current_state()

        except Exception as e:
            self.interface_adapter.show_error(f"Improve failed: {str(e)}")

    async def process_research_command(self, query: str):
        """Process a research command using the workflow system."""
        try:
            result = await self.workflow_runner.start_semantic_search_workflow(query)

            # Handle the new QueryResult format
            if hasattr(result, 'success'):
                if result.success and result.content:
                    # Display the result to the user
                    self.render_markdown_response(result.content)
                    # Add to history
                    self.add_to_history("assistant", result.content)

                    # Update state machine - transition to research state
                    self.state_machine.transition_after_research(
                        found_results=True,
                        research_results=result.content,
                        paper_ids=result.paper_ids,
                        original_query=query
                    )
                else:
                    # Handle failure case
                    self.interface_adapter.show_error(result.message)
                    self.state_machine.transition_to_initial("No research results")
            else:
                # Backward compatibility for old string format
                if result and not result.startswith("❌"):
                    self.render_markdown_response(result)
                    self.add_to_history("assistant", result)

        except Exception as e:
            self.interface_adapter.show_error(f"Research failed: {str(e)}")
            self.state_machine.transition_to_initial(f"Error: {str(e)}")

    async def run_chat_loop(self):
        """Main chat loop."""
        self.show_welcome()
        
        if not self.initialize():
            return
        
        self.console.print("\n🎯 [bold green]Ready! Type 'help' for commands or start with 'find <your query>'[/bold green]\n")
        
        while True:
            try:
                # Get user input
                user_input = Prompt.ask(
                    "[bold blue]You[/bold blue]",
                    console=self.console
                ).strip()
                
                if not user_input:
                    continue
                
                # Add to history
                self.add_to_history("user", user_input)
                
                # Handle quit commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.console.print("👋 [bold blue]Goodbye! Happy researching![/bold blue]")
                    break

                # Extract command name for validation
                cmd_parts = user_input.strip().split(None, 1)
                cmd_name = cmd_parts[0].lower() if cmd_parts else ""
                cmd_arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

                # Check if command is valid in current state (skip global commands)
                global_commands = ["help", "status", "history", "clear", "quit", "exit", "rebuild-index", "summarize-all", "validate-store"]

                # Get all valid command names (including global ones)
                all_valid_commands = set(global_commands)
                state_commands = self.state_machine.get_valid_commands()
                for cmd in state_commands:
                    all_valid_commands.add(cmd.split()[0])

                # Check if the command is recognized at all
                if cmd_name not in all_valid_commands:
                    # Check for common typos
                    if cmd_name == "valiate-store":
                        self.interface_adapter.show_error(
                            "Did you mean 'validate-store'? (Note the 'd' in 'validate')"
                        )
                    else:
                        self.interface_adapter.show_error(
                            f"Unknown command '{cmd_name}'. Type 'help' to see available commands."
                        )
                    continue

                # Check if command is valid in current state
                if cmd_name not in global_commands and not self.state_machine.is_command_valid(user_input):
                    valid_cmds = [cmd for cmd in self.state_machine.get_valid_commands()
                                 if not cmd.split()[0] in global_commands][:5]
                    self.interface_adapter.show_error(
                        f"Command '{cmd_name}' not valid in current state. "
                        f"Valid commands: {', '.join(valid_cmds)}{'...' if len(valid_cmds) == 5 else ''}"
                    )
                    continue

                # Handle special commands
                if cmd_name == 'help':
                    self.show_help()

                elif cmd_name == 'status':
                    self.show_status()

                elif cmd_name == 'history':
                    self.show_history()

                elif cmd_name == 'clear':
                    self.clear_history()
                    self.state_machine.reset()  # Reset state machine on clear

                elif cmd_name == 'rebuild-index':
                    await self.process_rebuild_index_command()
                elif cmd_name == 'summarize-all':
                    await self.process_summarize_all_command()
                elif cmd_name == 'validate-store':
                    await self.process_validate_store_command()
                elif cmd_name == 'reindex-paper':
                    if cmd_arg:
                        await self.process_reindex_paper_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide a paper ID[/red]")

                # Handle workflow commands
                elif cmd_name == 'find':
                    if cmd_arg:
                        await self.process_search_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide a search query[/red]")

                elif cmd_name == 'summarize':
                    if cmd_arg:
                        await self.process_summarize_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide a paper number or ID[/red]")

                elif cmd_name == 'summary':
                    if cmd_arg:
                        await self.process_summary_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide a paper number or ID[/red]")

                elif cmd_name == 'open':
                    if cmd_arg:
                        await self.process_open_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide a paper number or ID[/red]")

                elif cmd_name == 'notes':
                    await self.process_notes_command()

                elif cmd_name == 'improve':
                    if cmd_arg:
                        await self.process_improve_workflow_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide improvement feedback[/red]")

                elif cmd_name == 'save':
                    # Handle save differently based on current state
                    if self.state_machine.current_state.value == "summarized":
                        # Save paper summary using old method for now
                        await self.process_save_command()
                    else:
                        # Save workflow results (search/research)
                        await self.process_save_workflow_command()

                elif cmd_name in ['sem-search', 'semantic-search']:
                    if cmd_arg:
                        await self.process_semantic_search_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide a search query[/red]")

                elif cmd_name == 'research':
                    if cmd_arg:
                        # Research command uses same implementation as sem-search but may transition to different state
                        await self.process_research_command(cmd_arg)
                    else:
                        self.console.print("❌ [red]Please provide a research query[/red]")

                elif cmd_name == 'list':
                    await self.process_list_command()

                # No legacy commands - all transitioned to state machine

                else:
                    self.interface_adapter.show_info("Unknown command. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                self.console.print("\n👋 [bold blue]Goodbye! Happy researching![/bold blue]")
                break
            except EOFError:
                self.console.print("\n👋 [bold blue]Goodbye! Happy researching![/bold blue]")
                break
            except Exception as e:
                self.interface_adapter.show_error(f"Unexpected error: {str(e)}")


def main():
    """Main entry point for the chat interface."""
    try:
        chat = ChatInterface()
        asyncio.run(chat.run_chat_loop())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()