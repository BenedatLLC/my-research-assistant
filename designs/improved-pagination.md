# Improved Pagination Design

**Status**: Draft
**Created**: 2025-10-20
**Updated**: 2025-10-20

## Overview

Replace the current line-buffered pagination (requires Enter key) with single-key pagination that responds immediately to keypresses. The pagination should be responsive to terminal size and display content incrementally without clearing.

## Problem Statement

Current pagination has usability issues:
1. Displays "Press Enter for next page, or type any other key to exit" but requires Enter even for other keys
2. Uses `Prompt.ask()` which requires line-buffered input
3. Fixed page sizes don't adapt to terminal height
4. User experience is awkward - misleading instructions

Example of current behavior:
```
Press Enter for next page, or type any other key to exit
 ():  # User types 'q' but nothing happens until Enter is pressed
```

## Requirements

### Functional Requirements

1. **Single-key input**: Read keypresses without requiring Enter
2. **Space bar scrolling**: Press SPACE to add ~40-50% more content
3. **Immediate exit**: Press any other key to exit pagination and return to command prompt
4. **Terminal-aware sizing**: Calculate page sizes based on actual terminal height
5. **Cumulative display**: Content remains visible (no clearing between pages)
6. **Auto-exit**: Automatically exit when reaching end of content

### User Experience Requirements

1. **List command** (`list`):
   - Initial display: Fill ~80% of terminal height with table rows
   - Scroll amount: Add ~40-50% more rows (don't break mid-row)
   - Keep table formatting consistent

2. **Open command** (`open` with terminal display):
   - Initial display: Fill ~80% of terminal height with content
   - Scroll amount: Add ~40-50% more lines
   - Preserve markdown rendering

3. **Other potential uses**:
   - Research results
   - Long summaries
   - Search results

### Technical Requirements

1. Platform compatibility: Unix/macOS (primary), with graceful fallback
2. Handle special keys properly (Ctrl+C should interrupt)
3. Reusable pagination utility for other commands
4. Don't break existing tests

## Design

### Architecture

#### New Module: `pagination.py`

**Location**: `src/my_research_assistant/pagination.py`

**Components**:

1. **`getch()` function**: Single-character input without echo
   - Uses `termios` + `tty` on Unix/macOS
   - Returns the character pressed
   - Handles Ctrl+C (raises KeyboardInterrupt)

2. **`Paginator` base class**: Common pagination logic
   - Terminal height detection
   - Page size calculations
   - Scroll amount calculations
   - Pagination state management

3. **`TablePaginator` class**: For Rich tables
   - Calculates rows per page based on terminal height
   - Ensures no mid-row breaks
   - Handles table headers and borders

4. **`TextPaginator` class**: For text/markdown content
   - Line-based pagination
   - Preserves markdown rendering

### Pagination Flow

```
┌─────────────────────────────────────┐
│ 1. Calculate initial page size      │
│    - Based on terminal height       │
│    - ~80% of available space        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Display initial page             │
│    - Render content                 │
│    - Show pagination prompt         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Read single character (getch)    │
└──────────────┬──────────────────────┘
               │
         ┌─────┴─────┐
         │           │
    SPACE key    Other key
         │           │
         ▼           ▼
┌────────────┐  ┌──────────┐
│ Add ~45%   │  │ Exit     │
│ more       │  │ Return   │
│ content    │  │ to cmd   │
└─────┬──────┘  └──────────┘
      │
      ▼
┌──────────────┐
│ At end?      │
└─────┬────────┘
      │
  Yes │ No
      │ └──> Back to step 3
      ▼
┌──────────────┐
│ Auto-exit    │
│ to command   │
└──────────────┘
```

### Terminal Size Calculations

**Initial page size**: 80% of terminal height
```python
initial_rows = int(console.height * 0.8)
```

**Scroll amount**: 45% of terminal height (middle of 40-50% range)
```python
scroll_rows = int(console.height * 0.45)
```

**For tables**:
- Account for table header (2-3 lines)
- Account for borders
- Account for pagination prompt (2-3 lines)
- Ensure we show complete rows only

**For text**:
- Account for panel borders if used
- Account for pagination prompt
- Line-based scrolling

### API Design

```python
# pagination.py

def getch() -> str:
    """Read a single character from stdin without echo.

    Returns:
        The character pressed (including special chars like space, newline)

    Raises:
        KeyboardInterrupt: If Ctrl+C is pressed
    """
    pass


class Paginator:
    """Base class for pagination with single-key input."""

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
        """Calculate initial page size in rows."""
        pass

    def calculate_scroll_size(self) -> int:
        """Calculate scroll amount in rows."""
        pass


class TablePaginator(Paginator):
    """Paginator for Rich tables with row-aware scrolling."""

    def paginate_papers(self, papers: List[PaperMetadata]) -> None:
        """Display papers with pagination.

        Args:
            papers: List of paper metadata to display

        Displays:
            - Table with papers
            - Pagination prompts
            - Adds more rows when space is pressed
            - Exits on any other key
        """
        pass


class TextPaginator(Paginator):
    """Paginator for text/markdown content with line-aware scrolling."""

    def paginate_lines(self, lines: List[str], title: str = None) -> None:
        """Display text content with pagination.

        Args:
            lines: List of text lines to display
            title: Optional title for panel

        Displays:
            - Content (optionally in panel with markdown)
            - Pagination prompts
            - Adds more lines when space is pressed
            - Exits on any other key
        """
        pass
```

### Integration Points

#### List Command (`process_list_command`)

**Current approach** (lines 470-582):
```python
while True:
    # Create table for current page
    # Display table
    # Prompt.ask() for next page
    # Check if user_input != ""
```

**New approach**:
```python
paginator = TablePaginator(self.console)
paginator.paginate_papers(papers)
# Returns when user exits pagination
```

#### Open Command (`process_open_command`)

**Current approach** (lines 1005-1031):
```python
while True:
    # Calculate page
    # Display in panel
    # Prompt.ask() for next page
```

**New approach**:
```python
paginator = TextPaginator(self.console)
lines = content.split('\n')
paginator.paginate_lines(lines, title=paper.title)
# Returns when user exits pagination
```

## Implementation Plan

### Summary
Implement a new pagination system with single-keypress interaction using termios for Unix/macOS platforms. The implementation creates reusable pagination components (base class + table/text specializations) and integrates them into the list and open commands. The approach uses Rich console for terminal size detection and preserves cumulative display without clearing.

### Files to Create/Modify

**New Files**:
1. `src/my_research_assistant/pagination.py` - Core pagination module with getch(), Paginator base class, TablePaginator, TextPaginator
2. `tests/test_pagination.py` - Unit tests for pagination components
3. `tests/test_pagination_integration.py` - Integration tests for list/open command pagination

**Files to Modify**:
1. `src/my_research_assistant/chat.py` - Replace line-buffered pagination in process_list_command() (lines 504-559) and process_open_command() (lines 1005-1031)

### Step-by-Step Plan

#### Phase 1: Core Pagination Utility (TDD)
1. **Create pagination.py skeleton**
   - Import necessary modules (termios, tty, sys, rich.console)
   - Define getch() function signature
   - Define Paginator base class structure

2. **Write tests FIRST** (`tests/test_pagination.py`):
   - Test getch() with mocked termios (character input, space, escape, Ctrl+C)
   - Test getch() fallback on non-Unix platforms
   - Test Paginator.calculate_initial_size() with various terminal heights (10, 20, 50, 100 lines)
   - Test Paginator.calculate_scroll_size() with various heights
   - Test edge cases: very small terminal (< 20 lines), zero height

3. **Implement to make tests pass**:
   - Implement getch() with termios + tty for Unix/macOS
   - Add try/except for graceful fallback with warning on non-Unix
   - Implement Paginator base class with terminal size calculations
   - Use console.height for dynamic sizing
   - Apply initial_fill (0.8) and scroll_fill (0.45) percentages
   - Handle minimum sizes for small terminals

#### Phase 2: Table Pagination (TDD)
1. **Write tests FIRST** (`tests/test_pagination.py`):
   - Test TablePaginator with 0 papers (no pagination prompt)
   - Test TablePaginator with 5 papers (fits in one page, no pagination)
   - Test TablePaginator with 50 papers (requires multiple scrolls)
   - Test that rows are never broken mid-row
   - Test space key adds ~45% more rows
   - Test any-other-key exits pagination
   - Test auto-exit when content ends mid-scroll
   - Test table overhead calculations (title, headers, borders ~6 lines)

2. **Implement TablePaginator class**:
   - Calculate table overhead: title (1) + header (2) + borders (2) + pagination prompt (2) = ~7 lines
   - Calculate rows per initial page: max(1, int(console.height * 0.8) - overhead)
   - Calculate rows per scroll: max(1, int(console.height * 0.45))
   - Implement paginate_papers() method:
     - Display initial table with calculated rows
     - Show pagination prompt if more content
     - Read character with getch()
     - If space: add scroll_rows, repeat
     - If other key: exit
     - If end of content: auto-exit
   - Build cumulative table (add rows incrementally, don't clear)

3. **Write integration tests FIRST** (`tests/test_pagination_integration.py`):
   - Test list command with 0 papers (no pagination)
   - Test list command with 10 papers (single page)
   - Test list command with 100 papers (multiple scrolls)
   - Mock getch() to simulate space key presses
   - Verify state machine transitions work correctly
   - Verify query_set is preserved

4. **Integrate into process_list_command**:
   - Replace lines 504-559 in chat.py with TablePaginator call
   - Remove Prompt.ask() usage
   - Remove page-based logic
   - Keep summary info and next steps display at end
   - Ensure state machine transitions remain unchanged

#### Phase 3: Text Pagination (TDD)
1. **Write tests FIRST** (`tests/test_pagination.py`):
   - Test TextPaginator with empty content (no pagination)
   - Test TextPaginator with 10 lines (fits in one page)
   - Test TextPaginator with 200 lines (requires multiple scrolls)
   - Test space key adds ~45% more lines
   - Test markdown rendering preservation
   - Test panel overhead calculations (~5 lines)
   - Test auto-exit at end of content

2. **Implement TextPaginator class**:
   - Calculate text overhead: panel borders (2) + title (1) + pagination prompt (2) = ~5 lines
   - Calculate lines per initial page: max(5, int(console.height * 0.8) - overhead)
   - Calculate lines per scroll: max(5, int(console.height * 0.45))
   - Implement paginate_lines() method:
     - Display initial panel with markdown rendering
     - Show pagination prompt if more content
     - Read character with getch()
     - If space: add scroll_lines, display cumulative content, repeat
     - If other key: exit
     - If end of content: auto-exit
   - Display cumulative content (don't clear panels between scrolls)

3. **Write integration tests** (`tests/test_pagination_integration.py`):
   - Test open command with short paper (no pagination)
   - Test open command with long paper (multiple scrolls)
   - Mock getch() to simulate space and exit keys
   - Verify markdown rendering preserved
   - Verify state machine transitions

4. **Integrate into process_open_command**:
   - Replace lines 1005-1031 in chat.py with TextPaginator call
   - Remove Prompt.ask() usage
   - Remove page-based logic
   - Preserve panel formatting and markdown rendering
   - Ensure state transitions unchanged

#### Phase 4: Testing & Documentation
1. **Run all existing tests immediately**:
   - Execute `pytest` to ensure no regressions
   - Fix any failures before proceeding

2. **Run new tests**:
   - Verify all pagination tests pass
   - Check for flaky tests (getch mocking)
   - Ensure integration tests pass

3. **Manual testing checklist**:
   - Test on terminal sizes: 20, 40, 80 lines
   - Test list command with 0, 5, 50 papers
   - Test open command with short/long content
   - Test space key scrolling
   - Test exit with various keys (q, enter, escape, any letter)
   - Test Ctrl+C interruption
   - Test auto-exit at end of content

4. **Update documentation**:
   - Complete Implementation section in this design document
   - Update tests/TESTING_SUMMARY.md with new test coverage
   - Mark design status as "implemented"

### Testing Strategy

#### Unit Tests (tests/test_pagination.py)
**Components to test**:
1. getch() function (12 tests):
   - Character input (mocked termios)
   - Special characters: space, escape, newline
   - Ctrl+C raises KeyboardInterrupt
   - Non-Unix platform fallback with warning

2. Paginator base class (8 tests):
   - calculate_initial_size() with heights: 10, 20, 50, 100
   - calculate_scroll_size() with same heights
   - Minimum sizes for small terminals (< 20 lines)
   - Edge case: height = 0

3. TablePaginator (15 tests):
   - paginate_papers() with 0, 1, 5, 50, 100 papers
   - Row counting never breaks mid-row
   - Table overhead calculations
   - Space key adds content (mocked getch)
   - Other keys exit (mocked getch)
   - Auto-exit at end of content
   - Pagination prompt display

4. TextPaginator (12 tests):
   - paginate_lines() with 0, 10, 100, 500 lines
   - Line counting for scrolling
   - Text overhead calculations
   - Markdown rendering preserved
   - Space key adds content (mocked getch)
   - Other keys exit (mocked getch)
   - Auto-exit at end of content

**Total unit tests**: ~47 tests

#### Integration Tests (tests/test_pagination_integration.py)
**E2E workflows**:
1. List command pagination (8 tests):
   - List 0 papers (no pagination prompt)
   - List 10 papers (single page, no pagination)
   - List 50 papers with space scrolling
   - List with exit on first prompt
   - List with Ctrl+C interruption
   - Verify state machine transitions (initial → select-view)
   - Verify query_set preservation
   - Verify next steps display

2. Open command pagination (7 tests):
   - Open short paper (no pagination)
   - Open long paper with space scrolling
   - Open with exit on first prompt
   - Open with Ctrl+C interruption
   - Verify markdown rendering
   - Verify panel formatting
   - Verify state transitions (select-view → summarized)

**Total integration tests**: ~15 tests

#### Testability Considerations
- **API-level testing**: All pagination classes testable without terminal I/O
- **Mock getch()**: Use unittest.mock to simulate keypresses
- **Mock console.height**: Use fixtures to control terminal size
- **Isolation**: Tests don't depend on actual terminal or user input
- **No terminal I/O simulation**: Direct API calls to paginate_papers() and paginate_lines()

### Risk Areas

1. **Platform compatibility**:
   - termios only available on Unix/macOS
   - **Mitigation**: Graceful fallback with warning if getch() fails, fall back to line-buffered Prompt.ask()

2. **Terminal size detection**:
   - console.height may not work in all environments
   - **Mitigation**: Use sensible defaults (50 lines) if console.height returns 0 or None

3. **Breaking existing tests**:
   - Changes to process_list_command and process_open_command might affect other tests
   - **Mitigation**: Run full test suite immediately after integration, ensure all tests pass before completion

4. **User experience with very small terminals**:
   - Terminals < 20 lines might have poor UX
   - **Mitigation**: Use minimum values (10 lines initial, 5 lines scroll) for small terminals

5. **Cumulative display with large content**:
   - Displaying 1000+ rows might overwhelm terminal scrollback
   - **Mitigation**: This is acceptable - users can always exit early with any key

6. **Testing getch() reliably**:
   - Mocking termios might be fragile
   - **Mitigation**: Use unittest.mock with careful mocking of termios.tcgetattr, tcsetattr, tty.setraw

### Documentation Updates

**README.md**:
- Update list command description: "Press SPACE to scroll, any other key to exit"
- Update open command description: "Press SPACE to scroll, any other key to exit"
- Mention single-keypress pagination (no Enter required)

**CLAUDE.md**:
- Add pagination.py to architecture overview
- Document terminal size detection approach
- Add pagination to Component list with brief description

**tests/TESTING_SUMMARY.md**:
- Add pagination section under Core Components
- Document 47 unit tests and 15 integration tests
- Add to E2E flows: "Flow 8: Pagination Workflows"

**devlog.md**:
- Add concise entry (10-15 lines):
  - What: Replaced line-buffered pagination with single-keypress pagination
  - Why: Improve UX - no Enter key required, responsive to terminal size
  - How: New pagination.py module with getch(), TablePaginator, TextPaginator
  - Testing: 47 unit tests + 15 integration tests
  - Outcome: Seamless space-to-scroll, any-key-to-exit behavior

## Testing Considerations

### Unit Tests

1. **`getch()` function**:
   - Test character input (mocked)
   - Test Ctrl+C handling
   - Test special characters (space, escape, etc.)

2. **Size calculations**:
   - Test `calculate_initial_size()` with different terminal heights
   - Test `calculate_scroll_size()` with different heights
   - Test edge cases (very small terminals)

### Integration Tests

1. **TablePaginator**:
   - Test with different numbers of papers (0, 1, many)
   - Test that rows aren't broken
   - Test end-of-content auto-exit
   - Test space key adds content
   - Test other keys exit

2. **TextPaginator**:
   - Test with different content lengths
   - Test markdown rendering preservation
   - Test end-of-content auto-exit
   - Test space key adds content
   - Test other keys exit

### Manual Testing

1. Test on different terminal sizes (small, medium, large)
2. Test space key scrolling
3. Test exit keys (q, escape, enter, etc.)
4. Test Ctrl+C interruption
5. Test with list command
6. Test with open command

## Edge Cases

1. **Content shorter than one page**: Display all, no pagination prompt
2. **Very small terminal** (< 20 lines): Use minimum sensible values
3. **Content ends mid-scroll**: Show remaining content, auto-exit
4. **No papers/content**: Display appropriate message, no pagination
5. **Terminal resize during pagination**: Use initial terminal size (don't recalculate mid-session)

## Non-Goals

1. Bi-directional scrolling (up/down arrow keys) - keep it simple
2. Jump-to-page functionality
3. Search within paginated content
4. Windows support (termios not available)
5. Color-coded pagination prompts (keep consistent with current style)

## Future Enhancements

1. Use pagination for research results
2. Use pagination for long summaries
3. Add configuration for initial_fill and scroll_fill percentages
4. Support for Windows (using msvcrt)
5. Add 'q' as explicit quit key (in addition to any-other-key)

## Implementation

**Status**: ✅ Completed
**Implemented**: October 21, 2025
**Total Tests**: 38 (33 unit + 5 integration)

### What Was Built

#### Core Module: `pagination.py`

**1. `getch()` Function**
- Single-character input using `termios` and `tty` modules (Unix/macOS)
- Handles Ctrl+C by raising `KeyboardInterrupt`
- Restores terminal settings in `finally` block
- Raises `NotImplementedError` on non-Unix platforms with warning message

**2. `Paginator` Base Class**
- Terminal height detection via `console.height` from Rich
- `calculate_initial_size()`: Returns 80% of terminal height
- `calculate_scroll_size()`: Returns 45% of terminal height
- Configurable fill ratios via constructor parameters

**3. `TablePaginator` Class**
- Table overhead constant: 7 lines (title + header + borders + prompt)
- Row-aware pagination - each paper is exactly 1 terminal line
- All table columns use `no_wrap=True` to prevent line wrapping
- Title and author fields truncated to fit column widths (55 and 25 chars)
- Displays: #, Paper ID, Title, Authors, Published date
- Graceful error handling for `termios.error` and other exceptions

**4. `TextPaginator` Class**
- Text overhead constant: 5 lines (panel borders + title + prompt)
- Line-based pagination for markdown content
- Preserves markdown rendering in Rich Panel
- Optional panel title parameter

### Integration Points

**List Command** (`chat.py` line 472-500):
```python
from .pagination import TablePaginator

paginator = TablePaginator(self.console)
paginator.paginate_papers(papers)
```

**Open Command** (`chat.py` line 933-943):
```python
from .pagination import TextPaginator

lines = content.split('\n')
paginator = TextPaginator(self.console)
paginator.paginate_lines(lines, title=paper.title)
```

### Key Decisions

**1. Exception Handling Strategy**
- **Challenge**: `termios.error` is not a subclass of `OSError`, causing unhandled exceptions when stdin isn't a proper terminal
- **Solution**: Catch broad `Exception` (excluding `KeyboardInterrupt`) and display fallback message
- **Fallback Behavior**: Display all remaining content with warning message

**2. Table Row Wrapping Prevention**
- **Challenge**: Long titles/authors caused rows to span multiple terminal lines, breaking row count calculations
- **Solution**: Add `no_wrap=True` to all table columns and truncate text to fit
- **Result**: Each paper is guaranteed to be exactly 1 terminal line

**3. Terminal Height Detection**
- **Approach**: Use `console.height` from Rich Console (already instantiated in chat interface)
- **Benefits**: Accurate terminal size, handles terminal resizing
- **Note**: Terminal size is captured at pagination start, not updated during scrolling

**4. Debug Output**
- **Added**: Commented debug line showing terminal calculations (line 153)
- **Purpose**: Help troubleshoot pagination issues without modifying code
- **Usage**: Uncomment to see: terminal height, overhead, rows per page, total papers

### Challenges and Solutions

**Challenge 1: Testing Terminal I/O**
- **Problem**: `getch()` requires actual terminal, subprocess tests don't have access
- **Solution**: Mock `termios`, `tty`, and `sys.stdin` in unit tests
- **Result**: 38 tests all passing with full coverage of pagination logic

**Challenge 2: Non-Interactive Environments**
- **Problem**: CI/CD, piped input, or redirected output causes `termios.error: (19, 'Operation not supported by device')`
- **Solution**: Catch exception and gracefully display all remaining content with informative message
- **Result**: Pagination degrades gracefully instead of crashing

**Challenge 3: Row-Aware Scrolling**
- **Problem**: Design required "no mid-row breaks" but text wrapping caused unpredictable row heights
- **Solution**: Force all columns to `no_wrap=True` and pre-truncate text to fit column widths
- **Result**: Predictable row count = paper count (1:1 mapping)

**Challenge 4: User Testing Required**
- **Problem**: Subprocess-based testing couldn't verify actual terminal behavior
- **Solution**: Manual testing by user in real terminal session
- **Result**: User confirmed pagination working correctly

### Test Coverage

**Unit Tests** (33 tests in `test_pagination.py`):
- `getch()`: 7 tests
- `Paginator` base class: 8 tests
- `TablePaginator`: 9 tests
- `TextPaginator`: 9 tests

**Integration Tests** (5 tests in `test_pagination_integration.py`):
- List command with pagination: 4 tests
- Keyboard interrupt handling: 1 test

**Test Strategy**:
- Mock `termios.tcgetattr`, `termios.tcsetattr`, `tty.setraw`, `sys.stdin`
- Mock `getch()` to return specific characters for testing space/exit keys
- Test terminal size calculations with various heights (10, 20, 50, 100 lines)
- Test edge cases: zero papers, very small terminals, auto-exit at end

### Files Modified

**New Files** (3):
1. `src/my_research_assistant/pagination.py` (301 lines)
2. `tests/test_pagination.py` (18,497 bytes)
3. `tests/test_pagination_integration.py` (8,588 bytes)

**Modified Files** (1):
1. `src/my_research_assistant/chat.py`:
   - `process_list_command()`: Replaced manual pagination loop with `TablePaginator`
   - `process_open_command()`: Replaced manual pagination loop with `TextPaginator`

### Performance Notes

- Terminal height detection: O(1) - single Rich Console property access
- Table rendering: O(n) where n = papers displayed so far (Rich handles efficiently)
- Memory: Cumulative rendering stores all content in terminal buffer (not in Python)
- CPU: Minimal - most work done by Rich library for table rendering

### Future Enhancements

**Potential Improvements** (not implemented):
1. Bi-directional scrolling (up/down arrow keys)
2. Jump-to-page functionality
3. 'q' as explicit quit key
4. Windows support using `msvcrt` module
5. Configurable initial_fill and scroll_fill percentages
6. Use pagination for research results and long summaries

**Why Not Implemented**:
- Keep it simple - SPACE vs any-other-key is intuitive
- Focus on Unix/macOS (primary development platform)
- Avoid feature creep - solve the immediate usability issue

### Lessons Learned

1. **Mock thoughtfully**: Proper mocking of termios required understanding internal implementation
2. **Graceful degradation**: Better to show all content than crash on terminal errors
3. **User testing essential**: Subprocess tests couldn't validate actual terminal behavior
4. **Rich API helpful**: `console.height` made terminal detection trivial
5. **Exception hierarchy matters**: `termios.error` not being `OSError` caught us by surprise
