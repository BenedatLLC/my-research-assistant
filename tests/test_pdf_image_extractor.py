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


@pytest.mark.skip("This code needs some more work before we can include it")
def test_extract_images_from_pdf(temp_file_locations):
    """Test composite image extraction from PDF with visual region analysis"""
    from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
    from my_research_assistant.pdf_image_extractor import extract_images_from_pdf
    
    # Download the test paper
    md = get_paper_metadata(EXAMPLE_PAPER_ID)
    local_pdf_path = download_paper(md, temp_file_locations)
    assert exists(local_pdf_path)
    
    # Temporarily replace the global FILE_LOCATIONS
    from my_research_assistant import summarizer
    original_file_locations = summarizer.FILE_LOCATIONS
    summarizer.FILE_LOCATIONS = temp_file_locations
    
    try:
        # Extract composite images with a description
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
            
            # Composite images should be larger than individual embedded images
            assert len(image_data) > 10000, f"Composite image {image_filename} should be larger than 10KB"
            
            # Image should be openable by PIL
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            # Composite images should have reasonable dimensions (larger than individual pieces)
            assert width >= 100 and height >= 100, f"Composite image {image_filename} should be at least 100x100 pixels, got {width}x{height}"
            
            # Verify it's saved as PNG (our composite format)
            assert image_filename.endswith('.png'), f"Composite image {image_filename} should be PNG format"
            
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

