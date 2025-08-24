"""Interface adapters for UI-agnostic workflow interaction.

This module implements the Adapter pattern to decouple the core workflow logic
from specific user interface implementations. It enables the same business logic
to work seamlessly across different interface types while maintaining consistent
user experience and functionality.

## Architecture Overview

The interface adapter system consists of:

1. **InterfaceAdapter** (Abstract): Defines the contract for all UI implementations
2. **TerminalAdapter** (Concrete): Rich terminal interface with formatting and progress indicators  
3. **WebAdapter** (Concrete): Future web interface for HTTP/WebSocket communication

## Key Design Benefits

- **UI Independence**: Core workflow logic doesn't depend on specific UI frameworks
- **Consistent Experience**: Same operations produce consistent results across interfaces
- **Easy Extension**: New interface types can be added without changing core logic
- **Testability**: Business logic can be tested with mock interface adapters
- **Future-Proof**: Supports planned web and API interfaces

## Usage Patterns

```python
# Terminal usage
from rich.console import Console
terminal_adapter = TerminalAdapter(Console())

# Future web usage  
web_adapter = WebAdapter(websocket_connection)

# Both work with the same workflow
workflow_runner = WorkflowRunner(llm, terminal_adapter)
workflow_runner = WorkflowRunner(llm, web_adapter)
```

## Interface Contract

All adapters must implement:
- Progress indication for long operations
- Success/error/info message display
- Content rendering (markdown, tables, etc.)
- Paper list display with selection UI
- User input collection

This ensures consistent behavior regardless of the underlying UI technology.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Any, Dict
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.status import Status
from contextlib import contextmanager

from .project_types import PaperMetadata


class InterfaceAdapter(ABC):
    """Abstract base class for UI adapters."""
    
    @abstractmethod
    def show_progress(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show a progress message to the user."""
        pass
    
    @abstractmethod
    def show_success(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show a success message to the user."""
        pass
    
    @abstractmethod
    def show_error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show an error message to the user."""
        pass
    
    @abstractmethod
    def show_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show an informational message to the user."""
        pass
    
    @abstractmethod
    def render_content(self, content: str, content_type: str = "text", title: Optional[str] = None):
        """Render rich content (markdown, text, etc.)."""
        pass
    
    @abstractmethod
    def display_papers(self, papers: List[PaperMetadata]) -> None:
        """Display a list of papers for user selection."""
        pass
    
    @abstractmethod
    async def get_user_input(self, prompt: str, options: Optional[List[str]] = None) -> str:
        """Get input from the user."""
        pass
    
    @contextmanager
    def progress_context(self, message: str):
        """Context manager for long-running operations."""
        self.show_progress(message)
        try:
            yield
        finally:
            pass


class TerminalAdapter(InterfaceAdapter):
    """Rich terminal implementation of the interface adapter."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._current_status = None
    
    def show_progress(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show progress with Rich status display."""
        if self._current_status:
            self._current_status.stop()
        # Don't start a new status here, let progress_context handle it
        pass
    
    def show_success(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show success message with green styling."""
        if self._current_status:
            self._current_status.stop()
            self._current_status = None
        self.console.print(f"✅ [green]{message}[/green]")
    
    def show_error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show error message with red styling."""
        if self._current_status:
            self._current_status.stop()
            self._current_status = None
        self.console.print(f"❌ [red]{message}[/red]")
    
    def show_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Show info message with blue styling."""
        if self._current_status:
            self._current_status.stop()
            self._current_status = None
        self.console.print(f"ℹ️ [blue]{message}[/blue]")
    
    def render_content(self, content: str, content_type: str = "text", title: Optional[str] = None):
        """Render content using Rich formatting."""
        if self._current_status:
            self._current_status.stop()
            self._current_status = None
            
        if content_type == "markdown" or content.strip().startswith('#') or '**' in content:
            # Render as markdown
            panel = Panel(
                Markdown(content),
                title=title or "📝 Response",
                border_style="green"
            )
        else:
            # Render as plain text
            panel = Panel(
                content,
                title=title or "💬 Response", 
                border_style="green"
            )
        
        self.console.print(panel)
    
    def display_papers(self, papers: List[PaperMetadata]) -> None:
        """Display papers using Rich table formatting."""
        if not papers:
            self.show_error("No papers found")
            return
        
        from rich.table import Table
        
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
        
        if len(papers) == 1:
            self.console.print("\n[yellow]This is the best match. Type 'select 1' to proceed or search again.[/yellow]")
        else:
            self.console.print(f"\n[yellow]Type 'select <number>' (1-{len(papers)}) to choose a paper.[/yellow]")
    
    async def get_user_input(self, prompt: str, options: Optional[List[str]] = None) -> str:
        """Get user input with Rich prompt."""
        from rich.prompt import Prompt
        
        if options:
            prompt_text = f"{prompt} ({'/'.join(options)})"
        else:
            prompt_text = prompt
            
        return Prompt.ask(prompt_text, console=self.console)
    
    @contextmanager
    def progress_context(self, message: str):
        """Context manager for showing progress during operations."""
        status = self.console.status(f"[bold yellow]{message}")
        self._current_status = status
        status.start()
        try:
            yield
        finally:
            status.stop()
            self._current_status = None


class WebAdapter(InterfaceAdapter):
    """Web interface adapter (placeholder for future implementation)."""
    
    def __init__(self, websocket_connection=None):
        self.websocket = websocket_connection
        self.events = []
    
    def show_progress(self, message: str, context: Optional[Dict[str, Any]] = None):
        event = {"type": "progress", "message": message, "context": context}
        self.events.append(event)
        if self.websocket:
            # Future: emit to websocket
            pass
    
    def show_success(self, message: str, context: Optional[Dict[str, Any]] = None):
        event = {"type": "success", "message": message, "context": context}
        self.events.append(event)
        if self.websocket:
            # Future: emit to websocket
            pass
    
    def show_error(self, message: str, context: Optional[Dict[str, Any]] = None):
        event = {"type": "error", "message": message, "context": context}
        self.events.append(event)
        if self.websocket:
            # Future: emit to websocket
            pass
    
    def show_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        event = {"type": "info", "message": message, "context": context}
        self.events.append(event)
        if self.websocket:
            # Future: emit to websocket
            pass
    
    def render_content(self, content: str, content_type: str = "text", title: Optional[str] = None):
        event = {
            "type": "content",
            "content": content,
            "content_type": content_type,
            "title": title
        }
        self.events.append(event)
        if self.websocket:
            # Future: emit to websocket
            pass
    
    def display_papers(self, papers: List[PaperMetadata]) -> None:
        event = {
            "type": "papers",
            "papers": [paper.model_dump() for paper in papers]
        }
        self.events.append(event)
        if self.websocket:
            # Future: emit to websocket
            pass
    
    async def get_user_input(self, prompt: str, options: Optional[List[str]] = None) -> str:
        # Future: handle via websocket/HTTP request
        event = {
            "type": "input_request",
            "prompt": prompt,
            "options": options
        }
        self.events.append(event)
        # For now, return empty string as placeholder
        return ""
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all events for web clients."""
        return self.events.copy()
    
    def clear_events(self):
        """Clear event history."""
        self.events.clear()