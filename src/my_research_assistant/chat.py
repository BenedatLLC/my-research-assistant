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
from .types import PaperMetadata


class ChatInterface:
    """Interactive chat interface for the research assistant."""
    
    def __init__(self):
        self.console = Console()
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
            
            # Initialize workflow runner
            self.workflow_runner = WorkflowRunner(llm=self.llm, file_locations=FILE_LOCATIONS)
            
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

* **Search** for papers on ArXiv
* **Download** papers to your local library
* **Index** papers for semantic search
* **Search** your indexed papers semantically
* **Summarize** papers with AI-powered analysis
* **Refine** summaries based on your feedback

## Commands:
* `search <query>` - Search for papers on ArXiv
* `sem-search <query>` - Search your indexed papers semantically
* `help` - Show this help message  
* `status` - Show current status
* `history` - Show conversation history
* `clear` - Clear conversation history
* `quit` or `exit` - Exit the chat

## Getting Started:
* Search ArXiv: `search machine learning transformers`
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
            "search <query>", 
            "Search for papers on ArXiv", 
            "search neural networks"
        )
        help_table.add_row(
            "sem-search <query>", 
            "Search your indexed papers semantically", 
            "sem-search agent safety"
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
        """Display paper search results in a formatted table."""
        if not papers:
            self.console.print("❌ [red]No papers found[/red]")
            return
        
        table = Table(title=f"📄 Found {len(papers)} Paper(s)")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Title", style="white", max_width=50)
        table.add_column("Authors", style="yellow", max_width=30)
        table.add_column("Published", style="green", width=12)
        table.add_column("Categories", style="blue", max_width=25)
        
        for i, paper in enumerate(papers, 1):
            # Truncate long titles and author lists
            title = paper.title[:47] + "..." if len(paper.title) > 50 else paper.title
            authors = ", ".join(paper.authors[:2])
            if len(paper.authors) > 2:
                authors += f" + {len(paper.authors) - 2} more"
            
            categories = ", ".join(paper.categories[:2])
            if len(paper.categories) > 2:
                categories += "..."
                
            table.add_row(
                str(i),
                title,
                authors,
                paper.published.strftime('%Y-%m-%d'),
                categories
            )
        
        self.console.print(table)
        self.current_papers = papers
        
        if len(papers) == 1:
            self.console.print("\n[yellow]This is the best match. Type 'select 1' to proceed or search again.[/yellow]")
        else:
            self.console.print(f"\n[yellow]Type 'select <number>' (1-{len(papers)}) to choose a paper.[/yellow]")
    
    def render_markdown_response(self, content: str):
        """Render markdown content with rich formatting."""
        if content.strip().startswith('#') or '**' in content or '*' in content:
            # Looks like markdown, render it
            self.console.print(Panel(
                Markdown(content),
                title="📝 Response",
                border_style="green"
            ))
        else:
            # Plain text response
            self.console.print(Panel(
                content,
                title="💬 Response",
                border_style="green"
            ))
    
    async def process_search_command(self, query: str):
        """Process a search command."""
        self.current_state = "searching"
        
        try:
            with self.console.status(f"[bold green]Searching ArXiv for: '{query}'..."):
                from .arxiv_downloader import search_arxiv_papers
                papers = search_arxiv_papers(query, k=5)
            
            self.display_papers(papers)
            self.current_state = "paper_selection"
            
        except Exception as e:
            self.console.print(f"❌ [red]Search failed: {str(e)}[/red]")
            self.current_state = "ready"
    
    async def process_select_command(self, selection: str):
        """Process a paper selection command."""
        if not self.current_papers:
            self.console.print("❌ [red]No papers available to select. Search first.[/red]")
            return
        
        try:
            paper_num = int(selection) - 1
            if paper_num < 0 or paper_num >= len(self.current_papers):
                self.console.print(f"❌ [red]Invalid selection. Choose 1-{len(self.current_papers)}[/red]")
                return
            
            selected_paper = self.current_papers[paper_num]
            self.console.print(f"✅ [green]Selected: {selected_paper.title}[/green]")
            
            # Run the workflow for the selected paper
            await self.run_paper_workflow(selected_paper)
            
        except ValueError:
            self.console.print("❌ [red]Invalid selection. Enter a number.[/red]")
        except Exception as e:
            self.console.print(f"❌ [red]Selection failed: {str(e)}[/red]")
    
    async def run_paper_workflow(self, paper: PaperMetadata):
        """Run the complete paper processing workflow."""
        self.current_state = "processing"
        
        try:
            # Download
            with self.console.status("[bold yellow]📥 Downloading paper..."):
                from .arxiv_downloader import download_paper
                local_path = download_paper(paper, FILE_LOCATIONS)
            
            self.console.print(f"✅ [green]Downloaded to: {local_path}[/green]")
            
            # Index
            with self.console.status("[bold yellow]🔍 Indexing paper..."):
                from .vector_store import index_file
                paper_text = index_file(paper)
            
            self.console.print(f"✅ [green]Indexed {len(paper_text)} characters[/green]")
            
            # Summarize
            with self.console.status("[bold yellow]📝 Generating summary..."):
                from .summarizer import summarize_paper
                summary = summarize_paper(paper_text, paper)
            
            self.console.print("✅ [green]Summary generated![/green]\n")
            self.render_markdown_response(summary)
            
            # Store for potential improvements
            self.current_summary = summary
            self.current_paper = paper
            self.current_paper_text = paper_text
            self.current_state = "summary_ready"
            
            self.console.print("\n[yellow]💡 You can now:[/yellow]")
            self.console.print("• Type 'improve <feedback>' to refine the summary")
            self.console.print("• Type 'save' to save the summary")
            self.console.print("• Type 'search <new query>' to start over")
            
        except Exception as e:
            self.console.print(f"❌ [red]Workflow failed: {str(e)}[/red]")
            self.current_state = "ready"
    
    async def process_improve_command(self, feedback: str):
        """Process a summary improvement command."""
        if self.current_state != "summary_ready":
            self.console.print("❌ [red]No summary to improve. Process a paper first.[/red]")
            return
        
        try:
            with self.console.status("[bold yellow]🔄 Improving summary..."):
                from .summarizer import summarize_paper
                improved_summary = summarize_paper(
                    self.current_paper_text, 
                    self.current_paper, 
                    feedback=feedback, 
                    previous_summary=self.current_summary
                )
            
            self.console.print("✅ [green]Summary improved![/green]\n")
            self.render_markdown_response(improved_summary)
            
            # Update current summary
            self.current_summary = improved_summary
            
            self.console.print("\n[yellow]💡 You can continue to improve or type 'save' to save.[/yellow]")
            
        except Exception as e:
            self.console.print(f"❌ [red]Improvement failed: {str(e)}[/red]")
    
    async def process_save_command(self):
        """Process a save summary command."""
        if self.current_state != "summary_ready":
            self.console.print("❌ [red]No summary to save. Process a paper first.[/red]")
            return
        
        try:
            with self.console.status("[bold yellow]💾 Saving summary..."):
                from .summarizer import save_summary
                file_path = save_summary(self.current_summary, self.current_paper.paper_id)
            
            self.console.print(f"✅ [green]Summary saved to: {file_path}[/green]")
            
            # Show completion summary
            completion_panel = Panel(
                f"""
🎉 **Process Complete!**

**Paper:** {self.current_paper.title}
**Actions Completed:**
  • Downloaded PDF
  • Indexed for search
  • Generated summary
  • Saved to filesystem

**Summary Location:** {file_path}

You can now search for another paper or type 'quit' to exit.
                """,
                title="✅ Success",
                border_style="green"
            )
            self.console.print(completion_panel)
            
            # Reset state
            self.current_state = "ready"
            
        except Exception as e:
            self.console.print(f"❌ [red]Save failed: {str(e)}[/red]")
    
    async def process_semantic_search_command(self, query: str):
        """Process a semantic search command."""
        self.current_state = "semantic_searching"
        
        try:
            with self.console.status(f"[bold green]Searching indexed papers for: '{query}'..."):
                result = await self.workflow_runner.start_semantic_search_workflow(query)
            
            if result and not result.startswith("❌"):
                self.console.print("✅ [green]Semantic search completed![/green]\n")
                
                # Render the result as markdown
                self.render_markdown_response(result)
                
                # Add to history
                self.add_to_history("assistant", result)
                
            else:
                # Handle error case
                error_msg = result if result else "Unknown error occurred"
                self.console.print(f"❌ [red]{error_msg}[/red]")
            
            # Reset state
            self.current_state = "ready"
            
        except Exception as e:
            self.console.print(f"❌ [red]Semantic search failed: {str(e)}[/red]")
            self.current_state = "ready"
    
    async def run_chat_loop(self):
        """Main chat loop."""
        self.show_welcome()
        
        if not self.initialize():
            return
        
        self.console.print("\n🎯 [bold green]Ready! Type 'help' for commands or start with 'search <your query>'[/bold green]\n")
        
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
                
                elif user_input.lower().startswith('search '):
                    query = user_input[7:].strip()
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
                
                else:
                    self.console.print("❓ [yellow]Unknown command. Type 'help' for available commands.[/yellow]")
                
            except KeyboardInterrupt:
                self.console.print("\n👋 [bold blue]Goodbye! Happy researching![/bold blue]")
                break
            except EOFError:
                self.console.print("\n👋 [bold blue]Goodbye! Happy researching![/bold blue]")
                break
            except Exception as e:
                self.console.print(f"❌ [red]Unexpected error: {str(e)}[/red]")


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