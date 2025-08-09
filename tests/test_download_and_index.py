
import tempfile
import pytest
from os.path import exists
from my_research_assistant import file_locations

EXAMPLE_PAPER_ID='2503.22738'


@pytest.fixture
def temp_file_locations():
    """Create a temporary directory and set FILE_LOCATIONS to use it.
    After the test, restore the original FILE_LOCATIONS.
    """
    # Save the original FILE_LOCATIONS
    original_file_locations = file_locations.FILE_LOCATIONS
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create new FileLocations pointing to the temp directory
        temp_locations = file_locations.FileLocations.get_locations(temp_dir)
        
        # Replace the module-level FILE_LOCATIONS
        file_locations.FILE_LOCATIONS = temp_locations
        
        try:
            yield temp_locations
        finally:
            # Restore the original FILE_LOCATIONS
            file_locations.FILE_LOCATIONS = original_file_locations


def test_pdf_download(temp_file_locations):
    """Download the pdf for an arxiv paper and validate some of its metadata"""
    from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
    md = get_paper_metadata(EXAMPLE_PAPER_ID)
    assert md.title=="ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning"
    assert len(md.authors)==3
    
    local_pdf_path = download_paper(md, temp_file_locations)
    assert exists(local_pdf_path)
    
    # Also test that the method on the metadata works
    expected_path = md.get_local_pdf_path(temp_file_locations)
    assert exists(expected_path)


def test_pdf_index(temp_file_locations):
    from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
    md = get_paper_metadata(EXAMPLE_PAPER_ID)
    download_paper(md, temp_file_locations)
    import my_research_assistant.vector_store as vs
    vs.index_file(md)
    rtr = vs.VECTOR_STORE.as_retriever()
    response = rtr.retrieve('shielding agents')
    print(response)

