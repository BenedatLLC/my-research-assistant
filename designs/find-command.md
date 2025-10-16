---
status: draft
---
# Design: Enhanced Find Command with Web Search

_Enhance the `find` command to use web search as the primary discovery method, with configurable fallback to ArXiv API search._

## Overview

The current `find` command uses the ArXiv API's keyword search to discover papers. However, as of October 2025, the ArXiv API keyword search is returning 0 results for all text-based queries, while ID-based lookups continue to work. This design enhances the `find` command to use web search (via `site:arxiv.org` queries) as the primary discovery method, providing:

- **More reliable search** - Web search finds papers even when ArXiv API keyword search is broken
- **Higher quality results** - Web search provides better relevance matching, not just exact title matches
- **Graceful degradation** - Configurable fallback to ArXiv API when web search is unavailable or disabled
- **Consistent behavior** - Results sorted by paper ID, consistent with `list` command and state variables

The enhancement maintains backward compatibility while providing a more robust search experience.

## User Stories / Use Cases

1. **Use Case 1**: User wants to find papers on a specific topic using the default web search
   - User action: `find transformer attention mechanisms`
   - System response:
     - Performs web search with `site:arxiv.org transformer attention mechanisms`
     - Extracts ArXiv IDs from search results
     - Fetches metadata via ArXiv API for discovered papers
     - Applies semantic reranking
     - Sorts results by paper ID
     - Displays top 5 papers
   - Outcome: User sees relevant papers sorted by paper ID, even when ArXiv API keyword search is broken

2. **Use Case 2**: User wants to find a paper by exact title
   - User action: `find Evaluating Large Language Models Trained on Code`
   - System response: Web search finds exact title match, returns it in the results
   - Outcome: User finds the specific paper they were looking for

3. **Use Case 3**: User wants to use ArXiv API search only (e.g., no web search quota)
   - User action: Sets `USE_WEB_SEARCH=no` environment variable, then runs `find machine learning`
   - System response: Uses ArXiv API keyword search exclusively (legacy behavior)
   - Outcome: Search behaves as it did before, useful when ArXiv API is working or web search unavailable

4. **Use Case 4**: User searches for a very specific query
   - User action: `find DeepSeek-V3 Technical Report`
   - System response: Web search finds the exact paper, returns metadata
   - Outcome: User gets the specific technical report with all ArXiv metadata

## Requirements

### Functional Requirements

- **FR1**: The system shall use web search as the default discovery method when USE_WEB_SEARCH is not set or is set to "yes" (case-insensitive)
- **FR2**: The system shall use ArXiv API keyword search exclusively when USE_WEB_SEARCH is set to "no" (case-insensitive)
- **FR3**: When using web search, the system shall query with `site:arxiv.org <user_query>`
- **FR4**: The system shall extract ArXiv paper IDs from web search result URLs (formats: `/abs/ID`, `/pdf/ID`, `/html/ID`)
- **FR5**: The system shall fetch full paper metadata using ArXiv API ID lookup (which is working reliably)
- **FR6**: The system shall apply semantic reranking to search results (existing behavior)
- **FR7**: The system shall sort final results by paper ID in ascending order (consistent with `list` command)
- **FR8**: The system shall limit results to the requested number (default k=5)
- **FR9**: The system shall handle duplicate paper IDs (same paper found multiple times in web search)
- **FR10**: The system shall gracefully handle version numbers in ArXiv IDs (e.g., strip `v1`, `v2` for API lookup)

### Non-Functional Requirements

- **NFR1**: Performance - Search should complete within 10 seconds for typical queries
- **NFR2**: Usability - User experience should be identical to current `find` command (transparent enhancement)
- **NFR3**: Reliability - System should provide clear error messages when both web search and ArXiv API fail
- **NFR4**: Maintainability - Code should clearly separate web search and ArXiv search paths for debugging
- **NFR5**: Testability - All search methods must be mockable for unit testing

## Design

### Architecture

The enhanced find command modifies the search flow in `arxiv_downloader.py`:

```
User runs: find <query>
         │
         ▼
┌────────────────────────────┐
│ search_arxiv_papers()      │
│ (main entry point)         │
└────────────────────────────┘
         │
         ▼
   Check USE_WEB_SEARCH env var
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  "yes"      "no"
  (default)  (legacy)
    │         │
    ▼         ▼
┌─────────────────────┐  ┌──────────────────────┐
│ _web_search_arxiv() │  │ _arxiv_keyword_search│
│                     │  │ (existing function)  │
│ 1. WebSearch        │  │                      │
│    site:arxiv.org   │  │ arxiv.Search(query)  │
│ 2. Extract IDs      │  │                      │
│ 3. arxiv.Search     │  │                      │
│    (id_list)        │  └──────────────────────┘
└─────────────────────┘           │
         │                        │
         └──────────┬─────────────┘
                    ▼
         candidates: list[PaperMetadata]
                    │
                    ▼
         ┌──────────────────────┐
         │ Semantic Reranking   │
         │ (existing logic)     │
         │ - Embed query        │
         │ - Embed papers       │
         │ - Compute similarity │
         │ - Sort by similarity │
         │ - Take top k         │
         └──────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Sort by Paper ID     │
         │ (ascending order)    │
         └──────────────────────┘
                    │
                    ▼
         Return: list[PaperMetadata]
         (sorted by paper ID)
```

### State Management

No changes to state machine. The `find` command continues to transition from any state to `select-new` state, with `last_query_set` containing the list of found paper IDs (sorted by paper ID).

### Data Structures

No new data structures. Continues to use existing `PaperMetadata` from `project_types.py`.

### Key Functions

#### New Function: `_web_search_arxiv()`

```python
def _web_search_arxiv(query: str, max_results: int) -> list[PaperMetadata]:
    """
    Search for papers using web search + ArXiv API.

    Parameters
    ----------
    query : str
        User's search query
    max_results : int
        Maximum number of papers to return

    Returns
    -------
    list[PaperMetadata]
        Papers found via web search, with full metadata from ArXiv API

    Raises
    ------
    Exception
        If web search fails or ArXiv API cannot fetch metadata
    """
    # 1. Perform web search with site:arxiv.org
    # 2. Extract ArXiv IDs from result URLs
    # 3. Fetch metadata using arxiv.Search(id_list=[...])
    # 4. Return list of PaperMetadata
```

#### Modified Function: `search_arxiv_papers()`

```python
def search_arxiv_papers(query: str, k: int = 1, candidate_limit: int = 50) -> list[PaperMetadata]:
    """
    Search for papers using web search (default) or ArXiv API (if USE_WEB_SEARCH=no).

    Parameters
    ----------
    query : str
        Search query
    k : int
        Number of results to return after reranking
    candidate_limit : int
        Maximum candidates to retrieve before reranking

    Returns
    -------
    list[PaperMetadata]
        Top k papers, sorted by paper ID (ascending)
    """
    # 1. Check USE_WEB_SEARCH environment variable
    # 2. Call _web_search_arxiv() or _arxiv_keyword_search()
    # 3. Apply semantic reranking (existing logic)
    # 4. Sort results by paper ID
    # 5. Return top k papers
```

### URL Parsing

ArXiv URLs come in multiple formats:
- Abstract: `https://arxiv.org/abs/2107.03374`
- PDF: `https://arxiv.org/pdf/2107.03374`
- HTML: `https://arxiv.org/html/2412.19437v1`
- Versioned: `https://arxiv.org/abs/2107.03374v2`

Regular expression pattern:
```python
r'/(?:abs|pdf|html)/(\d+\.\d+(?:v\d+)?)'
```

Version handling:
- Extract: `2107.03374v2`
- Strip version for API: `2107.03374` (ArXiv API handles version automatically)

### User Interface

No changes to command syntax. User continues to use:
```
> find <query>
```

Output remains the same - displays papers with:
- Paper number (1-indexed)
- Title
- Authors
- Categories
- ArXiv ID

Example:
```
> find transformer attention

Searching ArXiv...
Found 5 papers:

1. [2107.03374] Evaluating Large Language Models Trained on Code
   Authors: Mark Chen, Jerry Tworek, ...
   Categories: Machine Learning, Software Engineering

2. [2308.03873] Evaluating and Explaining Large Language Models...
   Authors: David N Palacio, ...
   Categories: Software Engineering, Machine Learning

...
```

### Environment Variable

**`USE_WEB_SEARCH`** - Controls search method
- **Not set** (default): Use web search
- **"yes"** (case-insensitive): Use web search
- **"no"** (case-insensitive): Use ArXiv API keyword search only
- **Any other value**: Log warning, default to web search

Check logic:
```python
use_web_search = os.environ.get('USE_WEB_SEARCH', 'yes').lower() != 'no'
```

### Error Handling

1. **Web search fails** (network error, quota exceeded, etc.)
   - Log error with details
   - Raise exception with user-friendly message: "Web search failed: <reason>. Try setting USE_WEB_SEARCH=no to use ArXiv API directly."

2. **No papers found via web search**
   - Return empty list
   - User sees: "No papers found matching query: <query>"

3. **ArXiv ID extraction fails**
   - Skip URLs that don't match pattern
   - Log warning with URL
   - Continue processing remaining URLs

4. **ArXiv API metadata fetch fails**
   - Log error with paper IDs that failed
   - Continue with successfully fetched papers
   - If all fail, raise exception

5. **Invalid USE_WEB_SEARCH value**
   - Log warning: "Invalid USE_WEB_SEARCH value '<value>', defaulting to 'yes'"
   - Proceed with web search

### Edge Cases

1. **Duplicate paper IDs in web search results**
   - Solution: Use set to track seen IDs, skip duplicates

2. **Version numbers in URLs** (`2107.03374v1`, `2107.03374v2`)
   - Solution: Strip version suffix before deduplication and API lookup

3. **Very generic queries** (e.g., "AI", "neural network")
   - May return many results from web search
   - Limit to `candidate_limit` URLs processed
   - Semantic reranking narrows to top k

4. **Query with special characters** (e.g., quotes, ampersands)
   - Web search handles URL encoding automatically
   - No special processing needed

5. **Web search returns 0 results but papers exist**
   - User can try reformulating query or setting USE_WEB_SEARCH=no
   - System returns empty list, consistent with current behavior

6. **ArXiv API is completely down**
   - Both web search and ArXiv keyword search will fail at metadata fetch
   - Raise exception with clear message

7. **Papers in web search are withdrawn/deleted**
   - ArXiv API will fail to fetch metadata
   - Log warning, skip those papers
   - Return successfully fetched papers

8. **Empty query**
   - Existing validation in chat interface handles this
   - If it reaches search function, web search will return generic results
   - ArXiv API would also return generic results

## Testing Considerations

### Test Scenarios

1. **Scenario 1**: Web search finds papers successfully (happy path)
   - Given: USE_WEB_SEARCH is not set (defaults to "yes")
   - When: User runs `find transformer attention`
   - Then:
     - Web search is called with `site:arxiv.org transformer attention`
     - ArXiv IDs are extracted from URLs
     - Metadata is fetched via ArXiv API
     - Results are sorted by paper ID
     - Top k papers are returned

2. **Scenario 2**: ArXiv API search used when web search disabled
   - Given: USE_WEB_SEARCH=no
   - When: User runs `find machine learning`
   - Then:
     - ArXiv API keyword search is used (legacy behavior)
     - No web search is performed
     - Results sorted by paper ID

3. **Scenario 3**: Web search returns no results
   - Given: USE_WEB_SEARCH=yes
   - When: User runs `find xyzabc123nonexistent`
   - Then:
     - Web search returns empty list
     - User sees "No papers found" message
     - State remains unchanged

4. **Scenario 4**: Duplicate papers in web search
   - Given: Web search returns same paper multiple times (different URLs)
   - When: Processing web search results
   - Then:
     - Duplicates are detected and removed
     - Only one copy of paper in final results

5. **Scenario 5**: Version numbers in URLs
   - Given: Web search returns URLs with versions (v1, v2)
   - When: Extracting ArXiv IDs
   - Then:
     - Version suffixes are stripped
     - Latest version is fetched from ArXiv API
     - Deduplication handles multiple versions of same paper

6. **Scenario 6**: Some papers fail metadata fetch
   - Given: Web search returns 10 paper IDs
   - When: 2 papers fail ArXiv API fetch (withdrawn/error)
   - Then:
     - 8 papers with successful metadata are returned
     - Errors are logged
     - No exception raised

7. **Scenario 7**: Environment variable variations
   - Given: USE_WEB_SEARCH is set to "YES", "yes", "No", "NO", "YES", etc.
   - When: Checking environment variable
   - Then: Case-insensitive comparison works correctly

8. **Scenario 8**: Web search with exact title match
   - Given: User searches for exact paper title
   - When: `find Evaluating Large Language Models Trained on Code`
   - Then:
     - Web search finds exact match
     - Paper appears in top results
     - Sorted by paper ID

### End-to-End User Flows

1. **Flow 1**: Find → Summarize workflow (web search)
   - Step 1: User runs `find transformer attention`
   - Step 2: System performs web search, displays 5 papers sorted by ID
   - Step 3: User runs `summarize 2`
   - Step 4: System downloads and summarizes paper #2 from results
   - **Expected**: State transitions to `select-new`, then `summarized`, paper ID in `selected_paper`

2. **Flow 2**: Find → List → Summary (sorted by ID)
   - Step 1: User runs `find DeepSeek V3`
   - Step 2: System shows results sorted by paper ID
   - Step 3: User runs `list`
   - Step 4: Papers displayed in same order (by ID)
   - Step 5: User runs `summary 1`
   - **Expected**: Consistent paper numbering across commands

3. **Flow 3**: Legacy ArXiv search workflow
   - Step 1: User sets `export USE_WEB_SEARCH=no`
   - Step 2: User runs `find neural networks`
   - Step 3: System uses ArXiv API keyword search (if working)
   - Step 4: Results displayed sorted by paper ID
   - **Expected**: Same behavior as before enhancement

### Unit Tests (with Mocks)

1. **test_web_search_arxiv_basic()**
   - Mock WebSearch to return sample ArXiv URLs
   - Mock ArXiv API to return sample metadata
   - Assert: Correct paper IDs extracted and metadata fetched

2. **test_web_search_arxiv_duplicate_ids()**
   - Mock WebSearch with duplicate paper URLs
   - Assert: Duplicates removed, only unique papers returned

3. **test_web_search_arxiv_version_handling()**
   - Mock WebSearch with versioned URLs (v1, v2)
   - Assert: Versions stripped, API called with base ID

4. **test_search_arxiv_papers_use_web_search_yes()**
   - Set USE_WEB_SEARCH=yes
   - Mock web search functions
   - Assert: Web search path is taken

5. **test_search_arxiv_papers_use_web_search_no()**
   - Set USE_WEB_SEARCH=no
   - Mock ArXiv API
   - Assert: ArXiv keyword search path is taken

6. **test_search_arxiv_papers_default()**
   - USE_WEB_SEARCH not set
   - Assert: Defaults to web search

7. **test_search_arxiv_papers_sorted_by_id()**
   - Mock search returns papers out of order
   - Assert: Final results sorted by paper ID ascending

8. **test_url_parsing_various_formats()**
   - Test regex with abs, pdf, html URLs
   - Test with and without version numbers
   - Assert: All formats parsed correctly

9. **test_web_search_empty_results()**
   - Mock WebSearch returns empty list
   - Assert: Returns empty list, no errors

10. **test_web_search_arxiv_api_failure()**
    - Mock WebSearch succeeds
    - Mock ArXiv API raises exception
    - Assert: Exception propagated with clear message

11. **test_env_var_case_insensitive()**
    - Test YES, yes, No, NO variations
    - Assert: Correct behavior for all cases

12. **test_invalid_env_var_value()**
    - Set USE_WEB_SEARCH=maybe
    - Assert: Warning logged, defaults to web search

### Integration Tests

1. **test_find_command_with_web_search_integration()**
   - Use actual ChatInterface and WorkflowRunner
   - Mock only external calls (WebSearch, ArXiv API)
   - Test state transitions and query set population

2. **test_find_with_legacy_search_integration()**
   - Set USE_WEB_SEARCH=no
   - Test legacy path still works

## Dependencies

- **Existing**: `arxiv` Python library (for metadata fetch via ID lookup)
- **Existing**: `WebSearch` tool (available in Claude Code environment)
- **Existing**: Semantic reranking logic in `search_arxiv_papers()`
- **Existing**: `PaperMetadata` data structure
- **Existing**: State machine and chat interface

No new external dependencies required.

## Alternatives Considered

### Alternative 1: Local repository search first
- **Pros**: Fast, works offline, finds papers user already has
- **Cons**: Doesn't discover new papers, requires indexed local collection
- **Decision**: Not chosen because user's primary use case is discovering new papers on ArXiv. Local search could be added later as a complementary feature.

### Alternative 2: Web search as fallback only
- **Pros**: Preserves existing behavior when ArXiv API works
- **Cons**: Inferior results quality, still breaks when ArXiv API has issues
- **Decision**: Not chosen because user prefers web search for quality and reliability

### Alternative 3: Make web search the only method (remove ArXiv keyword search)
- **Pros**: Simpler code, one code path
- **Cons**: No fallback if web search unavailable, less flexible
- **Decision**: Not chosen because user may want ArXiv-only search (quotas, regional restrictions)

### Alternative 4: Use different reranking for web vs ArXiv results
- **Pros**: Could optimize for each search type
- **Cons**: More complexity, inconsistent results
- **Decision**: Not chosen - keep consistent semantic reranking for all results

### Alternative 5: Sort results by relevance score instead of paper ID
- **Pros**: Most relevant papers shown first
- **Cons**: Inconsistent with `list` command, breaks user's mental model of paper numbering
- **Decision**: Not chosen - user explicitly wants paper ID sorting for consistency

## Open Questions

- [x] Should web search be default or fallback? → **Default** (user decision)
- [x] How should results be sorted? → **By paper ID** (user decision)
- [x] Environment variable name and values? → **USE_WEB_SEARCH with yes/no** (user decision)
- [ ] What should `candidate_limit` be for web search? (Web search may return fewer results than ArXiv keyword search)
- [ ] Should we add logging to show which search method was used? (helpful for debugging)
- [ ] Should we cache web search results to avoid repeated queries? (could improve performance)

---

## Notes

This design addresses the immediate issue with ArXiv API keyword search while improving overall search quality. The environment variable provides flexibility for users in different situations (quotas, regional restrictions, debugging).

The consistent sorting by paper ID ensures that paper numbering remains predictable across `find`, `list`, and other commands, maintaining user's mental model of the system.
