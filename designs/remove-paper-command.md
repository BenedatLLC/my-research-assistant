---
status: implemented
---
# Design for Remove Paper Command

The `remove-paper` command takes either a paper id or a paper number, confirms the choice of paper, and
removes it from the local store. This is useful when the wrong paper is downloaded or a paper has been
superceeded by a newer version.

## Command argument
The command requires one argument, either an arxiv paper id (e.g. "2107.03374v2") or an positive integer paper number.
See [Design for specifying papers on commands](command-arguments.md) for the common design for paper argument processing.
There is one important exception to the design for paper arguments: if the user specify a paper that has multiple versions without a version (e.g. "2107.03374"), never make assumptions about the version, just
tell the user to be more specific and list the versions of that paper that have been downloaded.

## Confirmation
When asking the user for confirmation, list the paper id, paper title, and publication date. If the user
does not confirm the paper deletion, go back to the current state without doing anything.

## Deletion
See the [File store design](file-store.md) for details on the file layout. In general,
only delete content specific to the requested paper. Here's how to handle each sub-directory
under `$DOC_HOME`, assuming the arxiv id of the paper is PAPER_ID:

- pdfs/                 - the downloaded paper is here as PAPER_ID.pdf
- paper_metadata/       - this contains json files for the paper metadata obtained from Arxiv.
                          The file for the paper will be PAPER_ID.json.
- extracted_paper_text/ - this is the markdown extracted from the paper PDF, using the filename
                          PAPER_ID.md.
- index/                - this is the semantic search index created by LlamaIndex. We want to remove any
                          chunks identified by this paper from both the content and summary indices.
                          Entries for other papers should be left untouched.
- summaries/            - this contains the llm-generated summaries of papers in markdown, using the
                          name PAPER_ID.md.
- notes/                - this directory main contain human-generated notes. Since they are human
                          generated always ask for additional confirmation before deleting any files
                          from this directory. The file, if present would be, PAPER_ID.md.
- results/              - this directory should not be touched, as the content is not paper-specific

The command should print the changes it makes as it runs. If state for a paper does not exist,
the command should proceed, indicating that no file was present.

## State management
This command can be run in any state. A paper index number can only be specified if `last_query_set`
has papers. This is covered in the design [Workflow state machine and commands](command-arguments.md).
Removing a paper should not change the state, but may update state variables. Specifically:

- If the deleted paper is in `last_query_set`, it should be removed from that set
- If `selected_paper` is the paper that was deleted, it should be set to None

## Examples
In this examples below, we elide output lines that are not relevent to the example
via a line containing only ellipsis ("...").

### Deletion request by paper id

```chat
You: remove-paper 2506.02153v1
🗑️ Removing paper 2506.02153v1 
   title:     Small Language Models are the Future of Agentic AI
   published: 2025-06-02
⚠️ This will delete all indexes from PDFs, extracted content, summaries, and notes.
Are you sure you want to continue? [y/n]: y
❌ Removed downloaded paper '/Users/jfischer/code/my-research-assistant/docs/pdfs/2402.14860v4.pdf'
❌ Removed 22 chunks from the content index.
❌ Removed extracted paper text '/Users/jfischer/code/my-research-assistant/docs/extracted_paper_text/2402.14860v4.md'
❌ Removed summary '/Users/jfischer/code/my-research-assistant/docs/summaries/2402.14860v4.md'
❌ Removed 1 chunks from the summary index.
No paper notes found at '/Users/jfischer/code/my-research-assistant/docs/notes/2402.14860v4.md'.
Removal of content for paper 2506.02153v1 completed successfully.
You:
```

### Deletion request by paper index with notes
```chat
You: list
...
You: remove-paper 15
🗑️ Removing paper 2506.02153v1 
   title:     Small Language Models are the Future of Agentic AI
   published: 2025-06-02
⚠️ This will delete all indexes from PDFs, extracted content, summaries, and notes.
Are you sure you want to continue? [y/n]: y
❌ Removed downloaded paper '/Users/jfischer/code/my-research-assistant/docs/pdfs/2402.14860v4.pdf'
❌ Removed 22 chunks from the content index.
❌ Removed extracted paper text '/Users/jfischer/code/my-research-assistant/docs/extracted_paper_text/2402.14860v4.md'
❌ Removed summary '/Users/jfischer/code/my-research-assistant/docs/summaries/2402.14860v4.md'
❌ Removed 1 chunks from the summary index.
Are you sure you want to delete the notes file '/Users/jfischer/code/my-research-assistant/docs/notes/2402.14860v4.md' [y/n]: y
❌ Removed paper notes found at '/Users/jfischer/code/my-research-assistant/docs/notes/2402.14860v4.md'.
Removal of content for paper 2506.02153v1 completed successfully.
You:
```

### Ambiguous deletion request
```chat
You: remove-paper 2506.02153
❌ Ambiguous removal request: there are multiple versions of that paper in the store: 2506.02153v1 and 2506.02153v2
Skipping removal.
You:
```

## Implementation

The `remove-paper` command has been successfully implemented according to the design specification. Here's an outline of the implementation:

### Files Created

**1. `src/my_research_assistant/paper_removal.py`** (NEW)

This new module provides the core paper removal functionality:

- **`remove_paper_from_indexes(paper_id, file_locations)`** - Removes all chunks associated with a paper from both the content and summary ChromaDB indexes using the `delete()` method with `where={"paper_id": paper_id}` metadata filters. Returns a tuple of (content_chunks_removed, summary_chunks_removed) for user feedback.

- **`find_matching_papers(paper_ref, file_locations)`** - Finds all downloaded papers matching a paper reference, handling both exact matches (with version) and prefix matches (without version). This is crucial for detecting ambiguous version-less references.

- **`remove_paper(paper_id, file_locations, confirm_callback, notes_confirm_callback)`** - Orchestrates the complete paper removal process including:
  - Ambiguous version detection and error reporting
  - Initial confirmation prompt with paper details
  - Deletion of PDF, metadata, extracted text, summary files
  - Removal from both vector indexes
  - Separate confirmation and deletion of notes (if present)
  - Detailed status reporting for each deletion step
  - Graceful handling of missing files (continues with partial deletion)

### Files Modified

**1. `src/my_research_assistant/state_machine.py`**
- Added `"remove-paper <number|id>"` to the global commands list in `get_valid_commands()`
- The command is now available in all states as designed

**2. `src/my_research_assistant/chat.py`**
- Added `process_remove_paper_command(paper_ref)` method that:
  - Uses `find_matching_papers()` to check for ambiguous references
  - Uses `parse_paper_argument_enhanced()` to resolve paper references
  - Defines confirmation callbacks that use console input
  - Calls `remove_paper()` with the callbacks
  - Updates state variables after successful removal:
    - Removes paper from `last_query_set` if present
    - Clears `selected_paper` if it matches the deleted paper
  - Maintains current state (no state transition)
- Added command routing for `remove-paper` in the main command processing loop
- Added `remove-paper` to global commands list for validation
- Updated help display and welcome message to include the new command

### Tests Created

**1. `tests/test_paper_removal.py`** (NEW)

Comprehensive test suite with 14 tests covering:

- **TestRemovePaperFromIndexes** (4 tests):
  - Removing from non-existent indexes
  - Removing from content index only
  - Removing from both indexes
  - Handling collection access errors gracefully

- **TestFindMatchingPapers** (4 tests):
  - Exact paper ID matches
  - Prefix matches with multiple versions
  - No matches found
  - Single version matches with prefix

- **TestRemovePaper** (6 tests):
  - Paper not found handling
  - Ambiguous version detection
  - User cancellation handling
  - Complete successful removal of all files
  - Partial removal when only some files exist
  - Notes preservation when user declines deletion

All tests use proper mocking and temporary directories to avoid affecting real data.

### Key Implementation Details

**ChromaDB Index Deletion:**
- Uses `chromadb.PersistentClient` to connect to existing indexes
- Calls `collection.get(where={"paper_id": paper_id})` to count chunks before deletion
- Calls `collection.delete(where={"paper_id": paper_id})` to remove all matching chunks
- Handles missing indexes gracefully (no error if index doesn't exist)
- Reports exact number of chunks removed for user feedback

**Ambiguous Version Handling:**
- When user provides paper ID without version (e.g., "2107.03374")
- Searches all downloaded papers for prefix matches
- If multiple versions found (e.g., "2107.03374v1", "2107.03374v2"):
  - Returns error message listing all matching versions
  - Requires user to specify exact version
  - Does not attempt to guess which version to delete

**Confirmation Prompts:**
- First confirmation shows paper ID, title, and publication date
- Warns that deletion affects PDFs, extracted content, summaries, and notes
- If notes file exists, requests separate confirmation before deletion
- Both confirmations use simple `input()` calls (via callbacks)
- User can decline notes deletion while proceeding with other deletions

**State Variable Updates:**
- After successful removal:
  - Removes paper_id from `last_query_set` if present
  - Re-sorts `last_query_set` to maintain consistency
  - Clears `selected_paper` if it matches the deleted paper
- Current state is maintained (no transition)
- This ensures state remains consistent even after paper removal

**Error Handling:**
- Paper not found: Clear error message
- Ambiguous versions: Lists all matching versions
- Missing files: Reports "not found" and continues with other deletions
- Index errors: Printed warning, continues with deletion
- Metadata loading errors: Returns error message with details
- All errors are non-fatal when possible (partial deletion proceeds)

### Test Results

All tests pass successfully:
- **14/14** new paper removal tests pass
- **31/31** state machine tests pass (no regressions)
- **24/24** paper argument parsing tests pass (no regressions)
- **11/11** chat interface tests pass (no regressions)

### Design Compliance

The implementation fully complies with the design specification:

1. ✅ **Command argument**: Accepts paper ID or number via enhanced parsing
2. ✅ **Ambiguous version handling**: Detects and reports multiple versions, requires explicit version
3. ✅ **Confirmation**: Shows paper details and requires user confirmation
4. ✅ **Deletion**: Removes all paper-specific files as specified
5. ✅ **Index removal**: Uses ChromaDB delete() with metadata filters for both indexes
6. ✅ **Notes handling**: Separate confirmation for notes deletion
7. ✅ **Partial deletion**: Continues with available files, reports missing files
8. ✅ **State management**: Updates state variables, maintains current state
9. ✅ **Error messages**: Clear, helpful error messages for all edge cases
10. ✅ **Examples**: Behavior matches all provided examples in design

### Usage Examples

**Remove by paper ID:**
```bash
remove-paper 2506.02153v1
```

**Remove by paper number (after list or search):**
```bash
list
remove-paper 15
```

**Handle ambiguous version:**
```bash
remove-paper 2506.02153
# Error: Ambiguous removal request: there are multiple versions...
# User must then specify exact version:
remove-paper 2506.02153v1
```

The implementation provides a safe, user-friendly way to remove papers from the store with appropriate confirmations and detailed feedback about what was deleted.
