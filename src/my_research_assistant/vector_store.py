import os
import datetime
from os.path import isdir, exists, join
from shutil import rmtree
from typing import Optional
import chromadb
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.schema import Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from .file_locations import FILE_LOCATIONS, FileLocations
from .types import PaperMetadata, SearchResult
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


def index_file(pmd:PaperMetadata, file_locations:FileLocations=FILE_LOCATIONS) -> str:
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
    str
        The concatenated text content of all document chunks.

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
    result_text = []
    for doc in documents:
        doc.metadata['file_path'] = 'pdfs/' + doc.metadata['file_name']
        doc.metadata['paper_id'] = pmd.paper_id
        doc.metadata['title'] = pmd.title
        doc.metadata['authors'] = ', '.join(pmd.authors)
        doc.metadata['categories'] = ', '.join(pmd.categories)
        result_text.append(doc.text)
        VECTOR_STORE.insert(doc)

    # 4. ChromaDB automatically persists changes, no need to manually save
    print("Index updated successfully (ChromaDB auto-persists).")
    return ''.join(result_text)

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

