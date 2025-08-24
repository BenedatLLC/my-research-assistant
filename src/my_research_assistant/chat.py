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
        self.current_papers = []
        self.current_state = "ready"
        
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
        
        help_table.add_row(
            "find <query>", 
            "Find papers on ArXiv to download", 
            "find neural networks"
        )
        help_table.add_row(
            "sem-search <query>", 
            "Search your indexed papers semantically", 
            "sem-search agent safety"
        )
        help_table.add_row(
            "list", 
            "Show all downloaded papers with pagination", 
            "list"
        )
        help_table.add_row(
            "select <number>", 
            "Select a paper from search results", 
            "select 1"
        )
        help_table.add_row(
            "improve <feedback>", 
            "Improve current summary", 
            "improve make it more detailed"
        )
        help_table.add_row(
            "save", 
            "Save the current summary", 
            "save"
        )
        help_table.add_row(
            "status", 
            "Show current workflow status", 
            "status"
        )
        help_table.add_row(
            "history", 
            "Show conversation history", 
            "history"
        )
        help_table.add_row(
            "clear", 
            "Clear conversation history", 
            "clear"
        )
        help_table.add_row(
            "help", 
            "Show this help message", 
            "help"
        )
        help_table.add_row(
            "quit/exit", 
            "Exit the chat", 
            "quit"
        )
        
        self.console.print(help_table)
    
    def show_status(self):
        """Display current status."""
        status_panel = Panel(
            f"""
**Current State:** {self.current_state}
**Papers in Context:** {len(self.current_papers)}
**Conversation Messages:** {len(self.conversation_history)}
**File Locations:** 
  • PDFs: {FILE_LOCATIONS.pdfs_dir}
  • Summaries: {FILE_LOCATIONS.summaries_dir}
  • Index: {FILE_LOCATIONS.index_dir}
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
            
            if result and not result.startswith("❌") and not result.startswith("No papers"):
                self.current_state = "paper_selection"
            else:
                self.current_state = "ready"
            
        except Exception as e:
            self.interface_adapter.show_error(f"Search failed: {str(e)}")
            self.current_state = "ready"
    
    async def process_select_command(self, selection: str):
        """Process a paper selection command using the workflow system."""
        if not self.current_papers:
            self.interface_adapter.show_error("No papers available to select. Search first.")
            return
        
        try:
            paper_num = int(selection) - 1
            if paper_num < 0 or paper_num >= len(self.current_papers):
                self.interface_adapter.show_error(f"Invalid selection. Choose 1-{len(self.current_papers)}")
                return
            
            selected_paper = self.current_papers[paper_num]
            self.interface_adapter.show_success(f"Selected: {selected_paper.title}")
            
            # Use the workflow system for paper processing
            result = await self.workflow_runner.process_paper_selection(selected_paper)
            
            # Check if we got a summary event back for potential improvements
            if hasattr(result, 'paper') and hasattr(result, 'summary') and hasattr(result, 'paper_text'):
                self.current_summary = result.summary
                self.current_paper = result.paper
                self.current_paper_text = result.paper_text
                self.current_state = "summary_ready"
                
                self.interface_adapter.show_info("You can now:")
                self.interface_adapter.show_info("• Type 'improve <feedback>' to refine the summary")
                self.interface_adapter.show_info("• Type 'save' to save the summary")
            else:
                self.current_state = "ready"
            
        except ValueError:
            self.interface_adapter.show_error("Invalid selection. Enter a number.")
        except Exception as e:
            self.interface_adapter.show_error(f"Selection failed: {str(e)}")
    
    
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
            
            if result and not result.startswith("❌"):
                # Add to history
                self.add_to_history("assistant", result)
            
            # Reset state
            self.current_state = "ready"
            
        except Exception as e:
            self.interface_adapter.show_error(f"Semantic search failed: {str(e)}")
            self.current_state = "ready"
    
    async def process_list_command(self):
        """Process a list command to show all downloaded papers."""
        from .arxiv_downloader import get_downloaded_paper_ids, get_paper_metadata
        import math
        
        try:
            self.console.print("📋 [bold blue]Listing downloaded papers...[/bold blue]\n")
            
            # Get list of downloaded paper IDs
            paper_ids = get_downloaded_paper_ids(FILE_LOCATIONS)
            
            if not paper_ids:
                self.console.print("📭 [yellow]No papers have been downloaded yet.[/yellow]")
                self.console.print("💡 [dim]Use 'find <query>' to find and download papers.[/dim]")
                return
            
            # Get paper metadata for each ID and sort by title
            papers_with_metadata = []
            failed_papers = []
            
            with self.console.status(f"[bold green]Loading metadata for {len(paper_ids)} papers..."):
                for paper_id in paper_ids:
                    try:
                        metadata = get_paper_metadata(paper_id)
                        papers_with_metadata.append(metadata)
                    except Exception as e:
                        failed_papers.append((paper_id, str(e)))
            
            # Sort papers alphabetically by title
            papers_with_metadata.sort(key=lambda p: p.title.lower())
            
            # Display papers with pagination
            papers_per_page = 10  # Show 10 papers per page
            total_papers = len(papers_with_metadata)
            total_pages = math.ceil(total_papers / papers_per_page) if total_papers > 0 else 1
            
            current_page = 1
            
            while True:
                # Calculate start and end indices for current page
                start_idx = (current_page - 1) * papers_per_page
                end_idx = min(start_idx + papers_per_page, total_papers)
                current_papers = papers_with_metadata[start_idx:end_idx]
                
                # Create table for current page
                table = Table(title=f"Downloaded Papers (Page {current_page}/{total_pages})")
                table.add_column("Index", style="cyan", no_wrap=True, width=6)
                table.add_column("Paper ID", style="yellow", no_wrap=True, width=12)
                table.add_column("Title", style="white", width=60)
                table.add_column("Authors", style="green", width=30)
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
                    if failed_papers:
                        pagination_text += f" • {len(failed_papers)} failed to load"
                    
                    self.console.print(pagination_text)
                    
                    if current_page < total_pages:
                        self.console.print("[dim]Press Enter for next page, or type any other key to exit[/dim]")
                        from rich.prompt import Prompt
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
                    if failed_papers:
                        total_text += f" • {len(failed_papers)} failed to load"
                    self.console.print(total_text)
                    break
            
            # Show any failed papers
            if failed_papers:
                self.console.print(f"\n⚠️ [yellow]Failed to load metadata for {len(failed_papers)} paper(s):[/yellow]")
                for paper_id, error in failed_papers[:3]:  # Show first 3 failures
                    self.console.print(f"  • {paper_id}: {error}")
                if len(failed_papers) > 3:
                    self.console.print(f"  • ... and {len(failed_papers) - 3} more")
            
        except Exception as e:
            self.interface_adapter.show_error(f"List command failed: {str(e)}")
    
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
                
                # Handle special commands
                elif user_input.lower() == 'help':
                    self.show_help()
                
                elif user_input.lower() == 'status':
                    self.show_status()
                
                elif user_input.lower() == 'history':
                    self.show_history()
                
                elif user_input.lower() == 'clear':
                    self.clear_history()
                
                elif user_input.lower().startswith('find '):
                    query = user_input[5:].strip()
                    if query:
                        await self.process_search_command(query)
                    else:
                        self.console.print("❌ [red]Please provide a search query[/red]")
                
                elif user_input.lower().startswith('select '):
                    selection = user_input[7:].strip()
                    if selection:
                        await self.process_select_command(selection)
                    else:
                        self.console.print("❌ [red]Please provide a selection number[/red]")
                
                elif user_input.lower().startswith('improve '):
                    feedback = user_input[8:].strip()
                    if feedback:
                        await self.process_improve_command(feedback)
                    else:
                        self.console.print("❌ [red]Please provide improvement feedback[/red]")
                
                elif user_input.lower() == 'save':
                    await self.process_save_command()
                
                elif user_input.lower().startswith('semantic-search ') or user_input.lower().startswith('sem-search '):
                    # Handle both semantic-search and sem-search commands
                    if user_input.lower().startswith('semantic-search '):
                        query = user_input[16:].strip()  # "semantic-search " is 16 chars
                    else:
                        query = user_input[11:].strip()  # "sem-search " is 11 chars
                    
                    if query:
                        await self.process_semantic_search_command(query)
                    else:
                        self.console.print("❌ [red]Please provide a search query[/red]")
                
                elif user_input.lower() == 'list':
                    await self.process_list_command()
                
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