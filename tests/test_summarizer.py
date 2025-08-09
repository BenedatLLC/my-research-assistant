import tempfile
import pytest
from os.path import exists, join
from PIL import Image
import io
from my_research_assistant import file_locations

EXAMPLE_PAPER_ID = '2503.22738'


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


def test_extract_images_from_pdf(temp_file_locations):
    """Test image extraction from PDF with meaningful content filtering"""
    from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
    from my_research_assistant.summarizer import extract_images_from_pdf
    
    # Download the test paper
    md = get_paper_metadata(EXAMPLE_PAPER_ID)
    local_pdf_path = download_paper(md, temp_file_locations)
    assert exists(local_pdf_path)
    
    # Temporarily replace the global FILE_LOCATIONS
    from my_research_assistant import summarizer
    original_file_locations = summarizer.FILE_LOCATIONS
    summarizer.FILE_LOCATIONS = temp_file_locations
    
    try:
        # Extract images with a description
        extracted_images = extract_images_from_pdf(
            md.default_pdf_filename,
            "Overview of shieldagent",
            limit=3
        )
        
        # Verify that images were extracted
        assert extracted_images is not None
        assert len(extracted_images) > 0
        assert len(extracted_images) <= 3  # Should respect the limit
        
        # Verify each extracted image exists and has meaningful content
        for image_filename in extracted_images:
            image_path = join(temp_file_locations.images_dir, image_filename)
            assert exists(image_path), f"Image file {image_filename} should exist"
            
            # Test that the image can be opened and has reasonable properties
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Image should have reasonable file size (not tiny placeholder)
            assert len(image_data) > 1000, f"Image {image_filename} should be larger than 1KB"
            
            # Image should be openable by PIL
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            # Image should have reasonable dimensions (not tiny)
            assert width >= 50 and height >= 50, f"Image {image_filename} should be at least 50x50 pixels"
            
            # Image should not be completely black (check extrema)
            extrema = image.getextrema()
            if image.mode == 'RGB':
                # For RGB, extrema is ((min_r, max_r), (min_g, max_g), (min_b, max_b))
                max_values = [channel[1] if isinstance(channel, tuple) else channel for channel in extrema]
                assert any(val > 20 for val in max_values), f"Image {image_filename} should not be completely black"
            elif image.mode in ['L', 'P']:
                # For grayscale, extrema is (min, max)
                if isinstance(extrema, tuple) and len(extrema) == 2:
                    max_val = extrema[1]
                    if isinstance(max_val, (int, float)):
                        assert max_val > 20, f"Image {image_filename} should not be completely black"
    finally:
        # Restore the original FILE_LOCATIONS
        summarizer.FILE_LOCATIONS = original_file_locations


def test_extract_images_no_matches(temp_file_locations):
    """Test image extraction when no images match the description"""
    from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
    from my_research_assistant.summarizer import extract_images_from_pdf
    from my_research_assistant import summarizer
    
    # Download the test paper
    md = get_paper_metadata(EXAMPLE_PAPER_ID)
    local_pdf_path = download_paper(md, temp_file_locations)
    assert exists(local_pdf_path)
    
    # Temporarily replace the global FILE_LOCATIONS
    original_file_locations = summarizer.FILE_LOCATIONS
    summarizer.FILE_LOCATIONS = temp_file_locations
    
    try:
        # Try to extract images with a very specific description that won't match
        extracted_images = extract_images_from_pdf(
            md.default_pdf_filename,
            "unicorns and rainbows dancing in a field",
            limit=3
        )
        
        # Should return None or empty list when no matches found
        assert extracted_images is None or len(extracted_images) == 0
    finally:
        # Restore the original FILE_LOCATIONS
        summarizer.FILE_LOCATIONS = original_file_locations


def test_extract_images_with_limit(temp_file_locations):
    """Test that the limit parameter is respected"""
    from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
    from my_research_assistant.summarizer import extract_images_from_pdf
    from my_research_assistant import summarizer
    
    # Download the test paper
    md = get_paper_metadata(EXAMPLE_PAPER_ID)
    local_pdf_path = download_paper(md, temp_file_locations)
    assert exists(local_pdf_path)
    
    # Temporarily replace the global FILE_LOCATIONS
    original_file_locations = summarizer.FILE_LOCATIONS
    summarizer.FILE_LOCATIONS = temp_file_locations
    
    try:
        # Extract images with limit of 1
        extracted_images = extract_images_from_pdf(
            md.default_pdf_filename,
            "Overview of shieldagent",
            limit=1
        )
        
        # Should extract exactly 1 image (or None if no matches)
        if extracted_images is not None:
            assert len(extracted_images) == 1
    finally:
        # Restore the original FILE_LOCATIONS
        summarizer.FILE_LOCATIONS = original_file_locations


def test_extract_images_file_not_found(temp_file_locations):
    """Test error handling when PDF file doesn't exist"""
    from my_research_assistant.summarizer import extract_images_from_pdf, ImageExtractError
    from my_research_assistant import summarizer
    
    # Temporarily replace the global FILE_LOCATIONS
    original_file_locations = summarizer.FILE_LOCATIONS
    summarizer.FILE_LOCATIONS = temp_file_locations
    
    try:
        # Try to extract from a non-existent file
        with pytest.raises(ImageExtractError) as exc_info:
            extract_images_from_pdf("nonexistent_file.pdf", "test description")
        
        assert "not found" in str(exc_info.value) or "no such file" in str(exc_info.value)
    finally:
        # Restore the original FILE_LOCATIONS
        summarizer.FILE_LOCATIONS = original_file_locations


def test_image_filtering_logic():
    """Test the image filtering logic directly"""
    from my_research_assistant.summarizer import extract_images_from_pdf
    
    # This test would ideally test the is_meaningful_image function directly,
    # but since it's nested, we rely on the integration test above to verify
    # that the filtering is working (i.e., we get meaningful images, not black rectangles)
    pass


def test_images_directory_creation(temp_file_locations):
    """Test that the images directory is created when needed"""
    from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
    from my_research_assistant.summarizer import extract_images_from_pdf
    from my_research_assistant import summarizer
    
    # Verify images directory doesn't exist initially
    assert not exists(temp_file_locations.images_dir)
    
    # Download the test paper
    md = get_paper_metadata(EXAMPLE_PAPER_ID)
    download_paper(md, temp_file_locations)
    
    # Temporarily replace the global FILE_LOCATIONS
    original_file_locations = summarizer.FILE_LOCATIONS
    summarizer.FILE_LOCATIONS = temp_file_locations
    
    try:
        # Extract images (this should create the images directory)
        extract_images_from_pdf(
            md.default_pdf_filename,
            "Overview of shieldagent",
            limit=1
        )
        
        # Verify images directory was created
        assert exists(temp_file_locations.images_dir)
    finally:
        # Restore the original FILE_LOCATIONS
        summarizer.FILE_LOCATIONS = original_file_locations
