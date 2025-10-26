# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a command-line chatbot agent for keeping up with the latest research in generative AI, as published on ArXiv. The system provides an interactive terminal interface using the `rich` Python library, enabling users to find, download, index, summarize, and search through research papers with semantic capabilities.

## Commands

### Testing
```bash
# Run all tests
pytest

# Run tests with uv (preferred package manager)
uv run pytest

# Run specific test file
pytest tests/test_summarizer.py

# Run tests with verbose output
pytest -v
```

Write new unit tests under tests/ rather than creating throwaway tests to validate changes.
When testing anything that can change files under docs/, be sure to use FileLocations to override
the default location and make changes into a temporary directory. DO NOT modify the files under
docs/ without first asking the user.

### Running the Application
```bash
# Run the main application
python -m my_research_assistant

# Run the interactive chat interface (recommended)
chat

# Or with uv
uv run chat
uv run python -m my_research_assistant
```

### Interactive Chat Interface
The `chat` command launches a rich terminal interface with:
- Interactive paper search and selection
- Real-time workflow progress with visual feedback  
- Markdown rendering for summaries and responses
- Command-based interaction for research operations
- Conversation history and status tracking

#### Core User Operations
1. **Find, download, and summarize papers** - Keyword search from ArXiv with user refinement, automated paper processing
2. **View repository content** - List indexed papers, view individual papers and summaries, open PDFs in viewer
3. **Semantic search** - Search across papers with summarized answers and page references
4. **Deep research** - Hierarchical RAG approach: summary search → targeted content retrieval → synthesis with citations
5. **Repository management** - Re-index, re-summarize, validate store, remove papers, and manage the paper collection
6. **Personal notes** - Add and edit personal notes for papers
7. **Content management** - Improve summaries and research results, save results to files

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Add dev dependency
uv add --group dev <package-name>
```

## Architecture Overview

The system is built around a state machine-driven workflow with a pipeline architecture for paper processing:

### Core Data Flow
1. **Search & Metadata** (`arxiv_downloader.py`, `google_search.py`) - Google Custom Search (primary) or ArXiv API (fallback) for searching and retrieving paper metadata
2. **Download** (`arxiv_downloader.py`) - PDF download and local storage management
3. **Text Extraction** (`vector_store.py`) - Extract text from PDFs using PyMuPDF4LLM
4. **Indexing** (`vector_store.py`) - Dual ChromaDB instances (content and summary indexes) for semantic search
5. **Summarization** (`summarizer.py`) - LLM-powered paper summarization with versioned prompts
6. **Workflow Orchestration** (`workflow.py`) - LlamaIndex workflow for research assistant operations
7. **State Management** (`state_machine.py`) - State machine controlling valid commands and transitions

### Key Components

- **`PaperMetadata`** (`project_types.py`) - Central data structure containing paper information (title, authors, categories, URLs, local paths)
- **`FileLocations`** (`file_locations.py`) - Configuration for data storage locations (PDFs, summaries, indexes, images, notes, results)
- **`ChatInterface`** (`chat.py`) - Rich terminal interface with state machine integration and command processing
- **`StateMachine`** (`state_machine.py`) - Workflow state management with 6 states (initial, select-new, select-view, summarized, sem-search, research)
- **`WorkflowRunner`** (`workflow.py`) - LlamaIndex workflow orchestration with structured result objects
- **`PromptManager`** (`prompt.py`) - Template-based prompt system with variable substitution from markdown files
- **Dual Vector Stores** (`vector_store.py`) - Separate ChromaDB instances for content and summary indexes
- **Model Management** (`models.py`) - Centralized LLM configuration with caching
- **Google Search Integration** (`google_search.py`) - Google Custom Search API for paper discovery with ArXiv ID extraction and version handling
- **Paper Management** (`paper_manager.py`) - Utilities for resolving paper references (by number or ArXiv ID) and loading summaries
- **Paper Removal** (`paper_removal.py`) - Remove papers from all storage locations including vector indexes
- **Result Storage** (`result_storage.py`) - Save and manage search/research results with LLM-generated titles, open papers in PDF viewer
- **Store Validation** (`validate_store.py`) - Validate and report on paper storage status across all components
- **Logging Configuration** (`logging_config.py`) - Centralized logging setup with Rich terminal integration, file output, and API key redaction

### Data Storage Structure
```
${DOC_HOME}/
├── pdfs/                       # Downloaded PDF files
├── paper_metadata/             # JSON files with ArXiv metadata
├── extracted_paper_text/       # Markdown text extracted from PDFs
├── summaries/                  # LLM-generated markdown summaries
│   └── images/                 # Extracted figures from papers
├── notes/                      # Personal notes for papers (markdown)
├── results/                    # Saved semantic search and research results
└── index/                      # ChromaDB vector store persistence
    ├── content/                # Content index (paper chunks)
    └── summary/                # Summary index (summaries + notes)
```

### Prompt System
The system uses a template-based prompt architecture with:
- Markdown template files stored in `src/my_research_assistant/prompts/`
- Variable substitution using `{{VAR_NAME}}` syntax
- Versioned prompts (v1, v2) for base summaries and improvements
- Centralized prompt management through `prompt.py`

### Environment Configuration
- `DOC_HOME` - Required environment variable specifying base directory for all data
- `DEFAULT_MODEL` - Optional, defaults to 'gpt-4o' for LLM operations
- `DEFAULT_EMBEDDING_MODEL` - Optional, defaults to 'text-embedding-ada-002' for embeddings
- `MODEL_API_BASE` - Optional, defaults to OpenAI API, can use gateway or local server
- `OPENAI_API_KEY` - Required for LLM and embedding operations
- `PDF_VIEWER` - Optional, path to PDF viewer executable (e.g., '/usr/bin/open'). If not set, `open` command displays papers in terminal
- `GOOGLE_SEARCH_API_KEY` - Optional, enables Google Custom Search for paper discovery (100 queries/day free tier)
- `GOOGLE_SEARCH_ENGINE_ID` - Optional, specifies Custom Search Engine ID (configured for arxiv.org)

### Search & Retrieval Strategy
The system uses a multi-stage approach:
1. **Keyword Search** - Google Custom Search (if credentials configured) or ArXiv API (fallback) for candidate papers
2. **Version Deduplication** - Automatic selection of latest paper versions from search results
3. **Semantic Reranking** - LlamaIndex embeddings for similarity-based ranking, with fallback to text-based Jaccard similarity
4. **Paper ID Sorting** - Final results sorted by ArXiv ID (ascending) for consistent numbering across commands

### LlamaIndex Integration
- Uses LlamaIndex workflows for complex multi-step research operations
- Dual ChromaDB vector stores: content index (paper chunks) and summary index (summaries + notes)
- Document chunking, embedding, and vector storage capabilities with metadata enrichment
- Supports incremental indexing with persistent storage
- Event-driven workflow architecture for paper processing pipeline
- Structured result objects (`QueryResult`, `ProcessingResult`, `SaveResult`) for better error handling

### Error Handling and Logging

The system implements systematic error reporting and logging throughout:

**Error Message Format:**
- All user-facing error messages start with "❌" for consistency
- Messages are concise (1-3 lines) indicating what failed and why
- API errors from external services (OpenAI, Google Search, ArXiv) include details
- Sensitive information (API keys) is automatically redacted

**Logging System:**
- Centralized configuration via `logging_config.py`
- Integration with Rich library for terminal output
- Optional logging controlled by CLI arguments (`--loglevel`, `--logfile`)
- Four log levels: ERROR, WARNING, INFO, DEBUG
- Terminal format: Single-character level indicator (E/W/I/D) + message
- File format: ISO timestamp + level + message
- Log files are appended (not overwritten) with session delimiters
- LlamaIndex and OpenAI verbose logging suppressed by default

**Logging Conventions:**
- ERROR: All errors with stack traces (`exc_info=True`)
- WARNING: Unusual situations requiring user awareness
- INFO: Progress information and user commands
- DEBUG: Detailed debugging information
- Use `raise ... from ...` pattern when wrapping exceptions
- Log at catch sites, not at raise sites for custom exceptions
- Include context (paper ID, workflow state, substep) in error logs

**API Key Redaction:**
- Automatically redacts API keys in both terminal and file logs
- Shows first 6 and last 4 characters (e.g., "sk-U10C2******0yZg")
- Applies to OpenAI and Google Search API keys

### Testing Structure
- Tests use pytest with custom `conftest.py` for path setup and temporary directories
- `pytest-asyncio` for async workflow testing support
- Comprehensive test coverage:
  - State machine functionality (`test_state_machine.py`) - 30+ tests covering all workflows
  - Chat interface integration (`test_chat.py`) - Command processing and state transitions
  - Paper argument parsing (`test_paper_argument_parsing.py`) - 24 tests for enhanced parsing logic
  - Paper removal (`test_paper_removal.py`) - 14 tests for removal from all storage locations
  - Open command (`test_open_command.py`) - 8 tests for PDF viewer and terminal fallback
  - Workflow orchestration (`test_workflow.py`) - LlamaIndex workflow operations
  - Store validation (`test_validate_store.py`, `test_validate_store_integration.py`)
  - Component testing: summarizer, prompt system, PDF extraction, ArXiv search
- Mock-based unit tests for individual components
- Integration tests verify end-to-end functionality with temporary file structures

### State Machine Workflow

The system implements a comprehensive state machine with 6 states:

1. **initial** - Starting state, ready for queries
2. **select-new** - Papers found via `find`, ready to summarize
3. **select-view** - Papers listed via `list`, ready to view
4. **summarized** - Working with a specific paper and its summary
5. **sem-search** - Semantic search results available
6. **research** - Deep research results available

#### Command Set by State
- **Discovery**: `find <query>`, `list` (available from any state)
- **Paper Processing**: `summarize <number|id>` (from select-new), `summary <number|id>` (from select-view/sem-search/research)
- **Content Operations**: `open <number|id>` (view paper content via PDF viewer or terminal), `notes` (edit personal notes)
- **Search & Research**: `sem-search <query>`, `research <query>` (hierarchical RAG with citations, available from any state)
- **Workflow Management**: `improve <feedback>`, `save` (context-dependent)
- **Paper Management**: `remove-paper <number|id>` (remove paper from store, available from any state)
- **System**: `rebuild-index`, `validate-store`, `summarize-all`, `help`, `status`, `history`, `clear`, `quit`

#### State Variables
- `last_query_set` - Paper IDs from most recent query
- `selected_paper` - Currently selected paper for detailed work
- `draft` - In-progress content (summary, search results, research)
- `original_query` - User's original query for search/research operations

## Development Workflow

### Design-First Approach
The project follows a **design-first, test-driven development workflow** using three specialized Claude Code agents:

1. **Create design document** in `designs/` directory using `designs/TEMPLATE.md`
2. **Review design** with Claude to identify edge cases and unclear areas
3. **Update design** based on feedback and clarifications
4. **Implement with design-implementer agent**:
   - Creates detailed implementation plan in design doc
   - Gets user approval before coding
   - Implements using test-driven development
   - Delegates to qa-engineer for comprehensive testing
   - Delegates to doc-maintainer for documentation sync
   - Provides comprehensive summary with test counts and status

See `DEVELOPMENT_WORKFLOW.md` for complete workflow guide.

### The Three-Agent System

**design-implementer** (Coordinator):
- Implements features from design documents
- Creates implementation plans with user approval
- Uses test-driven development approach
- Delegates to specialized agents
- Located: `.claude/agents/design-implementer.md`

**qa-engineer** (Testing Specialist):
- Writes comprehensive test coverage (unit, integration, E2E)
- Ensures API-level testability
- Validates no existing functionality broken
- Updates `tests/TESTING_SUMMARY.md`
- Located: `.claude/agents/qa-engineer.md`

**doc-maintainer** (Documentation Specialist):
- Syncs README.md, CLAUDE.md, design docs
- Adds devlog.md entries with original user prompts
- Ensures documentation consistency
- Located: `.claude/agents/doc-maintainer.md`

### Testing Requirements
- **Write tests first** for new functionality (TDD approach)
- **API-level testing preferred** - avoid terminal I/O simulation when possible
- **Three test levels required**: Unit, Integration, End-to-End
- **Update tests/TESTING_SUMMARY.md** after adding tests
- **All tests must pass** before completion - never break existing functionality

### Documentation Requirements
All documentation must stay in sync with implementation:
- **README.md**: User-facing commands, features, and examples
- **CLAUDE.md**: Architecture, development conventions, and design document references
- **designs/*.md**: Feature specifications with Implementation Plan and Implementation sections
- **devlog.md**: Concise development log (simple changes: 5 lines max, major features: 10-20 lines)
- **tests/TESTING_SUMMARY.md**: Test coverage, E2E workflows, and testing gaps

**devlog.md format**: Match length to complexity. Simple fix = 3-5 lines (what + outcome). Major feature = 10-20 lines (context + changes + outcomes). No file lists - use git log.

### Design Document Structure
Design documents in `designs/` follow this structure:
- **Requirements and use cases** - What and why
- **Design and architecture** - How it works
- **Testing considerations** - What to test
- **Implementation Plan** - Written before coding (step-by-step, files, tests, risks)
- **Implementation** - How it was actually built (added after completion)

### Example Workflow
```bash
# 1. Create design
cp designs/TEMPLATE.md designs/new-feature.md
# Edit with requirements

# 2. Review with Claude
"Review designs/new-feature.md for clarity and edge cases"

# 3. Update based on feedback
"Update the design with [clarifications]"

# 4. Implement with agent
"Use design-implementer to implement designs/new-feature.md"
# Agent creates plan and asks for approval
# Agent implements with TDD
# Agent delegates to qa-engineer and doc-maintainer
# Agent provides comprehensive summary

# 5. All done!
# - Feature implemented
# - Tests written (15 tests: 5 unit, 7 integration, 3 E2E)
# - All tests passing
# - Documentation synced
# - devlog.md updated with your original prompt
```

## Development Notes

### Working with Papers
- Paper IDs can be provided with or without version numbers (e.g., '2503.22738v1' or '2503.22738')
- Papers can be referenced by integer number (when `last_query_set` exists) or ArXiv ID (from any state)
- Enhanced paper argument parsing handles version disambiguation and repository-wide lookups
- Conditional query set preservation: preserved when paper resolved by number, cleared when resolved by ArXiv ID (unless in set)
- The system handles ArXiv category mapping to human-readable names
- PDF files are named using ArXiv's default filename convention

### Error Handling
- Custom exceptions: `IndexError`, `ConfigError`, `PromptFileError`, `PromptVarError`
- State machine error recovery: transitions to appropriate states on failures
- Graceful fallbacks for embedding failures (switches to text-based similarity)
- Robust file existence checking before operations
- Prompt template validation and error reporting
- Structured error handling in workflow operations with detailed result objects

### Model Usage
- Centralized model configuration supports caching for performance
- Environment-based model selection (`DEFAULT_MODEL` env var, defaults to 'gpt-4o')
- OpenAI integration with configurable model parameters
- Template-based prompt system with versioned prompts for different operations

### Store Validation
- `validate-store` command provides comprehensive status reporting
- Checks for: PDF downloads, extracted text, summaries, notes, content index chunks, summary index chunks
- Rich table output with summary statistics
- Integration with both ChromaDB vector stores for chunk counting

### Design Documentation
The `designs/` directory contains comprehensive design documents:
- `workflow-state-machine-and-commands.md` - Complete state machine specification with test flows - **implemented**
- `command-arguments.md` - Enhanced paper argument parsing (integer numbers vs ArXiv IDs) - **implemented**
- `command-types.md` - Command categorization and usage patterns - **implemented**
- `open-command.md` - PDF viewer integration and terminal fallback - **implemented**
- `remove-paper-command.md` - Paper removal from all storage locations - **implemented**
- `research-command.md` - Hierarchical RAG design for deep research - **implemented**
- `find-command.md` - Enhanced find command with Google Custom Search integration - **implemented**
- `constants.md` - Centralized constants for search and retrieval hyperparameters - **implemented**
- `validate-command.md` - Store validation command design - **implemented**
- `error-handling-and-logging.md` - Error reporting and logging system - **implemented**
- `file-store.md` - Data storage architecture and paper states - **implemented**
- `user-stores.md` - High-level user operations and workflows - **partially implemented**
- `improved-pagination.md` - Single-key pagination design - **implemented**
