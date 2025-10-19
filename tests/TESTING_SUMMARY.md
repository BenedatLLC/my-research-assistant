# Testing Summary

**Last Updated**: October 17, 2025

This document provides an overview of test coverage across the my-research-assistant project. It helps developers understand what's tested, what workflows are covered, and where testing gaps exist.

## Test Organization

Tests are organized by component and functionality:
- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete user workflows

## Test Coverage by Component

### Core Components

#### State Machine (`test_state_machine.py`)
- **Coverage**: 30+ tests covering all state transitions and command validation
- **API-Level**: ✅ Yes - tests StateMachine directly without terminal I/O
- **Key Scenarios**:
  - All 6 states (initial, select-new, select-view, summarized, sem-search, research)
  - State transitions for each command
  - Command availability by state
  - State variable management (last_query_set, selected_paper, draft)
  - Error handling and invalid transitions
- **Last Modified**: September 2025

#### State Machine Ordering (`test_state_machine_ordering.py`)
- **Coverage**: Paper ordering and numbering consistency
- **Key Scenarios**:
  - Query set ordering maintained across operations
  - Paper numbers match paper IDs correctly
- **Last Modified**: September 2025

#### Chat Interface (`test_chat.py`)
- **Coverage**: Command processing and state integration
- **API-Level**: ✅ Yes - tests ChatInterface.process_command()
- **Key Scenarios**:
  - Command parsing and routing
  - Integration with state machine
  - User input handling
- **Last Modified**: September 2025

#### Workflow Orchestration (`test_workflow.py`)
- **Coverage**: LlamaIndex workflow operations
- **Key Scenarios**:
  - Workflow execution
  - Event handling
  - Result object validation
- **Async**: ✅ Uses pytest-asyncio
- **Last Modified**: October 2025

### Paper Management

#### Paper Argument Parsing (`test_paper_argument_parsing.py`)
- **Coverage**: 24 tests for enhanced paper selection logic
- **Key Scenarios**:
  - Integer number parsing (references to last_query_set)
  - ArXiv ID parsing (with/without version numbers)
  - Repository-wide paper lookup
  - Version disambiguation
  - Query set preservation logic
- **Last Modified**: September 2025

#### Paper Removal (`test_paper_removal.py`)
- **Coverage**: 14 tests for complete paper removal
- **Key Scenarios**:
  - Remove from all storage locations (PDFs, summaries, indexes, etc.)
  - Vector index cleanup
  - Error handling for non-existent papers
- **Last Modified**: October 2025

#### Open Command (`test_open_command.py`)
- **Coverage**: 8 tests for PDF viewing
- **Key Scenarios**:
  - PDF viewer integration
  - Terminal fallback when viewer unavailable
  - Paper selection by number and ID
- **Last Modified**: October 2025

### Document Processing

#### ArXiv Integration (`test_search_arxiv_papers.py`)
- **Coverage**: ArXiv API search and metadata retrieval
- **Unit Tests**: 3 tests for search functionality
- **Integration Tests**: 20 tests for Google search integration and routing
- **Key Scenarios**:
  - Paper search by keywords (ArXiv API)
  - Google Custom Search integration
  - Version deduplication (_deduplicate_arxiv_ids)
  - Search method routing (Google vs ArXiv)
  - Metadata extraction
  - Error handling for network issues
- **Mocking**: ✅ Mocks ArXiv API and Google Search to avoid flaky network tests
- **Last Modified**: October 2025

#### Google Search Integration (`test_google_search.py`)
- **Coverage**: Google Custom Search API integration
- **Unit Tests**: 15 tests for URL parsing and API integration
- **Key Scenarios**:
  - ArXiv ID extraction from URLs (modern and legacy formats)
  - Google Custom Search API calls
  - Version number handling
  - Error handling for missing credentials
- **Last Modified**: October 2025

#### PDF Processing (`test_pdf_image_extractor.py`)
- **Coverage**: PDF text and image extraction
- **Key Scenarios**:
  - Text extraction with PyMuPDF
  - Image extraction from PDFs
  - Error handling for corrupted PDFs
- **Last Modified**: August 2025

#### Download and Indexing (`test_download_and_index.py`)
- **Coverage**: 10 tests for PDF download and vector indexing
- **Key Scenarios**:
  - PDF download from ArXiv
  - Vector index creation with ChromaDB
  - Idempotent indexing
  - Search functionality
  - Index rebuilding
- **File Operations**: ✅ Uses temp_file_locations fixture
- **Last Modified**: October 2025

### Vector Store and Search

#### Semantic Search (`test_semantic_search_fix.py`)
- **Coverage**: Search query handling and diversity
- **Key Scenarios**:
  - MMR (Maximum Marginal Relevance) for diverse results
  - Compound query handling
  - Multiple paper matching
- **Last Modified**: September 2025

#### Store Validation (`test_validate_store.py`)
- **Coverage**: Paper storage validation logic
- **Key Scenarios**:
  - Check for complete paper storage (PDFs, text, summaries, indexes)
  - Missing file detection
  - Index chunk counting
- **Last Modified**: September 2025

#### Store Validation Integration (`test_validate_store_integration.py`)
- **Coverage**: End-to-end validation workflows
- **Integration Level**: ✅ Tests validate-store command flow
- **Last Modified**: September 2025

### Research Features

#### Research Workflow (`test_research_workflow.py`)
- **Coverage**: Hierarchical RAG implementation
- **Key Scenarios**:
  - Stage 1: Summary index search
  - Stage 2: Content index filtered search
  - Stage 3: LLM synthesis with citations
  - Stage 4: Reference formatting
- **Async**: ✅ Uses pytest-asyncio
- **Last Modified**: October 2025

#### Research Integration (`test_research_integration.py`)
- **Coverage**: E2E research command testing
- **Integration Level**: ✅ Tests complete research workflow
- **Key Scenarios**:
  - Query → Summary search → Content search → Synthesis
  - Citation generation and validation
  - Reference section formatting
- **Last Modified**: October 2025

### Content Generation

#### Summarization (`test_summarizer.py`)
- **Coverage**: LLM-powered paper summarization
- **Key Scenarios**:
  - Summary generation with templates
  - Prompt variable substitution
  - Version management (v1, v2 prompts)
- **Last Modified**: August 2025

#### Prompt Management (`test_prompt.py`)
- **Coverage**: Template-based prompt system
- **Key Scenarios**:
  - Prompt template loading
  - Variable substitution
  - Error handling for missing variables
- **Last Modified**: August 2025

### Model Configuration

#### Model Management (`test_models.py`)
- **Coverage**: LLM and embedding model configuration
- **Key Scenarios**:
  - Default model initialization
  - Embedding model configuration
  - Model caching
  - Batch embedding processing
- **Last Modified**: October 2025

### Ordering and Consistency

#### Find Command Ordering (`test_find_ordering.py`)
- **Coverage**: Search result ordering consistency
- **Key Scenarios**:
  - Results ordered by relevance from ArXiv
  - Internal state ordering matches display
- **Last Modified**: September 2025

#### List/Summary Ordering (`test_list_summary_ordering.py`)
- **Coverage**: Paper list display consistency
- **Key Scenarios**:
  - Consistent ordering across commands
  - Paper number alignment with IDs
- **Last Modified**: September 2025

## End-to-End User Flows

These tests verify complete user workflows from start to finish:

### Flow 1: Find → Summarize → Read
**Test Files**: `test_workflow.py`, `test_state_machine.py`, `test_find_command_e2e.py`
**Status**: ✅ Passing
**E2E Tests**: 9 comprehensive end-to-end tests covering enhanced find command
**Scenarios Covered**:
1. Find papers by keyword search (Google Custom Search or ArXiv API fallback)
2. Select paper by number from results (sorted by paper ID)
3. Generate summary with LLM
4. View summary in terminal
5. State transitions: initial → select-new → summarized
6. **NEW**: Google Custom Search integration with automatic fallback
7. **NEW**: Version deduplication (choosing latest version)
8. **NEW**: Quota exhaustion error handling
9. **NEW**: Empty result handling
10. **NEW**: Result limiting and sorting consistency

### Flow 2: List → View Summary → Open PDF
**Test Files**: `test_state_machine.py`, `test_open_command.py`
**Status**: ✅ Passing
**Scenarios Covered**:
1. List all indexed papers
2. Select paper by number
3. View existing summary
4. Open PDF in viewer
5. State transitions: initial → select-view → summarized

### Flow 3: Research with Citations
**Test Files**: `test_research_workflow.py`, `test_research_integration.py`
**Status**: ✅ Passing
**Scenarios Covered**:
1. User submits research query
2. System searches summary index (Stage 1)
3. System searches content index in relevant papers (Stage 2)
4. LLM synthesizes answer with citations (Stage 3)
5. System formats references (Stage 4)
6. State transitions: initial → research

### Flow 4: Semantic Search
**Test Files**: `test_semantic_search_fix.py`, `test_workflow.py`
**Status**: ✅ Passing
**Scenarios Covered**:
1. User submits search query
2. System searches content index
3. System retrieves relevant chunks
4. LLM summarizes results
5. State transitions: initial → sem-search

### Flow 5: Paper Management
**Test Files**: `test_paper_removal.py`, `test_validate_store.py`
**Status**: ✅ Passing
**Scenarios Covered**:
1. Validate paper storage
2. Identify papers to remove
3. Remove paper from all locations
4. Verify removal complete

### Flow 6: Index Rebuild
**Test Files**: `test_download_and_index.py`
**Status**: ✅ Passing
**Scenarios Covered**:
1. Rebuild vector indexes from scratch
2. Re-index all PDFs
3. Re-index all summaries and notes
4. Verify index functionality

### Flow 7: Enhanced Find Command Workflows (NEW)
**Test Files**: `test_find_command_e2e.py`
**Status**: ✅ Passing (9 E2E tests)
**Last Updated**: October 17, 2025

This comprehensive E2E test suite covers the enhanced find command implementation with Google Custom Search integration:

#### Test 1: Find → Summarize with Google Search
- User has Google credentials configured
- User runs `find transformer attention`
- System uses Google Custom Search (logged)
- System displays top 5 papers **sorted by paper ID** (ascending)
- User runs `summarize 2`
- System downloads and summarizes paper #2 from sorted results
- **Expected**: State transitions initial → select-new → summarized

#### Test 2: Find → List → Summary (Sorted by ID)
- User runs `find DeepSeek V3`
- System shows results sorted by paper ID
- User runs `list`
- Papers displayed in same order (by ID)
- User runs `summary 1`
- **Expected**: Consistent paper numbering across find and list commands

#### Test 3: Automatic Fallback to ArXiv Search
- User does not configure Google credentials (API_KEY or ENGINE_ID missing/empty)
- User runs `find neural networks`
- System detects no credentials
- System logs: "Google Custom Search not configured, using ArXiv API search..."
- System automatically uses ArXiv API keyword search
- Results displayed **sorted by paper ID**
- **Expected**: Backward compatible behavior (same as before enhancement)

#### Test 4: Google Search Quota Exhausted (Error Handling)
- User has Google credentials configured
- User runs `find deep learning`
- Google API returns 429 (quota exhausted)
- System raises exception with clear message
- **Expected**: User-friendly error message, no automatic fallback to ArXiv

#### Test 5: Google Search No Results
- User runs `find xyzabc123nonexistent`
- Google search returns empty list
- System returns empty result (success=False, "No papers found")
- **Expected**: State remains unchanged

#### Test 6: Google Search Version Deduplication
- Google search returns multiple versions: `["2107.03374", "2107.03374v1", "2107.03374v2", "2308.03873"]`
- System deduplicates by choosing latest version
- Only `2107.03374v2` appears in results (not v1 or base ID)
- **Expected**: Latest version chosen automatically

#### Test 7: Find → Semantic Search Integration
- User runs `find transformer attention`
- Papers found and sorted by ID
- User runs `sem-search query optimization`
- **Expected**: Query set preserved, papers still available for selection

#### Test 8: Empty Engine ID Fallback
- User has `GOOGLE_SEARCH_API_KEY` set but `GOOGLE_SEARCH_ENGINE_ID` is empty
- System detects incomplete credentials
- System falls back to ArXiv API search
- **Expected**: Graceful fallback on partial configuration

#### Test 9: Result Limiting with Google Search
- Google search returns 5 papers
- User requests k=3 papers
- System returns only 3 papers (first 3 when sorted by ID)
- **Expected**: Results properly limited after sorting

## Testing Gaps and TODOs

### Known Gaps
- [ ] Notes command not fully tested (implementation incomplete)
- [ ] Improve command error handling tests (more edge cases)
- [ ] Performance tests for large paper repositories (100+ papers)
- [ ] Concurrent access tests (multiple users/sessions)

### Future Test Improvements
- [ ] Add property-based testing for paper ID parsing
- [ ] Add load tests for semantic search with large indexes
- [ ] Add tests for network failure recovery in ArXiv downloads
- [ ] Add integration tests for PDF viewer fallback scenarios

## Test Running Guidelines

### Run All Tests
```bash
# Standard run
pytest

# With verbose output
pytest -v

# With coverage report (if coverage tool installed)
pytest --cov=src/my_research_assistant
```

### Run Specific Components
```bash
# State machine tests
pytest tests/test_state_machine.py

# Research workflow tests
pytest tests/test_research_workflow.py tests/test_research_integration.py

# All integration tests
pytest tests/test_*_integration.py
```

### Run by Test Type
```bash
# End-to-end flows only
pytest -k "test_e2e or test_flow or test_workflow"

# Unit tests only (excluding integration)
pytest -k "not integration"
```

### Run with Specific Markers (if configured)
```bash
# Fast tests only (excluding slow integration tests)
pytest -m "not slow"

# Tests that require external services
pytest -m "external"
```

## Test Fixtures

### Common Fixtures (`conftest.py`)

- **temp_file_locations**: Creates temporary FileLocations for testing
  - Automatically cleans up after test
  - Prevents modification of docs/ directory
  - Used by most file operation tests

### Best Practices

1. **Always use temp_file_locations** for file operations
2. **Mock external APIs** (ArXiv, OpenAI) to avoid flaky tests
3. **Prefer API-level testing** over terminal I/O simulation
4. **Follow naming conventions**: `test_<component>_<scenario>`
5. **Keep tests isolated**: Each test should be independent
6. **Use fixtures** for common setup/teardown
7. **Document complex test scenarios** with comments

## Updating This Document

When adding new tests or test files:
1. Add entry to appropriate section above
2. Document key scenarios covered
3. Note API-level testing status
4. Add to E2E flows if applicable
5. Update last modified date
6. Update testing gaps if resolving TODOs

---

**Note**: This document should be updated whenever:
- New test files are added
- Significant test coverage is added
- E2E workflows are implemented
- Testing gaps are identified or resolved
