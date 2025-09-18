import os
import datetime
from os.path import isdir, exists, join
from shutil import rmtree
from typing import Optional
import chromadb
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.schema import Document
from llama_index.vector_stores.chroma import ChromaVectorStore
import pymupdf4llm

from .file_locations import FILE_LOCATIONS, FileLocations
from .project_types import PaperMetadata, SearchResult
from .arxiv_downloader import get_downloaded_paper_ids, get_paper_metadata

# Initialize global variables to hold the VectorStoreIndex objects.
# We maintain separate indexes for content (paper text) and summaries/notes.
# This allows us to maintain the state of the indexes across multiple calls
# without having to reload them from disk every time.
CONTENT_INDEX = None
SUMMARY_INDEX = None

class IndexError(Exception):
    pass

class RetrievalError(Exception):
    pass


def _get_chroma_db_path(file_locations: FileLocations, index_type: str = "content") -> str:
    """Get the ChromaDB database path for the given file locations and index type.
    
    Parameters
    ----------
    file_locations : FileLocations
        The file locations configuration
    index_type : str
        Either "content" for paper content index or "summary" for summary/notes index
        
    Returns
    -------
    str
        Path to the ChromaDB directory for the specified index type
    """
    if index_type == "content":
        return join(file_locations.index_dir, "content_chroma_db")
    elif index_type == "summary":
        return join(file_locations.index_dir, "summary_chroma_db")
    else:
        raise ValueError(f"Invalid index_type: {index_type}. Must be 'content' or 'summary'")


def _initialize_chroma_vector_store(file_locations: FileLocations, index_type: str = "content") -> VectorStoreIndex:
    """Initialize a new ChromaDB vector store for the specified index type.
    
    Parameters
    ----------
    file_locations : FileLocations
        The file locations configuration
    index_type : str
        Either "content" for paper content index or "summary" for summary/notes index
        
    Returns
    -------
    VectorStoreIndex
        A new LlamaIndex vector store backed by ChromaDB
    """
    # Ensure the index directory exists
    file_locations.ensure_index_dir()
    
    # Initialize ChromaDB client with persistent storage
    db_path = _get_chroma_db_path(file_locations, index_type)
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # Get or create a collection based on index type
    collection_name = f"{index_type}_index"
    collection = chroma_client.get_or_create_collection(collection_name)
    
    # Create ChromaVectorStore
    vector_store = ChromaVectorStore(chroma_collection=collection)
    
    # Create storage context with the vector store
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create and return the index
    return VectorStoreIndex([], storage_context=storage_context)


def _load_existing_chroma_vector_store(file_locations: FileLocations, index_type: str = "content") -> VectorStoreIndex:
    """Load an existing ChromaDB vector store for the specified index type.
    
    Parameters
    ----------
    file_locations : FileLocations
        The file locations configuration
    index_type : str
        Either "content" for paper content index or "summary" for summary/notes index
        
    Returns
    -------
    VectorStoreIndex
        The loaded LlamaIndex vector store
        
    Raises
    ------
    IndexError
        If the database path or collection doesn't exist
    """
    db_path = _get_chroma_db_path(file_locations, index_type)
    
    if not exists(db_path):
        raise IndexError(f"ChromaDB path {db_path} does not exist")
    
    # Initialize ChromaDB client with persistent storage
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # Get the existing collection
    collection_name = f"{index_type}_index"
    try:
        collection = chroma_client.get_collection(collection_name)
    except Exception as e:
        raise IndexError(f"Collection '{collection_name}' not found: {e}")
    
    # Create ChromaVectorStore
    vector_store = ChromaVectorStore(chroma_collection=collection)
    
    # Create storage context with the vector store
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create and return the index
    return VectorStoreIndex([], storage_context=storage_context)


def _get_or_initialize_index(file_locations: FileLocations, index_type: str = "content") -> VectorStoreIndex:
    """Get or initialize a vector store index for the specified type.
    
    Parameters
    ----------
    file_locations : FileLocations
        The file locations configuration
    index_type : str
        Either "content" for paper content index or "summary" for summary/notes index
        
    Returns
    -------
    VectorStoreIndex
        The vector store index, either loaded from disk or newly created
    """
    global CONTENT_INDEX, SUMMARY_INDEX
    
    # Select the appropriate global variable
    if index_type == "content":
        current_index = CONTENT_INDEX
    elif index_type == "summary":
        current_index = SUMMARY_INDEX
    else:
        raise ValueError(f"Invalid index_type: {index_type}")
    
    # Initialize if not already set
    if current_index is None:
        print(f"{index_type.upper()}_INDEX is not set. Initializing...")
        
        # Check if ChromaDB already exists
        db_path = _get_chroma_db_path(file_locations, index_type)
        if exists(db_path):
            # If the database exists, load the existing index
            print(f"Existing {index_type} ChromaDB found at {db_path}. Loading into global variable.")
            try:
                current_index = _load_existing_chroma_vector_store(file_locations, index_type)
            except Exception as e:
                print(f"Error loading existing {index_type} ChromaDB: {e}. Creating a new empty index instead.")
                current_index = _initialize_chroma_vector_store(file_locations, index_type)
        else:
            # If the database does not exist, create a new instance
            print(f"No existing {index_type} ChromaDB found. Creating an empty global index.")
            current_index = _initialize_chroma_vector_store(file_locations, index_type)
        
        # Update the appropriate global variable
        if index_type == "content":
            CONTENT_INDEX = current_index
        else:
            SUMMARY_INDEX = current_index
    
    return current_index


def _paper_already_indexed(paper_id: str, index: VectorStoreIndex) -> bool:
    """Check if a paper is already indexed by searching for documents with the paper_id.
    
    Parameters
    ----------
    paper_id : str
        The paper ID to check for
    index : VectorStoreIndex
        The vector store index to search in
        
    Returns
    -------
    bool
        True if the paper is already indexed, False otherwise
    """
    try:
        # Use the retriever to search for any documents
        # We'll search for a generic term and check metadata
        retriever = index.as_retriever(similarity_top_k=20)
        results = retriever.retrieve("the")  # Search for common word
        
        # Check if any results have the matching paper_id in metadata
        for result in results:
            if hasattr(result, 'metadata') and result.metadata.get('paper_id') == paper_id:
                return True
        
        # If no results or no matches, try searching for the paper_id directly
        if not results:
            results = retriever.retrieve(paper_id)
            for result in results:
                if hasattr(result, 'metadata') and result.metadata.get('paper_id') == paper_id:
                    return True
                    
        return False
    except Exception:
        # If there's an error searching, assume not indexed to be safe
        return False


def _add_document_to_index(doc: Document, pmd: PaperMetadata, index: VectorStoreIndex, index_type: str = "content"):
    """Add a document to the specified index with appropriate metadata.
    
    Parameters
    ----------
    doc : Document
        The LlamaIndex document to add
    pmd : PaperMetadata
        The paper metadata for adding to document metadata
    index : VectorStoreIndex
        The index to add the document to
    index_type : str
        Either "content" or "summary" to determine appropriate metadata
    """
    # Add common metadata
    doc.metadata['paper_id'] = pmd.paper_id
    doc.metadata['title'] = pmd.title
    doc.metadata['authors'] = ', '.join(pmd.authors)
    doc.metadata['categories'] = ', '.join(pmd.categories)
    
    # Add type-specific metadata
    if index_type == "content":
        # For content index, add file path information
        if 'file_name' not in doc.metadata:
            filename = f"{pmd.paper_id}.pdf"
            doc.metadata['file_name'] = filename
        doc.metadata['file_path'] = 'pdfs/' + doc.metadata['file_name']
        
        # Add page_label if not present (use page number from metadata or default to 1)
        if 'page_label' not in doc.metadata:
            page_num = doc.metadata.get('page', 1)
            doc.metadata['page_label'] = str(page_num)
    elif index_type == "summary":
        # For summary index, add source type
        doc.metadata['source_type'] = doc.metadata.get('source_type', 'summary')
        # Add file path for summary/notes
        source_type = doc.metadata.get('source_type', 'summary')
        if source_type == 'summary':
            doc.metadata['file_path'] = f'summaries/{pmd.paper_id}.md'
        elif source_type == 'notes':
            doc.metadata['file_path'] = f'notes/{pmd.paper_id}.md'
    
    # Insert the document
    index.insert(doc)


def parse_file(pmd:PaperMetadata, file_locations:FileLocations=FILE_LOCATIONS) -> str:
    """
    Parses a single PDF file, returning a markdown representation of the text.
    We currently use PyMuPDF4LLM, which seems to have the best extraction. It is clearly
    better than the parser that comes with LlamaIndex.

    The extracted text is saved in extracted_paper_text_dir as PAPER_ID.md.
    If the file was previously parsed and cached, it loads from the cache instead of re-parsing.
    
    Parameters
    ----------
    pmd: PaperMetadata
        The metadata about the paper to be indexed, including file path, title,
        authors, and categories.
    file_locations: FileLocations, optional
        Locations to read pdfs and save the extracted text

    Returns
    -------
    str
        The extracted paper markdown text.

    """
    # Get the local PDF path
    local_pdf_path = pmd.get_local_pdf_path(file_locations)
    
    # Check if extracted text already exists for PyMuPDF parser
    file_locations.ensure_extracted_paper_text_dir()
    extracted_text_path = os.path.join(file_locations.extracted_paper_text_dir,
                                       f"{pmd.paper_id}.md")
    
    if os.path.exists(extracted_text_path):
        print(f"Using existing extracted text from: {extracted_text_path}")
        with open(extracted_text_path, 'r', encoding='utf-8') as f:
            paper_text = f.read()
        print(f"Loaded {len(paper_text)} characters of text")
    else:
        # Parse the PDF using PyMuPDF4LLM
        print("Parsing PDF with PyMuPDF4LLM...")
        paper_text = pymupdf4llm.to_markdown(local_pdf_path)
        print(f"Extracted {len(paper_text)} characters of text")
        
        # Save the extracted text for future reference
        with open(extracted_text_path, 'w', encoding='utf-8') as f:
            f.write(paper_text)
        print(f"Saved extracted text to: {extracted_text_path}")
    return paper_text



def index_file_using_pymupdf_parser(pmd:PaperMetadata, file_locations:FileLocations=FILE_LOCATIONS) -> None:
    """
    Parses, chunks, and indexes a single PDF file using PyMuPDF4LLM parser in an idempotent manner.
    
    This function loads a PDF document, creates chunks using PyMuPDF4LLM, adds metadata 
    (title, authors, categories), and inserts it into the content index. The function is 
    idempotent - if the paper is already indexed, it will skip indexing and return early.
    The index is automatically persisted to disk after adding the new document.

    Parameters
    ----------
    pmd: PaperMetadata
        The metadata about the paper to be indexed, including file path, title,
        authors, and categories.
    file_locations: FileLocations, optional
        Locations to read pdfs and save the index.

    Returns
    -------
    Nothing

    Raises
    ------
    IndexError
        If the PDF cannot be loaded or no documents are found in the file.
    """
    # 1. Get or initialize the content index
    content_index = _get_or_initialize_index(file_locations, "content")
    
    # 2. Check if paper is already indexed (idempotency check)
    if _paper_already_indexed(pmd.paper_id, content_index):
        print(f"Paper {pmd.paper_id} is already indexed. Skipping.")
        return
    
    # 3. Load the new PDF file using PyMuPDF4LLM reader.
    local_pdf_path = pmd.get_local_pdf_path(file_locations)
    try:
        llama_reader = pymupdf4llm.LlamaMarkdownReader()
        llama_docs = llama_reader.load_data(local_pdf_path)
        
        if not llama_docs:
            raise IndexError(f"Warning: No document loaded from {local_pdf_path}. Skipping.")

    except Exception as e:
        raise IndexError(f"Error loading document from {local_pdf_path}: {e}") from e

    # 4. Insert the new document into the content index.
    print(f"Adding new document '{local_pdf_path}' with {len(llama_docs)} chunks to the content index.")
    for doc in llama_docs:
        _add_document_to_index(doc, pmd, content_index, "content")

    # 5. ChromaDB automatically persists changes, no need to manually save
    print("Content index updated successfully (ChromaDB auto-persists).")


def index_file(pmd:PaperMetadata, file_locations:FileLocations=FILE_LOCATIONS) -> str:
    """
    Wrapper function to index a PDF file and return the extracted text.
    
    This function indexes the file using the PyMuPDF parser and then
    returns the cached text content from parse_file for further processing.
    
    Parameters
    ----------
    pmd: PaperMetadata
        The metadata about the paper to be indexed
    file_locations: FileLocations, optional
        Locations to read pdfs and save the index
        
    Returns
    -------
    str
        The extracted paper text content
    """
    # Index the file using the PyMuPDF parser
    index_file_using_pymupdf_parser(pmd, file_locations)
    
    # Get the cached text content using parse_file (avoids re-parsing)
    paper_text = parse_file(pmd, file_locations)
    return paper_text


def index_summary(pmd: PaperMetadata, file_locations: FileLocations = FILE_LOCATIONS) -> None:
    """
    Index a paper's summary in an idempotent manner.
    
    This function loads a paper's summary markdown file, chunks it, and adds it to the 
    summary index. The function is idempotent - if the paper's summary is already indexed, 
    it will skip indexing and return early.

    Parameters
    ----------
    pmd: PaperMetadata
        The metadata about the paper whose summary should be indexed
    file_locations: FileLocations, optional
        Locations to read summaries and save the index

    Returns
    -------
    None

    Raises
    ------
    IndexError
        If the summary file cannot be found or loaded
    """
    # 1. Get or initialize the summary index
    summary_index = _get_or_initialize_index(file_locations, "summary")
    
    # 2. Check if paper summary is already indexed (idempotency check)
    if _paper_already_indexed(pmd.paper_id, summary_index):
        print(f"Summary for paper {pmd.paper_id} is already indexed. Skipping.")
        return
    
    # 3. Check if summary file exists
    file_locations.ensure_summaries_dir()
    summary_path = join(file_locations.summaries_dir, f"{pmd.paper_id}.md")
    
    if not exists(summary_path):
        raise IndexError(f"Summary file not found: {summary_path}")
    
    # 4. Load the summary as a document
    try:
        reader = SimpleDirectoryReader(input_files=[summary_path])
        documents = reader.load_data()
        
        if not documents:
            raise IndexError(f"No content loaded from summary file: {summary_path}")
    except Exception as e:
        raise IndexError(f"Error loading summary from {summary_path}: {e}") from e
    
    # 5. Add documents to the summary index
    print(f"Adding summary for paper {pmd.paper_id} with {len(documents)} chunks to the summary index.")
    for doc in documents:
        doc.metadata['source_type'] = 'summary'
        _add_document_to_index(doc, pmd, summary_index, "summary")
    
    print("Summary index updated successfully (ChromaDB auto-persists).")


def index_notes(pmd: PaperMetadata, file_locations: FileLocations = FILE_LOCATIONS) -> None:
    """
    Index a paper's notes in an idempotent manner.
    
    This function loads a paper's notes markdown file, chunks it, and adds it to the 
    summary index. The function is idempotent - if the paper's notes are already indexed, 
    it will skip indexing and return early.

    Parameters
    ----------
    pmd: PaperMetadata
        The metadata about the paper whose notes should be indexed
    file_locations: FileLocations, optional
        Locations to read notes and save the index

    Returns
    -------
    None

    Raises
    ------
    IndexError
        If the notes file cannot be found or loaded
    """
    # 1. Get or initialize the summary index (notes go in the same index as summaries)
    summary_index = _get_or_initialize_index(file_locations, "summary")
    
    # 2. For notes, we check if they're already indexed by looking for notes-specific metadata
    # This is different from summary checking since both can exist for the same paper
    try:
        retriever = summary_index.as_retriever(similarity_top_k=10)
        results = retriever.retrieve(f"paper_id:{pmd.paper_id}")
        
        # Check if any results have notes source_type for this paper
        notes_already_indexed = False
        for result in results:
            if (hasattr(result, 'metadata') and 
                result.metadata.get('paper_id') == pmd.paper_id and
                result.metadata.get('source_type') == 'notes'):
                notes_already_indexed = True
                break
        
        if notes_already_indexed:
            print(f"Notes for paper {pmd.paper_id} are already indexed. Skipping.")
            return
            
    except Exception:
        # If there's an error searching, proceed with indexing to be safe
        pass
    
    # 3. Check if notes file exists
    file_locations.ensure_notes_dir()
    notes_path = join(file_locations.notes_dir, f"{pmd.paper_id}.md")
    
    if not exists(notes_path):
        raise IndexError(f"Notes file not found: {notes_path}")
    
    # 4. Load the notes as a document
    try:
        reader = SimpleDirectoryReader(input_files=[notes_path])
        documents = reader.load_data()
        
        if not documents:
            raise IndexError(f"No content loaded from notes file: {notes_path}")
    except Exception as e:
        raise IndexError(f"Error loading notes from {notes_path}: {e}") from e
    
    # 5. Add documents to the summary index
    print(f"Adding notes for paper {pmd.paper_id} with {len(documents)} chunks to the summary index.")
    for doc in documents:
        doc.metadata['source_type'] = 'notes'
        _add_document_to_index(doc, pmd, summary_index, "summary")
    
    print("Summary index updated successfully with notes (ChromaDB auto-persists).")


def search_index(query:str, k:int=5, file_locations:FileLocations=FILE_LOCATIONS) \
    -> list[SearchResult]:
    """
    Search the content index for papers matching the query.
    
    This function searches through the content index (PDF documents) for chunks matching
    the query and returns structured SearchResult objects.
    
    Parameters
    ----------
    query : str
        The search query
    k : int, optional
        Maximum number of results to return (default: 5)
    file_locations : FileLocations, optional
        File locations configuration
        
    Returns
    -------
    list[SearchResult]
        List of search results from the content index
        
    Raises
    ------
    IndexError
        If the content index cannot be loaded
    RetrievalError
        If there's an error processing search results
    """
    # Get the content index
    try:
        content_index = _get_or_initialize_index(file_locations, "content")
    except Exception as e:
        raise IndexError(f"Error loading content index: {e}")
    
    # Run the query
    retriever = content_index.as_retriever(similarity_top_k=k)
    chunks = retriever.retrieve(query)
    results = []
    for chunk in chunks:
        try:
            paper_id = chunk.metadata['paper_id']
            summary_filename = paper_id + '.md'
            results.append(SearchResult(
                paper_id=paper_id,
                pdf_filename = chunk.metadata['file_name'],
                summary_filename = summary_filename
                                   if exists(join(file_locations.summaries_dir,
                                             summary_filename))
                                   else None,
                paper_title = chunk.metadata['title'],
                page=int(chunk.metadata['page_label']),
                chunk=chunk.text
            ))
        except Exception as e:
            raise RetrievalError(f"Got an error processing chunk with metadata {chunk.metadata}") from e
    return results


def search_summary_index(query:str, k:int=5, file_locations:FileLocations=FILE_LOCATIONS) \
    -> list[SearchResult]:
    """
    Search the summary index for papers matching the query.
    
    This function searches through the summary index (summaries and notes) for chunks matching
    the query and returns structured SearchResult objects.
    
    Parameters
    ----------
    query : str
        The search query
    k : int, optional
        Maximum number of results to return (default: 5)
    file_locations : FileLocations, optional
        File locations configuration
        
    Returns
    -------
    list[SearchResult]
        List of search results from the summary index
        
    Raises
    ------
    IndexError
        If the summary index cannot be loaded
    RetrievalError
        If there's an error processing search results
    """
    # Get the summary index
    try:
        summary_index = _get_or_initialize_index(file_locations, "summary")
    except Exception as e:
        raise IndexError(f"Error loading summary index: {e}")
    
    # Run the query
    retriever = summary_index.as_retriever(similarity_top_k=k)
    chunks = retriever.retrieve(query)
    results = []
    for chunk in chunks:
        try:
            paper_id = chunk.metadata['paper_id']
            summary_filename = paper_id + '.md'
            
            # For summary index results, we don't have page numbers
            # Instead, we use the source type to indicate what was matched
            source_type = chunk.metadata.get('source_type', 'summary')
            
            results.append(SearchResult(
                paper_id=paper_id,
                pdf_filename = f"{paper_id}.pdf",  # Construct PDF filename
                summary_filename = summary_filename
                                   if exists(join(file_locations.summaries_dir,
                                             summary_filename))
                                   else None,
                paper_title = chunk.metadata['title'],
                page=1,  # Summary/notes don't have page numbers
                chunk=f"[{source_type.upper()}] {chunk.text}"  # Prefix with source type
            ))
        except Exception as e:
            raise RetrievalError(f"Got an error processing chunk with metadata {chunk.metadata}") from e
    return results



def rebuild_index(file_locations:FileLocations=FILE_LOCATIONS):
    """Reindex all the pdf files, summaries, and notes that we have downloaded.

    This function clears the existing content and summary indexes and rebuilds them from scratch using
    all downloaded PDFs, summaries, and notes. It uses the idempotent indexing functions but bypasses the
    idempotency check by clearing the indexes first."""
    global CONTENT_INDEX, SUMMARY_INDEX

    # Reset the global indexes first to release any existing connections
    CONTENT_INDEX = None
    SUMMARY_INDEX = None

    # Get list of papers first (before we mess with the database)
    paper_ids = get_downloaded_paper_ids(file_locations)
    print(f"Found {len(paper_ids)} downloaded papers. Rebuilding content and summary indexes...")

    # Clear the existing content ChromaDB by removing the entire directory
    # This avoids locking issues with trying to delete collections
    content_db_path = _get_chroma_db_path(file_locations, "content")
    if exists(content_db_path):
        print("Clearing old content ChromaDB...")
        rmtree(content_db_path)
        print("Removed content ChromaDB directory")

    # Clear the existing summary ChromaDB by removing the entire directory
    summary_db_path = _get_chroma_db_path(file_locations, "summary")
    if exists(summary_db_path):
        print("Clearing old summary ChromaDB...")
        rmtree(summary_db_path)
        print("Removed summary ChromaDB directory")

    # Wait a moment to ensure file handles are released
    import time
    time.sleep(0.1)

    # Initialize fresh indexes
    CONTENT_INDEX = _initialize_chroma_vector_store(file_locations, "content")
    SUMMARY_INDEX = _initialize_chroma_vector_store(file_locations, "summary")

    content_succeeded = 0
    content_failed = 0
    summary_succeeded = 0
    summary_failed = 0
    notes_succeeded = 0
    notes_failed = 0

    for (paper_num, paper_id) in enumerate(paper_ids):
        print(f"Processing paper {paper_num+1} of {len(paper_ids)}: {paper_id}")
        # get the metadata
        try:
            pmd = get_paper_metadata(paper_id)
        except Exception as e:
            print(f"Unable to get metadata for paper {paper_id}, skipping.")
            content_failed += 1
            continue

        # Index the paper content using the idempotent function
        # Since we cleared the index, all papers will be re-indexed
        try:
            index_file_using_pymupdf_parser(pmd, file_locations)
            content_succeeded += 1
        except Exception as e:
            print(f"Error indexing paper content for {paper_id}: {e}. Skipping.")
            content_failed += 1

        # Try to index summary if it exists
        summary_path = join(file_locations.summaries_dir, f"{pmd.paper_id}.md")
        if exists(summary_path):
            try:
                index_summary(pmd, file_locations)
                summary_succeeded += 1
            except Exception as e:
                print(f"Error indexing summary for {paper_id}: {e}. Skipping.")
                summary_failed += 1

        # Try to index notes if they exist
        notes_path = join(file_locations.notes_dir, f"{pmd.paper_id}.md")
        if exists(notes_path):
            try:
                index_notes(pmd, file_locations)
                notes_succeeded += 1
            except Exception as e:
                print(f"Error indexing notes for {paper_id}: {e}. Skipping.")
                notes_failed += 1

    # Print summary of results
    print(f"Content index: {content_succeeded} papers indexed, {content_failed} failed")
    if summary_succeeded > 0 or summary_failed > 0:
        print(f"Summary index: {summary_succeeded} summaries indexed, {summary_failed} failed")
    if notes_succeeded > 0 or notes_failed > 0:
        print(f"Notes index: {notes_succeeded} notes indexed, {notes_failed} failed")

    if content_succeeded > 0:
        print("Index rebuild completed successfully (ChromaDB auto-persisted).")
    else:
        raise IndexError(f"No papers were reindexed, had {content_failed} content errors.")


def main():
    """Entry point for the rebuild-index script."""
    try:
        rebuild_index()
        print("Rebuild index completed successfully!")
    except Exception as e:
        print(f"Error rebuilding index: {e}")
        exit(1)

