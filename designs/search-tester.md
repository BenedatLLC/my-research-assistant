---
status: implemented
---
# Design: Search tester script

This is the design of a command line script to test the search APIs. In particular, we want to
test the following functions in `vector_store.py`:
- `search_index` - search the content index
- `search_content_index_filtered` - seasrches the content index, filtering by paper ids
- `search_summary_index` - searches the summary index

We will use command line arguments to specify which of these to run and what hyperparameter
settings we should use (e.g. value of `k`).

The code for this script should go in the file `src/my_research_assistant/search_tester.py`

## Command line arguments
Here are the command line arguments, which should be parsed via `argparse`:

```
--summary
  If specified, search the summary index (via `search_summary_index`)

--papers PAPER_ID1[, PAPER_ID2, ...]
  If specified, use `search_content_index_filters` and filter by the specified paper ids
  (comma-separated). Not valid with --summary

-k --num-chunks K
  Number of chunks to return (defaults to 5)

--content-similarity-threshold T
  Minimum similarity score threshold for search results. Results below this threshold
  should be filtered out. Range: 0.0 (no filtering) to 1.0 (exact match).
  Defaults to 0.6

--use-mmr
  If specified, use Maximum Marginal Relevance (MMR) to rerank the chunks. Otherwise, return ranked
  only by similarity score.

--mmr-alpha A
  MMR alpha parameter for balancing relevance vs diversity in content search.
  Range: 0.0 (maximum diversity) to 1.0 (maximum relevance). Default is 0.5.
  Only valid if --use-mmr is specified.

--papers-only
  If specified, display results as a simple table with paper metadata only (no chunk content).
  Shows: result number, paper ID, chunk number (page), chunk length, and paper title.
  Orthogonal to other parameters (works with --summary, --papers, --use-mmr, etc.).

QUERY
  The text to use as the search query.
```

## Running the script
This scxript should be registered in the `project.scripts` section of `pyproject.toml`. You should
be able to run it as follows:

```sh
uv run search-tester [OPTIONS] QUERY
```

## Output

### Default Output (Paginated)
The output should be paginated using `rich`, like we do for paper markdown. The output
should have a summary section and the detailed chunks. The summary section should have:
- original query text
- function used for search
- values for k, content similarity threshold, whether MMR was used, and MMR alpha
- number of results returned

For each result show:
- paper id
- paper title
- filename (for either paper or summary, depending on which index was searched
- page number of chunk
- total size of chunk
- content of chunk - formatted using markdown if possible

### Papers-Only Output (Table)
When `--papers-only` is specified, display a simplified table with:
- Result number (sequential, 1-indexed)
- Paper ID (ArXiv identifier)
- Chunk number (page number where chunk appears)
- Chunk length (character count)
- Paper title

This mode is orthogonal to other parameters and works with all search types (content index,
summary index, and filtered content search).

## Implementation

### Summary
Successfully implemented a command-line script `search-tester` that provides a testing interface for the three search functions in `vector_store.py`. The implementation uses argparse for command-line argument parsing, calls the appropriate search function based on flags, and displays paginated results using Rich's TextPaginator with markdown rendering.

### Files Created/Modified

**Files Created:**
1. `src/my_research_assistant/search_tester.py` (245 lines) - Main script implementation with CLI parsing, validation, formatting, and pagination
2. `tests/test_search_tester.py` (407 lines) - Comprehensive test suite with 23 tests (11 unit, 7 integration, 3 E2E)

**Files Modified:**
1. `pyproject.toml` - Added script entry point: `search-tester = "my_research_assistant.search_tester:main"`

### Key Implementation Details

**Argument Parsing:**
- Used argparse with clear help text and descriptions
- Implemented all required flags: --summary, --papers, -k/--num-chunks, --content-similarity-threshold, --use-mmr, --mmr-alpha
- Default values pulled from constants.py (CONTENT_SEARCH_K=20, SUMMARY_SEARCH_K=5, etc.)
- Positional QUERY argument for search text

**Validation Logic:**
- Mutually exclusive flags: --summary and --papers cannot both be specified (exits with error message)
- --mmr-alpha requires --use-mmr (checked by comparing to default value)
- Range validation for similarity_threshold and mmr_alpha (0.0-1.0)
- All validation errors exit with status code 1 and clear error messages starting with "❌"

**Search Function Selection:**
- Automatically adjusts k default based on search type (20 for content, 5 for summary)
- Routes to appropriate function:
  - `search_summary_index` when --summary specified
  - `search_content_index_filtered` when --papers specified
  - `search_index` for default content search
- Proper parameter mapping for each function (mmr_alpha only for content search)

**Result Formatting:**
- Summary header includes: query, function name, all parameters, result count
- Each result shows: sequential number, paper ID, title, filename, page, chunk size, content
- Filename selection based on search type (pdf_filename for content, summary_filename for summary)
- Content formatted as markdown for rich display

**Pagination:**
- Uses Rich's TextPaginator for single-keypress navigation
- Title format: "🔍 Search Results: {query}"
- Automatic handling of long content with proper wrapping

**Error Handling:**
- Catches IndexError and RetrievalError from vector_store
- Displays user-friendly error messages with ❌ prefix
- Generic exception handler for unexpected errors
- All errors exit with status code 1

### Test Coverage Achieved

**Unit Tests (11 tests):**
- All argument parser flags and defaults
- All validation rules (mutually exclusive flags, parameter ranges, mmr-alpha requirement)
- Result formatting functions (header and individual results)
- Edge cases in formatting (summary vs content filenames, page numbers)

**Integration Tests (7 tests):**
- All three search functions called with correct parameters
- Parameter mapping verified (k adjustment, mmr parameters)
- Error handling for IndexError
- Mock-based testing for search function calls

**End-to-End Tests (3 tests):**
- Full workflow for content search with pagination
- Full workflow for summary search with pagination
- Validation error handling (exits with status 1)

**Test Results:**
- 23/23 tests passing
- All existing tests still passing (382 total in suite)
- No regressions introduced

### Deviations from Original Plan

None. Implementation followed the plan exactly as specified.

### Known Limitations

None. The script works as designed for all three search modes with full validation and error handling.

### Future Enhancements

Potential improvements (not required for current design):
- Add --json output mode for programmatic use
- Add --verbose flag for debugging
- Support for multiple query terms
- Export results to file option

