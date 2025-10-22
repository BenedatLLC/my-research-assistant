"""
Unit tests for the pagination.py module.

Tests cover:
- getch() function with mocked termios
- Paginator base class size calculations
- TablePaginator for row-aware table pagination
- TextPaginator for line-aware text pagination
"""
import pytest
from unittest.mock import patch, MagicMock, call
from rich.console import Console

from my_research_assistant.pagination import (
    getch,
    Paginator,
    TablePaginator,
    TextPaginator,
)
from my_research_assistant.project_types import PaperMetadata
import datetime


class TestGetch:
    """Test the getch() function for single-character input."""

    @patch('my_research_assistant.pagination.sys.stdin')
    @patch('my_research_assistant.pagination.termios')
    @patch('my_research_assistant.pagination.tty')
    def test_getch_reads_single_character(self, mock_tty, mock_termios, mock_stdin):
        """Test that getch() reads a single character."""
        mock_stdin.fileno.return_value = 0
        mock_stdin.read.return_value = 'a'
        mock_termios.tcgetattr.return_value = ['old', 'settings']

        result = getch()

        assert result == 'a'
        mock_termios.tcgetattr.assert_called_once_with(0)
        mock_tty.setraw.assert_called_once_with(0)
        mock_termios.tcsetattr.assert_called_once()
        mock_stdin.read.assert_called_once_with(1)

    @patch('my_research_assistant.pagination.sys.stdin')
    @patch('my_research_assistant.pagination.termios')
    @patch('my_research_assistant.pagination.tty')
    def test_getch_reads_space(self, mock_tty, mock_termios, mock_stdin):
        """Test that getch() reads space character."""
        mock_stdin.fileno.return_value = 0
        mock_stdin.read.return_value = ' '
        mock_termios.tcgetattr.return_value = ['old', 'settings']

        result = getch()

        assert result == ' '

    @patch('my_research_assistant.pagination.sys.stdin')
    @patch('my_research_assistant.pagination.termios')
    @patch('my_research_assistant.pagination.tty')
    def test_getch_reads_escape(self, mock_tty, mock_termios, mock_stdin):
        """Test that getch() reads escape character."""
        mock_stdin.fileno.return_value = 0
        mock_stdin.read.return_value = '\x1b'  # ESC
        mock_termios.tcgetattr.return_value = ['old', 'settings']

        result = getch()

        assert result == '\x1b'

    @patch('my_research_assistant.pagination.sys.stdin')
    @patch('my_research_assistant.pagination.termios')
    @patch('my_research_assistant.pagination.tty')
    def test_getch_reads_newline(self, mock_tty, mock_termios, mock_stdin):
        """Test that getch() reads newline character."""
        mock_stdin.fileno.return_value = 0
        mock_stdin.read.return_value = '\n'
        mock_termios.tcgetattr.return_value = ['old', 'settings']

        result = getch()

        assert result == '\n'

    @patch('my_research_assistant.pagination.sys.stdin')
    @patch('my_research_assistant.pagination.termios')
    @patch('my_research_assistant.pagination.tty')
    def test_getch_handles_ctrl_c(self, mock_tty, mock_termios, mock_stdin):
        """Test that getch() raises KeyboardInterrupt for Ctrl+C."""
        mock_stdin.fileno.return_value = 0
        mock_stdin.read.return_value = '\x03'  # Ctrl+C
        mock_termios.tcgetattr.return_value = ['old', 'settings']

        with pytest.raises(KeyboardInterrupt):
            getch()

    @patch('my_research_assistant.pagination.sys.stdin')
    @patch('my_research_assistant.pagination.termios')
    @patch('my_research_assistant.pagination.tty')
    def test_getch_restores_terminal_settings(self, mock_tty, mock_termios, mock_stdin):
        """Test that getch() restores terminal settings even on error."""
        mock_stdin.fileno.return_value = 0
        mock_stdin.read.side_effect = Exception("Read error")
        old_settings = ['old', 'settings']
        mock_termios.tcgetattr.return_value = old_settings

        with pytest.raises(Exception):
            getch()

        # Verify tcsetattr was called to restore settings
        restore_call = mock_termios.tcsetattr.call_args
        assert restore_call[0][0] == 0  # fd
        assert restore_call[0][1] == mock_termios.TCSADRAIN
        assert restore_call[0][2] == old_settings

    @patch('my_research_assistant.pagination.termios', None)
    @patch('my_research_assistant.pagination.Console')
    def test_getch_fallback_on_non_unix(self, mock_console_class):
        """Test that getch() raises NotImplementedError on non-Unix platforms."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with pytest.raises(NotImplementedError, match="getch.*only supported on Unix"):
            getch()


class TestPaginatorBaseClass:
    """Test the Paginator base class."""

    def test_calculate_initial_size_with_default_fill(self):
        """Test calculate_initial_size() with 80% fill (default)."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = Paginator(console)
        size = paginator.calculate_initial_size()

        # 50 * 0.8 = 40
        assert size == 40

    def test_calculate_initial_size_with_custom_fill(self):
        """Test calculate_initial_size() with custom fill percentage."""
        console = MagicMock(spec=Console)
        console.height = 100

        paginator = Paginator(console, initial_fill=0.6)
        size = paginator.calculate_initial_size()

        # 100 * 0.6 = 60
        assert size == 60

    def test_calculate_scroll_size_with_default_fill(self):
        """Test calculate_scroll_size() with 45% fill (default)."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = Paginator(console)
        size = paginator.calculate_scroll_size()

        # 50 * 0.45 = 22.5 -> 22
        assert size == 22

    def test_calculate_scroll_size_with_custom_fill(self):
        """Test calculate_scroll_size() with custom fill percentage."""
        console = MagicMock(spec=Console)
        console.height = 100

        paginator = Paginator(console, scroll_fill=0.5)
        size = paginator.calculate_scroll_size()

        # 100 * 0.5 = 50
        assert size == 50

    def test_small_terminal_initial_size(self):
        """Test calculate_initial_size() with small terminal."""
        console = MagicMock(spec=Console)
        console.height = 10

        paginator = Paginator(console)
        size = paginator.calculate_initial_size()

        # 10 * 0.8 = 8
        assert size == 8

    def test_small_terminal_scroll_size(self):
        """Test calculate_scroll_size() with small terminal."""
        console = MagicMock(spec=Console)
        console.height = 10

        paginator = Paginator(console)
        size = paginator.calculate_scroll_size()

        # 10 * 0.45 = 4.5 -> 4
        assert size == 4

    def test_zero_height_terminal(self):
        """Test size calculations with zero height (edge case)."""
        console = MagicMock(spec=Console)
        console.height = 0

        paginator = Paginator(console)

        # Should return 0 (let subclasses handle minimum)
        assert paginator.calculate_initial_size() == 0
        assert paginator.calculate_scroll_size() == 0

    def test_large_terminal_sizes(self):
        """Test size calculations with large terminal."""
        console = MagicMock(spec=Console)
        console.height = 200

        paginator = Paginator(console)

        # 200 * 0.8 = 160
        assert paginator.calculate_initial_size() == 160
        # 200 * 0.45 = 90
        assert paginator.calculate_scroll_size() == 90


class TestTablePaginator:
    """Test the TablePaginator class."""

    def create_papers(self, count: int) -> list[PaperMetadata]:
        """Helper to create test papers."""
        papers = []
        for i in range(count):
            papers.append(PaperMetadata(
                paper_id=f"2024.{i:05d}v1",
                title=f"Test Paper {i}",
                published=datetime.datetime(2024, 1, 1 + i % 28),
                updated=None,
                paper_abs_url=f"https://arxiv.org/abs/2024.{i:05d}v1",
                paper_pdf_url=f"https://arxiv.org/pdf/2024.{i:05d}v1.pdf",
                authors=["Author A", "Author B"],
                abstract="Test abstract",
                categories=["cs.AI"],
                doi=None,
                journal_ref=None
            ))
        return papers

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_zero_papers(self, mock_getch):
        """Test paginate_papers() with 0 papers shows no pagination prompt."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = TablePaginator(console)
        papers = []

        paginator.paginate_papers(papers)

        # Should not call getch (no pagination needed)
        mock_getch.assert_not_called()

        # Should print table (empty but with structure)
        console.print.assert_called()

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_few_papers_no_pagination(self, mock_getch):
        """Test paginate_papers() with papers that fit on one page."""
        console = MagicMock(spec=Console)
        console.height = 50  # Plenty of space for 5 papers

        paginator = TablePaginator(console)
        papers = self.create_papers(5)

        paginator.paginate_papers(papers)

        # Should not call getch (all fits on one page)
        mock_getch.assert_not_called()

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_many_papers_with_space_scroll(self, mock_getch):
        """Test paginate_papers() with many papers and space key scrolling."""
        console = MagicMock(spec=Console)
        console.height = 30  # Small terminal

        # Simulate: space, space, 'q' (quit)
        mock_getch.side_effect = [' ', ' ', 'q']

        paginator = TablePaginator(console)
        papers = self.create_papers(50)  # Many papers

        paginator.paginate_papers(papers)

        # Should call getch 3 times
        assert mock_getch.call_count == 3

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_exit_on_first_prompt(self, mock_getch):
        """Test paginate_papers() exits immediately on non-space key."""
        console = MagicMock(spec=Console)
        console.height = 30

        mock_getch.return_value = 'q'

        paginator = TablePaginator(console)
        papers = self.create_papers(50)

        paginator.paginate_papers(papers)

        # Should call getch once and exit
        mock_getch.assert_called_once()

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_auto_exit_at_end(self, mock_getch):
        """Test paginate_papers() auto-exits when content ends."""
        console = MagicMock(spec=Console)
        console.height = 30

        # Simulate many space presses (more than needed)
        mock_getch.side_effect = [' '] * 10

        paginator = TablePaginator(console)
        papers = self.create_papers(15)  # Just enough to need 2 pages

        paginator.paginate_papers(papers)

        # Should call getch less than 10 times (auto-exits at end)
        assert mock_getch.call_count < 10

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_handles_keyboard_interrupt(self, mock_getch):
        """Test paginate_papers() propagates KeyboardInterrupt."""
        console = MagicMock(spec=Console)
        console.height = 30

        mock_getch.side_effect = KeyboardInterrupt()

        paginator = TablePaginator(console)
        papers = self.create_papers(50)

        with pytest.raises(KeyboardInterrupt):
            paginator.paginate_papers(papers)

    def test_table_overhead_constant(self):
        """Test that TABLE_OVERHEAD is correctly defined."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = TablePaginator(console)

        # Should have TABLE_OVERHEAD attribute (title + header + borders + prompt)
        assert hasattr(paginator, 'TABLE_OVERHEAD')
        assert paginator.TABLE_OVERHEAD >= 6  # Minimum expected overhead

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_displays_all_papers_eventually(self, mock_getch):
        """Test that all papers are displayed if user keeps pressing space."""
        console = MagicMock(spec=Console)
        console.height = 20  # Very small terminal

        # Simulate lots of space presses
        mock_getch.side_effect = [' '] * 100

        paginator = TablePaginator(console)
        papers = self.create_papers(50)

        paginator.paginate_papers(papers)

        # Should eventually show all papers and auto-exit
        # Verify console.print was called multiple times
        assert console.print.call_count > 1


class TestTextPaginator:
    """Test the TextPaginator class."""

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_zero_lines(self, mock_getch):
        """Test paginate_lines() with 0 lines shows no pagination prompt."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = TextPaginator(console)
        lines = []

        paginator.paginate_lines(lines)

        # Should not call getch (no content)
        mock_getch.assert_not_called()

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_few_lines_no_pagination(self, mock_getch):
        """Test paginate_lines() with lines that fit on one page."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = TextPaginator(console)
        lines = ["Line " + str(i) for i in range(10)]

        paginator.paginate_lines(lines)

        # Should not call getch (all fits on one page)
        mock_getch.assert_not_called()

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_many_lines_with_space_scroll(self, mock_getch):
        """Test paginate_lines() with many lines and space key scrolling."""
        console = MagicMock(spec=Console)
        console.height = 30

        # Simulate: space, space, 'q'
        mock_getch.side_effect = [' ', ' ', 'q']

        paginator = TextPaginator(console)
        lines = ["Line " + str(i) for i in range(200)]

        paginator.paginate_lines(lines)

        # Should call getch 3 times
        assert mock_getch.call_count == 3

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_exit_on_first_prompt(self, mock_getch):
        """Test paginate_lines() exits immediately on non-space key."""
        console = MagicMock(spec=Console)
        console.height = 30

        mock_getch.return_value = 'q'

        paginator = TextPaginator(console)
        lines = ["Line " + str(i) for i in range(200)]

        paginator.paginate_lines(lines)

        # Should call getch once and exit
        mock_getch.assert_called_once()

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_auto_exit_at_end(self, mock_getch):
        """Test paginate_lines() auto-exits when content ends."""
        console = MagicMock(spec=Console)
        console.height = 30

        # Simulate many space presses
        mock_getch.side_effect = [' '] * 20

        paginator = TextPaginator(console)
        lines = ["Line " + str(i) for i in range(50)]

        paginator.paginate_lines(lines)

        # Should call getch less than 20 times (auto-exits at end)
        assert mock_getch.call_count < 20

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_with_title(self, mock_getch):
        """Test paginate_lines() with a title."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = TextPaginator(console)
        lines = ["Line " + str(i) for i in range(10)]

        paginator.paginate_lines(lines, title="Test Title")

        # Should not need pagination (fits on one page)
        mock_getch.assert_not_called()

        # Should print content (we can't easily verify title, but ensure it printed)
        console.print.assert_called()

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_handles_keyboard_interrupt(self, mock_getch):
        """Test paginate_lines() propagates KeyboardInterrupt."""
        console = MagicMock(spec=Console)
        console.height = 30

        mock_getch.side_effect = KeyboardInterrupt()

        paginator = TextPaginator(console)
        lines = ["Line " + str(i) for i in range(200)]

        with pytest.raises(KeyboardInterrupt):
            paginator.paginate_lines(lines)

    def test_text_overhead_constant(self):
        """Test that TEXT_OVERHEAD is correctly defined."""
        console = MagicMock(spec=Console)
        console.height = 50

        paginator = TextPaginator(console)

        # Should have TEXT_OVERHEAD attribute (panel borders + title + prompt)
        assert hasattr(paginator, 'TEXT_OVERHEAD')
        assert paginator.TEXT_OVERHEAD >= 4  # Minimum expected overhead

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_displays_all_lines_eventually(self, mock_getch):
        """Test that all lines are displayed if user keeps pressing space."""
        console = MagicMock(spec=Console)
        console.height = 20

        # Simulate lots of space presses
        mock_getch.side_effect = [' '] * 100

        paginator = TextPaginator(console)
        lines = ["Line " + str(i) for i in range(100)]

        paginator.paginate_lines(lines)

        # Should eventually show all lines and auto-exit
        assert console.print.call_count > 1

    @patch('my_research_assistant.pagination.getch')
    def test_paginate_preserves_markdown(self, mock_getch):
        """Test that paginate_lines() can handle markdown content."""
        console = MagicMock(spec=Console)
        console.height = 30

        mock_getch.return_value = 'q'

        paginator = TextPaginator(console)
        # Markdown-like content
        lines = [
            "# Title",
            "",
            "Some **bold** text",
            "",
            "- List item 1",
            "- List item 2",
        ] * 50  # Repeat to require pagination

        paginator.paginate_lines(lines)

        # Should call getch (requires pagination)
        mock_getch.assert_called_once()

        # Content should be printed (markdown rendering happens in Rich)
        console.print.assert_called()
