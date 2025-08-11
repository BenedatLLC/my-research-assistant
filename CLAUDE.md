# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an agentic research assistant focused on ArXiv papers. The system allows users to search, download, index, and summarize research papers, building a knowledge base with semantic search capabilities.

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
- Command-based interaction (search, select, improve, save)
- Conversation history and status tracking

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

The system is built around a pipeline architecture with these core components:

### Core Data Flow
1. **Search & Metadata** (`arxiv_downloader.py`) - ArXiv API integration for searching and retrieving paper metadata
2. **Download** (`arxiv_downloader.py`) - PDF download and local storage management
3. **Indexing** (`vector_store.py`) - LlamaIndex-based vector storage for semantic search
4. **Summarization** (`summarizer.py`) - LLM-powered paper summarization
5. **Workflow Orchestration** (`workflow.py`) - LlamaIndex workflow for research assistant operations

### Key Components

- **`PaperMetadata`** (`types.py`) - Central data structure containing paper information (title, authors, categories, URLs, local paths)
- **`FileLocations`** (`file_locations.py`) - Configuration for data storage locations (PDFs, summaries, index, images)
- **Global Vector Store** (`vector_store.py`) - Maintains persistent LlamaIndex vector store across sessions
- **Model Management** (`models.py`) - Centralized LLM configuration with caching

### Data Storage Structure
```
${DOC_HOME}/
├── pdfs/           # Downloaded PDF files
├── summaries/      # Generated markdown summaries
│   └── images/     # Extracted figures from papers
└── index/          # LlamaIndex vector store persistence
```

### Environment Configuration
- `DOC_HOME` - Required environment variable specifying base directory for all data
- `DEFAULT_MODEL` - Optional, defaults to 'gpt-4o' for LLM operations

### Search & Retrieval Strategy
The system uses a two-stage approach:
1. **Keyword Search** - ArXiv API search for candidate papers
2. **Semantic Reranking** - LlamaIndex embeddings for similarity-based ranking, with fallback to text-based Jaccard similarity

### LlamaIndex Integration
- Uses LlamaIndex for document chunking, embedding, and vector storage
- Supports incremental indexing with persistent storage
- Metadata enrichment (title, authors, categories) for enhanced retrieval

### Testing Structure
- Tests use pytest with custom `conftest.py` for path setup
- `pytest-asyncio` for async workflow testing support
- Test coverage includes search, download, indexing, summarization, and workflow orchestration
- Mock-based unit tests for individual workflow steps
- Integration tests verify end-to-end functionality
- Comprehensive workflow testing in `tests/test_workflow.py`

## Development Notes

### Working with Papers
- Paper IDs can be provided with or without version numbers (e.g., '2503.22738v1' or '2503.22738')
- The system handles ArXiv category mapping to human-readable names
- PDF files are named using ArXiv's default filename convention

### Error Handling
- Custom exceptions: `IndexError`, `ImageExtractError`, `ConfigError`
- Graceful fallbacks for embedding failures (switches to text-based similarity)
- Robust file existence checking before operations

### Model Usage
- Centralized model configuration supports caching for performance
- Environment-based model selection for flexibility across deployments
- OpenAI integration with configurable model parameters