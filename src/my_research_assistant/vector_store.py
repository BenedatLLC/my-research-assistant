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

# Initialize a global variable to hold the VectorStoreIndex object.
# This allows us to maintain the state of the index across multiple calls
# without having to reload it from disk every time.
VECTOR_STORE = None

class IndexError(Exception):
    pass

class RetrievalError(Exception):
    pass


def _get_chroma_db_path(file_locations: FileLocations) -> str:
    """Get the ChromaDB database path for the given file locations."""
    return join(file_locations.index_dir, "chroma_db")


def _initialize_chroma_vector_store(file_locations: FileLocations) -> VectorStoreIndex:
    """Initialize a new ChromaDB vector store."""
    # Ensure the index directory exists
    file_locations.ensure_index_dir()
    
    # Initialize ChromaDB client with persistent storage
    db_path = _get_chroma_db_path(file_locations)
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # Get or create a collection for our papers
    collection = chroma_client.get_or_create_collection("research_papers")
    
    # Create ChromaVectorStore
    vector_store = ChromaVectorStore(chroma_collection=collection)
    
    # Create storage context with the vector store
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create and return the index
    return VectorStoreIndex([], storage_context=storage_context)


def _load_existing_chroma_vector_store(file_locations: FileLocations) -> VectorStoreIndex:
    """Load an existing ChromaDB vector store."""
    db_path = _get_chroma_db_path(file_locations)
    
    if not exists(db_path):
        raise IndexError(f"ChromaDB path {db_path} does not exist")
    
    # Initialize ChromaDB client with persistent storage
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # Get the existing collection
    try:
        collection = chroma_client.get_collection("research_papers")
    except Exception as e:
        raise IndexError(f"Collection 'research_papers' not found: {e}")
    
    # Create ChromaVectorStore
    vector_store = ChromaVectorStore(chroma_collection=collection)
    
    # Create storage context with the vector store
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create and return the index
    return VectorStoreIndex([], storage_context=storage_context)


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


def index_file_using_llama_index_parser(pmd:PaperMetadata, file_locations:FileLocations=FILE_LOCATIONS) -> None:
    """
    Parses, chunks, and indexes a single PDF file, then saves the index to a specified path.
    
    The function loads a PDF document, adds metadata (title, authors, categories), 
    and inserts it into a global VectorStoreIndex. The index is automatically 
    persisted to disk after adding the new document.

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
    global VECTOR_STORE
    # 1. Initialize the global VECTOR_STORE if it's not already set.
    if VECTOR_STORE is None:
        print("VECTOR_STORE is not set. Initializing...")
        
        # Check if ChromaDB already exists
        db_path = _get_chroma_db_path(file_locations)
        if exists(db_path):
            # If the database exists, load the existing index
            print(f"Existing ChromaDB found at {db_path}. Loading into global variable.")
            try:
                VECTOR_STORE = _load_existing_chroma_vector_store(file_locations)
            except Exception as e:
                print(f"Error loading existing ChromaDB: {e}. Creating a new empty index instead.")
                VECTOR_STORE = _initialize_chroma_vector_store(file_locations)
        else:
            # If the database does not exist, create a new instance
            print("No existing ChromaDB found. Creating an empty global index.")
            VECTOR_STORE = _initialize_chroma_vector_store(file_locations)
    
    # 2. Load the new PDF file as a Document.
    local_pdf_path = pmd.get_local_pdf_path(file_locations)
    try:
        reader = SimpleDirectoryReader(input_files=[local_pdf_path])
        documents = reader.load_data()
        
        if not documents:
            raise IndexError(f"Warning: No document loaded from {local_pdf_path}. Skipping.")

    except Exception as e:
        raise IndexError(f"Error loading document from {local_pdf_path}: {e}") from e

    # 3. Insert the new document into the global VECTOR_STORE.
    # This automatically handles chunking and embedding.
    print(f"Adding new document '{local_pdf_path}' with {len(documents)} chunks to the index.")
    for doc in documents:
        # we first add metadata properties to each chunk
        doc.metadata['file_path'] = 'pdfs/' + doc.metadata['file_name']
        doc.metadata['paper_id'] = pmd.paper_id
        doc.metadata['title'] = pmd.title
        doc.metadata['authors'] = ', '.join(pmd.authors)
        doc.metadata['categories'] = ', '.join(pmd.categories)
        VECTOR_STORE.insert(doc)

    # 4. ChromaDB automatically persists changes, no need to manually save
    print("Index updated successfully (ChromaDB auto-persists).")


def index_file_using_pymupdf_parser(pmd:PaperMetadata, file_locations:FileLocations=FILE_LOCATIONS) -> None:
    """
    Parses, chunks, and indexes a single PDF file using PyMuPDF4LLM parser, then saves the index.
    
    This function is similar to index_file_using_llama_index_parser but uses PyMuPDF4LLM's
    LlamaMarkdownReader to create document chunks. The function loads a PDF document, 
    creates chunks using PyMuPDF4LLM, adds metadata (title, authors, categories), 
    and inserts it into a global VectorStoreIndex. The index is automatically 
    persisted to disk after adding the new document.

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
    global VECTOR_STORE
    # 1. Initialize the global VECTOR_STORE if it's not already set.
    if VECTOR_STORE is None:
        print("VECTOR_STORE is not set. Initializing...")
        
        # Check if ChromaDB already exists
        db_path = _get_chroma_db_path(file_locations)
        if exists(db_path):
            # If the database exists, load the existing index
            print(f"Existing ChromaDB found at {db_path}. Loading into global variable.")
            try:
                VECTOR_STORE = _load_existing_chroma_vector_store(file_locations)
            except Exception as e:
                print(f"Error loading existing ChromaDB: {e}. Creating a new empty index instead.")
                VECTOR_STORE = _initialize_chroma_vector_store(file_locations)
        else:
            # If the database does not exist, create a new instance
            print("No existing ChromaDB found. Creating an empty global index.")
            VECTOR_STORE = _initialize_chroma_vector_store(file_locations)
    
    # 2. Load the new PDF file using PyMuPDF4LLM reader.
    local_pdf_path = pmd.get_local_pdf_path(file_locations)
    try:
        llama_reader = pymupdf4llm.LlamaMarkdownReader()
        llama_docs = llama_reader.load_data(local_pdf_path)
        
        if not llama_docs:
            raise IndexError(f"Warning: No document loaded from {local_pdf_path}. Skipping.")

    except Exception as e:
        raise IndexError(f"Error loading document from {local_pdf_path}: {e}") from e

    # 3. Insert the new document into the global VECTOR_STORE.
    # This automatically handles chunking and embedding.
    print(f"Adding new document '{local_pdf_path}' with {len(llama_docs)} chunks to the index.")
    for doc in llama_docs:
        # we first add metadata properties to each chunk
        filename = os.path.basename(local_pdf_path)
        doc.metadata['file_path'] = 'pdfs/' + filename
        doc.metadata['file_name'] = filename
        doc.metadata['paper_id'] = pmd.paper_id
        doc.metadata['title'] = pmd.title
        doc.metadata['authors'] = ', '.join(pmd.authors)
        doc.metadata['categories'] = ', '.join(pmd.categories)
        # Add page_label if not present (use page number from metadata or default to 1)
        if 'page_label' not in doc.metadata:
            page_num = doc.metadata.get('page', 1)
            doc.metadata['page_label'] = str(page_num)
        VECTOR_STORE.insert(doc)

    # 4. ChromaDB automatically persists changes, no need to manually save
    print("Index updated successfully (ChromaDB auto-persists).")


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


def search_index(query:str, k:int=5, file_locations:FileLocations=FILE_LOCATIONS) \
    -> list[SearchResult]:
    # first, load the vector store into memory, if needed
    global VECTOR_STORE
    # 1. Initialize the global VECTOR_STORE if it's not already set.
    if VECTOR_STORE is None:
        # Check if ChromaDB exists
        db_path = _get_chroma_db_path(file_locations)
        if exists(db_path):
            # If the database exists, load the existing index
            try:
                VECTOR_STORE = _load_existing_chroma_vector_store(file_locations)
            except Exception as e:
                raise IndexError(f"Error loading existing ChromaDB: {e}.")
        else:
            raise IndexError(f"No existing ChromaDB found at {db_path}.")
    # now run the query
    retriever = VECTOR_STORE.as_retriever(similarity_top_k=k)
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



def rebuild_index(file_locations:FileLocations=FILE_LOCATIONS):
    """Reindex all the pdf files that we have downloaded.

    First, clears the existing ChromaDB collection or creates a new one. Then, gets the list
    of downloaded papers and finds the metadata for each paper (added to
    the metadata for each chunk). Next, each file is chunked and added
    to the ChromaDB vector store. ChromaDB automatically persists the changes."""
    global VECTOR_STORE
    
    # Reset the global VECTOR_STORE first to release any existing connections
    VECTOR_STORE = None
    
    # Get list of papers first (before we mess with the database)
    paper_ids = get_downloaded_paper_ids(file_locations)
    print(f"Found {len(paper_ids)} downloaded papers. Indexing...")
    
    # Clear the existing ChromaDB by removing the entire directory
    # This avoids locking issues with trying to delete collections
    db_path = _get_chroma_db_path(file_locations)
    if exists(db_path):
        print("Clearing old ChromaDB...")
        rmtree(db_path)
        print("Removed ChromaDB directory")
    
    # Wait a moment to ensure file handles are released
    import time
    time.sleep(0.1)
    
    # Initialize a fresh ChromaDB vector store
    VECTOR_STORE = _initialize_chroma_vector_store(file_locations)
    succeeded = 0
    failed = 0
    for paper_id in paper_ids:
        # get the metadata
        try:
            pmd = get_paper_metadata(paper_id)
        except Exception as e:
            print(f"Unable to get metadata for paper {paper_id}, skipping.")
            failed += 1
            continue
        # load the pdf
        local_pdf_path = pmd.get_local_pdf_path(file_locations)
        try:
            reader = SimpleDirectoryReader(input_files=[local_pdf_path])
            documents = reader.load_data()  
            if not documents:
                print(f"Warning: No document loaded from {local_pdf_path}. Skipping.")
                failed += 1
                continue
        except Exception as e:
            print(f"Error loading document from {local_pdf_path}: {e}. Skipping.")
            failed += 1
            continue

        # Insert the new document into the global VECTOR_STORE.
        # This automatically handles chunking and embedding.
        print(f"Adding new document '{local_pdf_path}' with {len(documents)} chunks to the index.")
        try:
            for doc in documents:
                doc.metadata['file_path'] = 'pdfs/' + doc.metadata['file_name']
                doc.metadata['paper_id'] = pmd.paper_id
                doc.metadata['title'] = pmd.title
                doc.metadata['authors'] = ', '.join(pmd.authors)
                doc.metadata['categories'] = ', '.join(pmd.categories)
                VECTOR_STORE.insert(doc)
        except Exception as e:
            print(f"Error indexing document from {local_pdf_path}: {e}. Skipping.")
            failed += 1
            continue
        succeeded += 1

    if succeeded>0:
        print(f"Processed {succeeded} papers successfully, {failed} had errors.")
        print("Index rebuild completed successfully (ChromaDB auto-persisted).")
    else:
        raise IndexError(f"No papers were reindexed, had {failed} errors.")


def main():
    """Entry point for the rebuild-index script."""
    try:
        rebuild_index()
        print("Rebuild index completed successfully!")
    except Exception as e:
        print(f"Error rebuilding index: {e}")
        exit(1)

