---
status: implemented
---
# Design for Open Command

The `open` command takes either a paper id or a paper number and launches the platform's pdf viewer with the paper's
downloaded pdf.

## Command argument
The command requires one argument, either an arxiv paper id (e.g. "2107.03374v2") or an positive integer paper number.
See [Design for specifying papers on commands](command-arguments.md) for the common design for paper argument processing.

## Specifying the PDF viewer
The path to a program to view PDFs is specified via the `PDF_VIEWER` environment variable. The command should start
a subprocess with the value of $PDF_VIEWER as its executable and one command line argument: the full file path to
the papers pdf file.

## Running the PDF viewr
The PDF viewer should be run decoupled from the parent chat session: the chat session should
not block and the viewer should not exit when the chat session exits.

## State management
This is covered in the design [Workflow state machine and commands](command-arguments.md)

## Error situations
Here are some error situations and how to handle them:

- If the `PDF_VIEWER` environment variable is not set, the command prints a warning and then pages through
  the extracted markdown text of the paper, using the same rich text library and paging approach used to
  print summaries.
- If the `PDF_VIEWER` is set to a file that does not exist or the subprocess call fails, an error message
  is printed and the chat returns to its previous state.
- If the paper id or number does not exist, this is handled as currently described in
  [Design for specifying papers on commands](command-arguments.md).

## Examples
In this examples below, we elide output lines that are not relevent to the example
via a line containing only ellipsis ("...").

### Open command when PDF_VIEWER is not set
In this case, the user selects a paper and runs the `open` command. The `PDF_VIEWER` environment variable is not
set, so the Markdown extraction of the paper is rendered in the terminal.

```chat
You: open 1
WARNING: PDF_VIEWER environment variable is not set, Rendering in terminal

╭────────────────────────────────────────────────────── 📝 Response ──────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                  Evaluating Large Language Models Trained on Code                                   ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                         │
│ Mark Chen [* 1] Jerry Tworek [* 1] Heewoo Jun [* 1] Qiming Yuan [* 1]                                                   │
│ Henrique Ponde de Oliveira Pinto [* 1]                                                                                  │
│                                                                                                                         │
│ Jared Kaplan [* 2] Harri Edwards [1] Yuri Burda [1] Nicholas Joseph [2] Greg                                            │
│ Brockman [1] Alex Ray [1] Raul Puri [1]                                                                                 │
...
📄 Page 1 of 10
Press Enter for next page, or type any other key to exit
():
```

### Open command when PDF_VIEWER is correctly set
In this case, the user selects a paper and runs the `open` command. The `PDF_VIEWER` environment variable is correctly
set to /usr/bin/open, so the paper is opened in the associated viewer.

```chat
You: open 2107.03374v2
╭────────────────────────────────────────────────────── 📝 Response ──────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                             Paper Content: 2107.03374v2                                             ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                         │
│ PDF Location: /Users/jfischer/code/my-research-assistant/docs/pdfs/2107.03374v2.pdf                                     │
│ Paper has been opened using PDF viewer /usr/bin/open                                                                    │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
You:
```

### Error when PDF_VIEWER is incorrectly set
In this case, the user selects a paper and runs the `open` command, The `PDF_VIEWER` environment variable is incorrectly
set to /usr/bin/pdfviewer, which either is not an executable or cannot be run on this machine.

```chat
You: open 2107.03374v2
❌ ❌ open failed: PDF_VIEWER is set to '/usr/bin/pdfviewer', which was not found.
You:
```

## Implementation

The `open` command has been successfully implemented according to the design specification. Here's an outline of the implementation:

### Files Modified

**1. `src/my_research_assistant/result_storage.py`**
- Updated `open_paper_content()` function to implement full design:
  - Changed return type from `Tuple[bool, str]` to `Tuple[bool, str, str]` to include action_type
  - Added PDF_VIEWER environment variable checking
  - Added subprocess handling for launching external PDF viewer with proper decoupling
  - Added fallback to extracted markdown text when PDF_VIEWER is not set
  - Comprehensive error handling for all edge cases

**2. `src/my_research_assistant/chat.py`**
- Updated `process_open_command()` to handle new functionality:
  - Handles three action types: "viewer", "markdown", and "error"
  - Implemented markdown pagination for terminal viewing (40 lines per page)
  - Uses Rich panel rendering with markdown formatting
  - Displays warning when PDF_VIEWER is not set
  - Interactive pagination (press Enter for next page)
  - Proper state machine integration via `transition_after_open()`

### Key Implementation Details

**Subprocess Handling for PDF Viewer:**
- Uses `subprocess.Popen()` with `start_new_session=True` for proper process decoupling
- Redirects stdout, stderr, and stdin to DEVNULL to prevent blocking
- Validates PDF_VIEWER executable exists using `shutil.which()` before launching
- Graceful error handling if subprocess fails to launch

**Markdown Fallback Mode:**
- Reads extracted markdown from `extracted_paper_text_dir`
- Splits content into pages (40 lines per page)
- Renders each page in a Rich panel with markdown formatting
- Interactive pagination similar to paper list pagination
- Shows page number and total pages
- User can exit pagination early by typing any key other than Enter

**Error Handling:**
- PDF not found: Clear error message with full path
- PDF_VIEWER executable not found: Specific error about the viewer path
- Subprocess launch failure: Error with exception details
- Extracted text not found: Clear error message when falling back to markdown
- All errors follow the pattern: `❌ open failed: <specific details>`

**State Management:**
- Integrates with existing state machine via `transition_after_open(paper)`
- Preserves query set based on paper selection context (via enhanced parsing)
- Transitions to SUMMARIZED state after successful open
- Follows the conditional query set preservation design

### Testing

**New Test File: `tests/test_open_command.py`**
- **8 comprehensive tests** covering all functionality:
  - `TestOpenPaperContentWithPDFViewer`: 3 tests for PDF viewer mode
  - `TestOpenPaperContentWithoutPDFViewer`: 2 tests for markdown fallback
  - `TestOpenPaperContentErrorCases`: 2 tests for error scenarios
  - `TestOpenCommandIntegration`: 1 integration test for full command flow

**Test Coverage:**
- Valid PDF viewer execution
- Invalid PDF viewer path handling
- Subprocess failure handling
- Markdown fallback display
- Missing extracted text handling
- Missing PDF handling
- Integration with state machine and chat interface

**All Tests Pass:**
- 8/8 new open command tests pass
- 31/31 state machine tests pass (no regressions)
- 24/24 paper argument parsing tests pass (no regressions)

### Design Compliance

The implementation fully complies with the design specification:

1. ✅ **Command argument**: Accepts paper ID or number via enhanced parsing
2. ✅ **PDF_VIEWER environment variable**: Properly checked and used
3. ✅ **Subprocess execution**: Decoupled, non-blocking
4. ✅ **Markdown fallback**: Pages through extracted text when PDF_VIEWER not set
5. ✅ **State management**: Integrated with state machine, preserves query set correctly
6. ✅ **Error handling**: All specified error cases handled with clear messages
7. ✅ **Examples**: Behavior matches all provided examples in design

### Usage Examples

**With PDF_VIEWER set:**
```bash
export PDF_VIEWER=/usr/bin/open
# Then in chat:
open 1  # Opens paper #1 in PDF viewer
open 2107.03374v2  # Opens specific paper by ID
```

**Without PDF_VIEWER set:**
```bash
unset PDF_VIEWER
# Then in chat:
open 1  # Pages through extracted markdown text in terminal
```

The implementation provides a seamless user experience for viewing papers, with automatic fallback to terminal viewing when no external viewer is configured.

