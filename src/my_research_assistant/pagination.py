"""
Pagination utilities for single-keypress interactive scrolling.

This module provides terminal pagination with immediate keypress response
(no Enter key required). Features:
- Single-character input using termios (Unix/macOS)
- Space bar to scroll ~40-50% more content
- Any other key to exit pagination
- Terminal-aware sizing
- Cumulative display (no clearing between pages)
- Auto-exit when reaching end of content

Components:
- getch(): Read single character without echo
- Paginator: Base class for pagination logic
- TablePaginator: Row-aware pagination for Rich tables
- TextPaginator: Line-aware pagination for text/markdown
"""
import sys
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from my_research_assistant.project_types import PaperMetadata

# Try to import termios/tty (Unix/macOS only)
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    termios = None
    tty = None
    HAS_TERMIOS = False


def getch() -> str:
    """Read a single character from stdin without echo.

    Uses termios to set raw mode temporarily, reads one character,
    then restores terminal settings.

    Returns:
        The character pressed (including special chars like space, newline)

    Raises:
        KeyboardInterrupt: If Ctrl+C is pressed
        NotImplementedError: If termios not available (non-Unix platform)
    """
    if not HAS_TERMIOS or termios is None:
        console = Console()
        console.print("[yellow]Warning: getch() is only supported on Unix/macOS platforms[/yellow]")
        raise NotImplementedError("getch() is only supported on Unix/macOS platforms")

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)

        # Handle Ctrl+C
        if ch == '\x03':
            raise KeyboardInterrupt()

        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class Paginator:
    """Base class for pagination with single-key input.

    Provides common functionality for calculating page sizes based on
    terminal height and managing pagination state.

    Attributes:
        console: Rich Console instance for terminal operations
        initial_fill: Fraction of terminal height for initial display (default 0.8)
        scroll_fill: Fraction of terminal height to add per scroll (default 0.45)
    """

    def __init__(self, console: Console, initial_fill: float = 0.8, scroll_fill: float = 0.45):
        """
        Args:
            console: Rich Console instance
            initial_fill: Fraction of terminal height for initial display (default 0.8)
            scroll_fill: Fraction of terminal height to add per scroll (default 0.45)
        """
        self.console = console
        self.initial_fill = initial_fill
        self.scroll_fill = scroll_fill

    def calculate_initial_size(self) -> int:
        """Calculate initial page size in rows based on terminal height.

        Returns:
            Number of rows for initial display (80% of terminal height by default)
        """
        return int(self.console.height * self.initial_fill)

    def calculate_scroll_size(self) -> int:
        """Calculate scroll amount in rows based on terminal height.

        Returns:
            Number of rows to add per scroll (45% of terminal height by default)
        """
        return int(self.console.height * self.scroll_fill)


class TablePaginator(Paginator):
    """Paginator for Rich tables with row-aware scrolling.

    Displays papers in a table format with incremental scrolling.
    Ensures complete rows are always shown (no mid-row breaks).
    """

    # Table overhead: title (1) + header (2) + borders (2) + pagination prompt (2) = 7
    TABLE_OVERHEAD = 7

    def paginate_papers(self, papers: List[PaperMetadata]) -> None:
        """Display papers with pagination.

        Args:
            papers: List of paper metadata to display

        Displays:
            - Table with papers
            - Pagination prompts
            - Adds more rows when space is pressed
            - Exits on any other key

        The pagination is cumulative - content remains visible between scrolls.
        Auto-exits when all content has been displayed.
        """
        if not papers:
            # Display empty table
            table = self._create_table([], 0)
            self.console.print(table)
            return

        # Calculate initial page size
        terminal_height = self.console.height
        initial_rows = self.calculate_initial_size()
        rows_per_page = max(1, initial_rows - self.TABLE_OVERHEAD)

        # Calculate scroll size
        scroll_rows = max(1, self.calculate_scroll_size())

        # Debug output for terminal size detection
        # self.console.print(f"[dim]Debug: Terminal height={terminal_height}, initial_rows={initial_rows}, overhead={self.TABLE_OVERHEAD}, rows_per_page={rows_per_page}, total_papers={len(papers)}[/dim]")

        # Track current position
        current_end = min(rows_per_page, len(papers))

        # Display initial page
        table = self._create_table(papers, current_end)
        self.console.print(table)

        # Pagination loop
        while current_end < len(papers):
            # Show pagination prompt
            self.console.print("\n[dim]Press [bold]SPACE[/bold] to show more, or any other key to exit[/dim]")

            try:
                ch = getch()
            except KeyboardInterrupt:
                # Propagate Ctrl+C
                raise
            except Exception as e:
                # getch() not available or terminal error - display all remaining content
                # This catches NotImplementedError, termios.error, OSError, etc.
                if not isinstance(e, KeyboardInterrupt):
                    self.console.print(f"\n[yellow]Note: Interactive pagination not available ({type(e).__name__})[/yellow]")
                    self.console.print("[yellow]Displaying all remaining content...[/yellow]\n")
                    # Display all remaining papers
                    table = self._create_table(papers, len(papers))
                    self.console.print(table)
                    return
                else:
                    raise

            if ch != ' ':
                # User wants to exit
                return

            # Add more rows
            current_end = min(current_end + scroll_rows, len(papers))

            # Display updated table (cumulative)
            table = self._create_table(papers, current_end)
            self.console.print(table)

        # Auto-exit when all content displayed (no final prompt)

    def _create_table(self, papers: List[PaperMetadata], up_to: int) -> Table:
        """Create a Rich table with papers up to the specified index.

        Args:
            papers: Full list of papers
            up_to: Index of last paper to include (exclusive)

        Returns:
            Rich Table with papers
        """
        table = Table(title=f"Page (showing {up_to} of {len(papers)})", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", no_wrap=True, width=4)
        table.add_column("Paper ID", style="yellow", no_wrap=True, width=14)
        table.add_column("Title", style="white", no_wrap=True, width=55)  # Force no wrap
        table.add_column("Authors", style="green", no_wrap=True, width=25)  # Force no wrap
        table.add_column("Published", style="blue", no_wrap=True, width=10)

        for i, paper in enumerate(papers[:up_to], 1):
            # Truncate long titles to fit in column
            title = paper.title if len(paper.title) <= 55 else paper.title[:52] + "..."

            # Format authors (first 2 + more indicator), truncate to fit
            authors = ", ".join(paper.authors[:2])
            if len(paper.authors) > 2:
                authors += f" +{len(paper.authors) - 2} more"
            if len(authors) > 25:
                authors = authors[:22] + "..."

            # Format publication date
            published_date = paper.published.strftime('%Y-%m-%d')

            table.add_row(
                str(i),
                paper.paper_id,
                title,
                authors,
                published_date
            )

        return table


class TextPaginator(Paginator):
    """Paginator for text/markdown content with line-aware scrolling.

    Displays text content in a panel with markdown rendering and
    incremental scrolling. Preserves markdown formatting throughout.
    """

    # Text overhead: panel borders (2) + title (1) + pagination prompt (2) = 5
    TEXT_OVERHEAD = 5

    def paginate_lines(self, lines: List[str], title: Optional[str] = None) -> None:
        """Display text content with pagination.

        Args:
            lines: List of text lines to display
            title: Optional title for panel

        Displays:
            - Content in panel with markdown rendering
            - Pagination prompts
            - Adds more lines when space is pressed
            - Exits on any other key

        The pagination is cumulative - content remains visible between scrolls.
        Auto-exits when all content has been displayed.
        """
        if not lines:
            # Display empty panel
            panel = Panel("", title=title or "Content")
            self.console.print(panel)
            return

        # Calculate initial page size
        initial_size = self.calculate_initial_size()
        lines_per_page = max(5, initial_size - self.TEXT_OVERHEAD)

        # Calculate scroll size
        scroll_lines = max(5, self.calculate_scroll_size())

        # Track current position
        current_end = min(lines_per_page, len(lines))

        # Display initial page
        self._display_content(lines, current_end, title)

        # Pagination loop
        while current_end < len(lines):
            # Show pagination prompt
            self.console.print("\n[dim]Press [bold]SPACE[/bold] to show more, or any other key to exit[/dim]")

            try:
                ch = getch()
            except KeyboardInterrupt:
                # Propagate Ctrl+C
                raise
            except Exception as e:
                # getch() not available or terminal error - display all remaining content
                # This catches NotImplementedError, termios.error, OSError, etc.
                if not isinstance(e, KeyboardInterrupt):
                    self.console.print(f"\n[yellow]Note: Interactive pagination not available ({type(e).__name__})[/yellow]")
                    self.console.print("[yellow]Displaying all remaining content...[/yellow]\n")
                    # Display all remaining lines
                    self._display_content(lines, len(lines), title)
                    return
                else:
                    raise

            if ch != ' ':
                # User wants to exit
                return

            # Add more lines
            current_end = min(current_end + scroll_lines, len(lines))

            # Display updated content (cumulative)
            self._display_content(lines, current_end, title)

        # Auto-exit when all content displayed (no final prompt)

    def _display_content(self, lines: List[str], up_to: int, title: Optional[str]) -> None:
        """Display content lines in a panel with markdown rendering.

        Args:
            lines: Full list of lines
            up_to: Index of last line to include (exclusive)
            title: Optional panel title
        """
        content = "\n".join(lines[:up_to])
        markdown = Markdown(content)
        panel = Panel(markdown, title=title or "Content", border_style="blue")
        self.console.print(panel)
