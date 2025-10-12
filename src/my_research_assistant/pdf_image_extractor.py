import openai
import fitz  # PyMuPDF
import base64
import json
import os
import io
import numpy as np
from os.path import join, basename
from llama_index.llms.openai import OpenAI
from PIL import Image
from typing import Optional, Dict, Any

from .file_locations import FILE_LOCATIONS
from .models import DEFAULT_MODEL


class ImageExtractError(Exception):
    pass


PROMPT=\
"""You are extracting a figure from a PDF page image.

Goal:
Locate the Figure that best matches the following description:
'{{description}}'

Bounding box rules (highest priority):
1. Must contain ONLY the graphical content of the figure.
2. Must NOT contain:
   - Caption text
   - Body text
   - Page headers/footers
3. Legends, axis labels, or embedded text that are physically part of the figure are allowed.
4. If unsure whether something belongs in the figure, EXCLUDE it.

Detecting the caption boundary:
- Look for a horizontal whitespace band, a visual divider line, or a change in font size that separates the figure from its caption.
- If the figure touches the caption with no visible divider, crop *above* the caption text line.
- Never extend the bounding box below the top of the caption, even if it means trimming part of the bottom of the figure.

Process:
Step 1: Identify the figure matching the description.
Step 2: Find the lowest pixel row that contains graphical content before whitespace/divider/caption text starts.
Step 3: Crop the bounding box at that point or higher.
Step 4: Output the caption text separately.

Output format:
{
  "region": { "x1": <fraction>, "y1": <fraction>, "x2": <fraction>, "y2": <fraction> },
  "caption": "<exact caption text as it appears>"
}

✅ Correct Example (tight crop above caption):
{
  "region": { "x1": 0.16, "y1": 0.24, "x2": 0.49, "y2": 0.54 },
  "caption": "Figure 2: Comparison of algorithm accuracy over datasets."
}

❌ Incorrect Example (includes caption):
{
  "region": { "x1": 0.16, "y1": 0.24, "x2": 0.49, "y2": 0.69 }
}
Reason: Bounding box includes both the figure and its caption text.

If no matching figure is found, return: {}

"""

def find_and_extract_image(
    pdf_filename: str,
    page_number:int,
    description: str,
) -> Optional[tuple[str, str]]:
    """
    Finds the closest matching image in a local PDF based on a text description,
    extracts it using AI-identified regions, and saves it.

    Args:
        pdf_path (str): The file path to the local PDF document.
        description (str): The text description of the image to find.
        output_dir (str): The directory where the extracted image will be saved.

    Returns:
        tuple[str,str], optional:
            If the image is found, returns a pair of strings - the path to the generated image
            and the caption. Otherwise returns None if no image was found.
    """
    try:
        client = openai.OpenAI() # TODO: cache the client in a global
    except KeyError:
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("Please create a .env file and add your key: OPENAI_API_KEY='your-key'")


    pdf_path = join(FILE_LOCATIONS.pdfs_dir, pdf_filename)
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at '{pdf_path}'")
        return None
    output_dir = FILE_LOCATIONS.images_dir

    try:
        # 1. Convert PDF pages to base64 encoded images
        print(f"Processing PDF '{os.path.basename(pdf_path)}'...")
        base64_images = []
        doc = fitz.open(pdf_path)
        if page_number>len(doc):
            raise Exception(f"Document has {len(doc)} pages, but page {page_number} was requested.")
        #for page_num in range(len(doc)):
        #    page = doc.load_page(page_num)
        #    # Use a high-DPI pixmap for better quality analysis by the AI
        #    pix = page.get_pixmap(dpi=150)
        #    img_bytes = pix.tobytes("png")
        #    base64_images.append(base64.b64encode(img_bytes).decode('utf-8'))
        page = doc.load_page(page_number-1)
        # Use a high-DPI pixmap for better quality analysis by the AI
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        base64_images.append(base64.b64encode(img_bytes).decode('utf-8'))
        doc.close()
        print(f"Successfully converted {len(base64_images)} pages to images.")

        # 2. Construct the prompt for OpenAI
        messages = [
            {
                "role": "system",
                "content": "You are an expert document analysis AI for research papers. Your task is to find a specific image region corresponding to a figure in a research paper, "
                "based on a user's description. Respond ONLY with a valid JSON object."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT.replace('{{description}}', description)
                    },
                    {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_images[0]}"}
                    }
                ]
            }
        ]

        # 3. Call the OpenAI API
        print("Sending request to OpenAI to find the image region...")
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            #max_completion_tokens=500
        )

        response_content = response.choices[0].message.content
        print(f"Received response from OpenAI: {response_content}")

        # 4. Parse the response
        try:
            result = json.loads(response_content)
        except json.JSONDecodeError:
            print("Error: OpenAI returned a non-JSON response.")
            print(repr(response))
            return None

        if not result or "region" not in result:
            print("OpenAI could not find a matching image region in the document.")
            return None

        region = result["region"]
        if 'caption' in result:
            caption = result['caption']
        else:
            caption = ""

        # 5. Extract the image region from the original PDF for maximum quality
        print(f"Extracting region from page {page_number}...")
        doc = fitz.open(pdf_path)

        page = doc.load_page(page_number-1)
        page_rect = page.rect # The page's dimensions in points

        # Convert fractional coordinates to absolute PDF points
        clip_rect = fitz.Rect(
            page_rect.width * region['x1'],
            page_rect.height * region['y1'],
            page_rect.width * region['x2'],
            page_rect.height * region['y2']
        )

        # Get a pixmap of just the clipped region
        pix = page.get_pixmap(clip=clip_rect, dpi=300) # Use high DPI for output
        doc.close()

        # 6. Save the extracted image
        FILE_LOCATIONS.ensure_images_dir()
        image_basename=pdf_filename.replace('.pdf', '')
        desc_for_filename = description[0:20].replace(' ', '_')
        output_filename = f"{image_basename}_p{page_number}_{desc_for_filename}.png"
        output_path = os.path.join(output_dir, output_filename)

        # Use Pillow to save the image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(output_path)

        print(f"Successfully extracted and saved image to '{output_path}'")
        return output_path, caption

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


# This version will do the work using pil and local heuristics
def extract_images_from_pdf(pdf_filename: str, description: str, limit:int=3) -> Optional[list[str]]:
    """
    Extracts composite images from a specified PDF file that match a given textual description.
    
    This function renders each page and analyzes visual content to extract meaningful 
    composite images (like figures made of multiple elements) rather than just 
    individual embedded image objects.

    Args:
        pdf_filename (str): The filename of the PDF document.
        description (str): A clear, descriptive text of the image to find (e.g., "a cat sitting on a mat," "the company logo").

    Returns:
        list[str], optional: A list of the images that were extracted and saved, based on the description.
    """
    pdf_path = join(FILE_LOCATIONS.pdfs_dir, pdf_filename)
    print(f"\nTool activated: Attempting to extract composite images matching '{description}' from '{pdf_path}'...")
    
    def find_image_regions(page_pixmap, min_area=50000):
        """Find regions on the page that likely contain meaningful visual content"""
        import numpy as np
        from PIL import Image, ImageOps
        
        # Convert pixmap to PIL Image
        img_data = page_pixmap.tobytes("ppm")
        pil_image = Image.open(io.BytesIO(img_data))
        
        # Convert to grayscale for analysis
        gray = pil_image.convert('L')
        
        # Convert to numpy array for processing
        img_array = np.array(gray)
        
        # Find regions with significant content by looking for areas with variation
        # Use a simple approach: look for rectangular regions that aren't mostly white/empty
        regions = []
        
        height, width = img_array.shape
        
        # Divide the page into a grid and analyze each cell
        grid_size = 50  # Size of each grid cell
        
        for y in range(0, height - grid_size, grid_size // 2):
            for x in range(0, width - grid_size, grid_size // 2):
                # Extract a region
                region = img_array[y:y+grid_size, x:x+grid_size]
                
                # Check if this region has interesting content
                std_dev = np.std(region)
                mean_brightness = np.mean(region)
                
                # Look for regions with good variation (not too uniform) and not too bright (not just white space)
                if std_dev > 20 and mean_brightness < 240:
                    # Expand this region to find the full extent of the visual content
                    expanded_region = expand_region(img_array, x, y, grid_size, grid_size)
                    if expanded_region and (expanded_region[2] - expanded_region[0]) * (expanded_region[3] - expanded_region[1]) >= min_area:
                        regions.append(expanded_region)
        
        # Merge overlapping regions
        merged_regions = merge_overlapping_regions(regions)
        
        return merged_regions, pil_image
    
    def expand_region(img_array, start_x, start_y, initial_w, initial_h):
        """Expand a region to include all connected visual content"""
        height, width = img_array.shape
        
        # Find the bounds of non-white content around this point
        min_x, max_x = start_x, min(start_x + initial_w, width)
        min_y, max_y = start_y, min(start_y + initial_h, height)
        
        # Expand outward to find the full extent
        # Look left
        for x in range(start_x, -1, -1):
            col = img_array[min_y:max_y, x]
            if np.mean(col) > 230 and np.std(col) < 10:  # Mostly white/empty
                break
            min_x = x
        
        # Look right  
        for x in range(start_x + initial_w, width):
            col = img_array[min_y:max_y, x]
            if np.mean(col) > 230 and np.std(col) < 10:  # Mostly white/empty
                break
            max_x = x
            
        # Look up
        for y in range(start_y, -1, -1):
            row = img_array[y, min_x:max_x]
            if np.mean(row) > 230 and np.std(row) < 10:  # Mostly white/empty
                break
            min_y = y
            
        # Look down
        for y in range(start_y + initial_h, height):
            row = img_array[y, min_x:max_x]
            if np.mean(row) > 230 and np.std(row) < 10:  # Mostly white/empty
                break
            max_y = y
        
        # Add some padding
        padding = 10
        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        max_x = min(width, max_x + padding)
        max_y = min(height, max_y + padding)
        
        return (min_x, min_y, max_x, max_y)
    
    def merge_overlapping_regions(regions):
        """Merge regions that overlap significantly"""
        if not regions:
            return []
            
        # Sort regions by area (largest first)
        regions = sorted(regions, key=lambda r: (r[2]-r[0])*(r[3]-r[1]), reverse=True)
        
        merged = []
        for region in regions:
            x1, y1, x2, y2 = region
            
            # Check if this region overlaps significantly with any existing merged region
            overlapped = False
            for i, existing in enumerate(merged):
                ex1, ey1, ex2, ey2 = existing
                
                # Calculate overlap
                overlap_x = max(0, min(x2, ex2) - max(x1, ex1))
                overlap_y = max(0, min(y2, ey2) - max(y1, ey1))
                overlap_area = overlap_x * overlap_y
                
                region_area = (x2 - x1) * (y2 - y1)
                existing_area = (ex2 - ex1) * (ey2 - ey1)
                
                # If overlap is significant, merge the regions
                if overlap_area > 0.3 * min(region_area, existing_area):
                    # Merge by taking the bounding box of both regions
                    merged[i] = (min(x1, ex1), min(y1, ey1), max(x2, ex2), max(y2, ey2))
                    overlapped = True
                    break
            
            if not overlapped:
                merged.append(region)
        
        return merged
    
    def is_meaningful_region(pil_image, region, min_dimension=100):
        """Check if a region contains meaningful visual content"""
        x1, y1, x2, y2 = region
        width = x2 - x1
        height = y2 - y1
        
        # Must be reasonably sized
        if width < min_dimension or height < min_dimension:
            return False
            
        # Extract the region
        region_image = pil_image.crop((x1, y1, x2, y2))
        
        # Convert to grayscale for analysis
        gray_region = region_image.convert('L')
        
        # Check if it has meaningful content (not just white space)
        import numpy as np
        region_array = np.array(gray_region)
        
        # Calculate statistics
        std_dev = np.std(region_array)
        mean_brightness = np.mean(region_array)
        
        # Good content should have variation and not be too bright
        return std_dev > 15 and mean_brightness < 230

    try:
        doc = fitz.open(pdf_path)
        image_files = []
        
        # Iterate through each page of the PDF
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            print(f"Analyzing page {page_num + 1} for composite images...")
            
            # Render the page at high resolution
            matrix = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pixmap = page.get_pixmap(matrix=matrix)  # type: ignore
            
            # Get all text on the page for LLM context
            page_text = page.get_text()  # type: ignore
            
            # Find visual regions on the page
            try:
                regions, full_page_image = find_image_regions(pixmap)
                print(f"Found {len(regions)} potential image regions on page {page_num + 1}")
            except Exception as e:
                print(f"Error analyzing page {page_num + 1}: {e}")
                continue
            
            # Process each region
            for region_idx, region in enumerate(regions):
                if not is_meaningful_region(full_page_image, region):
                    continue
                    
                print(f"  Analyzing region {region_idx + 1}: {region}")
                
                # Extract the region as an image
                x1, y1, x2, y2 = region
                region_image = full_page_image.crop((x1, y1, x2, y2))
                
                # Use LLM to determine if this region matches the description
                prompt = f"""
                You are an assistant that determines if an image region is relevant based on surrounding text.
                The user wants to find an image of: '{description}'.
                The text on the page where this visual region was found is:
                ---
                {page_text}
                ---
                This appears to be a visual region (possibly a figure, chart, or diagram) from the page.
                Based on the page text and the request, is it likely that this visual region contains what the user is looking for?
                Respond with only 'yes' or 'no'.
                """
                
                llm = OpenAI(model=DEFAULT_MODEL, temperature=0)
                response = llm.complete(prompt)
                print(f"    LLM response: {response.text.strip()}")
                
                # Check the LLM's decision
                if response.text.strip().lower() == 'yes':
                    print(f"    LLM confirmed region on page {page_num + 1} matches description.")
                    
                    # Save the region as an image
                    image_filename = f"extracted_page{page_num+1}_region{region_idx+1}.png"
                    image_filepath = join(FILE_LOCATIONS.images_dir, image_filename)
                    
                    FILE_LOCATIONS.ensure_images_dir()
                    region_image.save(image_filepath, "PNG", optimize=True)
                    print(f"    Saved composite image to '{image_filepath}'")
                    image_files.append(image_filename)
                    
                    if len(image_files) >= limit:
                        break
                        
            if len(image_files) >= limit:
                print(f"Reached limit of {limit} image files, stopping early.")
                break

        doc.close()

        if len(image_files) > 0:
            print(f"Successfully extracted {len(image_files)} composite image(s) matching '{description}' and saved them in the '{FILE_LOCATIONS.images_dir}' directory.")
            return image_files
        else:
            print(f"Could not find any composite images matching the description '{description}' in the document.")
            return None

    except FileNotFoundError as e:
        raise ImageExtractError(f"Error: The file at '{pdf_path}' was not found.") from e
    except Exception as e:
        raise ImageExtractError(f"An unexpected error occurred: {e}") from e