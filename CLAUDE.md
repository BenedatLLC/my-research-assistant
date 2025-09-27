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
2. **View repository content** - List indexed papers, view individual papers and summaries
3. **Semantic search** - Search across papers with summarized answers and page references
4. **Deep research** - High-level summary search combined with detailed chunk analysis
5. **Repository management** - Re-index, re-summarize, validate store, and manage the paper collection
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
1. **Search & Metadata** (`arxiv_downloader.py`) - ArXiv API integration for searching and retrieving paper metadata
2. **Download** (`arxiv_downloader.py`) - PDF download and local storage management
3. **Text Extraction** (`pdf_image_extractor.py`) - Extract text and images from PDFs using PyMuPDF
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
- **Paper Management** (`paper_manager.py`) - Utilities for resolving paper references and loading summaries
- **Result Storage** (`result_storage.py`) - Save and manage search/research results with LLM-generated titles
- **Store Validation** (`validate_store.py`) - Validate and report on paper storage status across all components

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

### Search & Retrieval Strategy
The system uses a two-stage approach:
1. **Keyword Search** - ArXiv API search for candidate papers
2. **Semantic Reranking** - LlamaIndex embeddings for similarity-based ranking, with fallback to text-based Jaccard similarity

### LlamaIndex Integration
- Uses LlamaIndex workflows for complex multi-step research operations
- Dual ChromaDB vector stores: content index (paper chunks) and summary index (summaries + notes)
- Document chunking, embedding, and vector storage capabilities with metadata enrichment
- Supports incremental indexing with persistent storage
- Event-driven workflow architecture for paper processing pipeline
- Structured result objects (`QueryResult`, `ProcessingResult`, `SaveResult`) for better error handling

### Testing Structure
- Tests use pytest with custom `conftest.py` for path setup and temporary directories
- `pytest-asyncio` for async workflow testing support
- Comprehensive test coverage:
  - State machine functionality (`test_state_machine.py`) - 30+ tests covering all workflows
  - Chat interface integration (`test_chat.py`) - Command processing and state transitions
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
- **Content Operations**: `open <number|id>` (view paper content), `notes` (edit personal notes)
- **Search & Research**: `sem-search <query>`, `research <query>` (available from any state)
- **Workflow Management**: `improve <feedback>`, `save` (context-dependent)
- **System**: `rebuild-index`, `validate-store`, `summarize-all`, `help`, `status`, `history`, `clear`, `quit`

#### State Variables
- `last_query_set` - Paper IDs from most recent query
- `selected_paper` - Currently selected paper for detailed work
- `draft` - In-progress content (summary, search results, research)
- `original_query` - User's original query for search/research operations

## Development Notes

### Working with Papers
- Paper IDs can be provided with or without version numbers (e.g., '2503.22738v1' or '2503.22738')
- The system handles ArXiv category mapping to human-readable names
- PDF files are named using ArXiv's default filename convention

### Error Handling
- Custom exceptions: `IndexError`, `ImageExtractError`, `ConfigError`, `PromptFileError`, `PromptVarError`
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
- `workflow-state-machine-and-commands.md` - Complete state machine specification with test flows
- `validate-command.md` - Store validation command design
- `file-store.md` - Data storage architecture and paper states
- `user-stores.md` - High-level user operations and workflows
