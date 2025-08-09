import os
import datetime
from typing import Optional
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.schema import Document
from .file_locations import FILE_LOCATIONS
from .types import PaperMetadata

# Initialize a global variable to hold the VectorStoreIndex object.
# This allows us to maintain the state of the index across multiple calls
# without having to reload it from disk every time.
VECTOR_STORE = None

class IndexError(Exception):
    pass

def index_file(pmd:PaperMetadata) -> str:
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
    index_path = FILE_LOCATIONS.index_dir
    # 1. Initialize the global VECTOR_STORE if it's not already set.
    if VECTOR_STORE is None:
        print("VECTOR_STORE is not set. Initializing...")
        
        # Check if the storage directory exists.
        if os.path.exists(index_path) and os.listdir(index_path):
            # If the directory exists, load the existing index from it.
            print(f"Existing index found at {index_path}. Loading into global variable.")
            try:
                storage_context = StorageContext.from_defaults(persist_dir=index_path)
                VECTOR_STORE = load_index_from_storage(storage_context)
            except Exception as e:
                print(f"Error loading existing index: {e}. Creating a new empty index instead.")
                VECTOR_STORE = VectorStoreIndex([]) # Create an empty index
        else:
            # If the directory does not exist, create an empty instance of the index.
            print("No existing index found. Creating an empty global index.")
            VECTOR_STORE = VectorStoreIndex([])
    
    # 2. Load the new PDF file as a Document.
    local_pdf_path = pmd.get_local_pdf_path(FILE_LOCATIONS)
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
        doc.metadata['title'] = pmd.title
        doc.metadata['authors'] = ', '.join(pmd.authors)
        doc.metadata['categories'] = ', '.join(pmd.categories)
        result_text.append(doc.text)
        VECTOR_STORE.insert(doc)

    # 4. Save the current state of the index to disk.
    # This persists the changes made to the global VECTOR_STORE object.
    print(f"Saving the updated index state to {index_path}.")
    VECTOR_STORE.storage_context.persist(persist_dir=index_path)
    print("Index saved successfully.")
    return ''.join(result_text)


