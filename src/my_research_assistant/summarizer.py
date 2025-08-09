"""Tools to summarize papers"""

import textwrap
from os.path import join
from typing import Optional
import io
from llama_index.llms.openai import OpenAI
import fitz  # PyMuPDF
from PIL import Image

from .types import PaperMetadata
from .file_locations import FILE_LOCATIONS

# Define the prompt for summarization
# This prompt guides the LLM to produce the desired structured output in Markdown.
summarization_prompt = """
Please summarize the following text block into a markdown document.
The summary should include the following sections:

1.  **Key ideas of the paper**: Briefly describe the main contributions and core concepts.
2.  **Implementation approach**: Explain how the proposed method is built and works.
3.  **Experiments**: Detail the experimental setup, datasets used, and key results.
4.  **Related work**: Discuss how this work relates to and differs from previous research.

The title of the markdown summary should be the title of the paper using a markdown level 1 header
("#").

---
Text to summarize:
{{text_block}}
---

Markdown Summary:
"""

class SummarizationError(Exception):
    pass


def extract_markdown(text:str) -> str:
    """Look to see if the response has a ``` block of type markdown. If so,
    extract that text and return it. Otherwise, return all of the text."""
    import re
    
    # Look for markdown code blocks with ```markdown
    markdown_pattern = r'```markdown\s*\n(.*?)\n```'
    match = re.search(markdown_pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # Also check for ```md as an alternative
    md_pattern = r'```md\s*\n(.*?)\n```'
    match = re.search(md_pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # If no markdown code block found, return the original text
    return text.strip()

def insert_metadata(markdown:str,
                    pmd:PaperMetadata) -> str:
    """We want to put the paper metadata just after the summary's title.
    """
    found_title = False
    result = []
    for line in markdown.splitlines(keepends=True):
        if (not found_title) and line.strip().startswith('# '):
            result.append(line)
            result.append("\n")
            result.append(f"* Paper id: {pmd.paper_id}\n")
            result.append(f"* Authors: {', '.join(pmd.authors)}\n")
            result.append(f"* Categories: {', '.join(pmd.categories)}\n")
            result.append(f"* Published: {pmd.published}\n")
            if pmd.updated is not None:
                result.append(f"* Updated: {pmd.updated}\n")
            result.append(f"* Paper URL: {pmd.paper_abs_url}\n")
            if pmd.abstract is not None:
                result.append("\n## Abstract\n")
                result.append(textwrap.fill(pmd.abstract) + '\n\n')
            found_title = True
        else:
            result.append(line)
    if found_title:
        return ''.join(result)
    else:
        raise SummarizationError("Generated markdown did not contain a title")


def summarize_paper(text:str, pmd:PaperMetadata) -> str:
    print(f"Generating summary for text of {len(text)} characters...")

    try:
        llm = OpenAI(model='gpt-4.1')
        # Make the LLM call to get the summary
        response = llm.complete(summarization_prompt.replace('{{text_block}}', text))
        markdown = insert_metadata(extract_markdown(response.text), pmd)
        return markdown
    except SummarizationError:
        raise
    except Exception as e:
        raise SummarizationError(f"An error occurred during summarizing: {e}") from e


def save_summary(markdown:str, paper_id:str) -> str:
    """Save a markdown summary. Returns the path"""
    FILE_LOCATIONS.ensure_summaries_dir()
    file_path = join(FILE_LOCATIONS.summaries_dir, paper_id + '.md')
    with open(file_path, 'w') as f:
        f.write(markdown)
    return file_path

class ImageExtractError(Exception):
    pass

def extract_images_from_pdf(pdf_filename: str, description: str, limit:int=3) -> Optional[list[str]]:
    """
    Extracts images from a specified PDF file that match a given textual description.

    This tool is useful when a user asks to "get," "find," or "extract" a picture
    of something specific from a PDF document.

    Args:
        pdf_filename (str): The filename of the PDF document.
        description (str): A clear, descriptive text of the image to find (e.g., "a cat sitting on a mat," "the company logo").

    Returns:
        list[str], optional: A list of the images that were extracted and saved, based on the description.
    """
    pdf_path = join(FILE_LOCATIONS.pdfs_dir, pdf_filename)
    print(f"\nTool activated: Attempting to extract images matching '{description}' from '{pdf_path}'...")
    
    def is_meaningful_image(image_bytes, min_size=1000, min_dimension=50):
        """Check if an image has meaningful content (not just a black rectangle or tiny image)"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Filter out very small images
            width, height = image.size
            if width < min_dimension or height < min_dimension:
                return False, None
                
            # Filter out very small file sizes (likely empty or placeholder images)
            if len(image_bytes) < min_size:
                return False, None
                
            # Check if image is mostly black/empty by converting to grayscale and checking histogram
            try:
                # Convert to grayscale for easier analysis
                if image.mode != 'L':
                    gray_image = image.convert('L')
                else:
                    gray_image = image
                
                # Get histogram and check if most pixels are very dark
                histogram = gray_image.histogram()
                total_pixels = width * height
                
                # Count pixels in the first 20 brightness levels (very dark)
                dark_pixels = sum(histogram[:20])
                dark_ratio = dark_pixels / total_pixels
                
                # If more than 90% of pixels are very dark, consider it empty
                if dark_ratio > 0.9:
                    return False, None
                    
            except Exception:
                # If histogram analysis fails, fall back to extrema
                extrema = image.getextrema()
                if hasattr(extrema, '__len__') and len(extrema) >= 2:
                    if isinstance(extrema[0], tuple):
                        # RGB mode: check max values in all channels
                        max_brightness = max(channel[1] if isinstance(channel, tuple) else channel for channel in extrema)
                    else:
                        # Grayscale mode
                        max_brightness = extrema[1] if isinstance(extrema[1], (int, float)) else 255
                    
                    if max_brightness <= 10:
                        return False, None
                    
            return True, image
        except Exception:
            return False, None
    
    try:
        doc = fitz.open(pdf_path)
        image_files = []
        
        # Iterate through each page of the PDF
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Get all images on the current page
            image_list = page.get_images(full=True)
            print(f"Found {len(image_list)} images on page {page_num + 1}")
            
            if not image_list:
                continue

            # Get all text on the page to provide context for the LLM
            page_text = page.get_text()  # type: ignore

            # For each image, check if it's meaningful and matches the description
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_ext = base_image['ext']
                image_bytes = base_image["image"]
                
                print(f"Image {img_index + 1}: {base_image['width']}x{base_image['height']}, {base_image['ext']}, {base_image['size']} bytes")
                
                # First, check if this is a meaningful image
                is_meaningful, pil_image = is_meaningful_image(image_bytes)
                if not is_meaningful or pil_image is None:
                    print(f"  Skipping image {img_index + 1}: appears to be empty/placeholder")
                    continue
                    
                print(f"  Image {img_index + 1} appears to have meaningful content")
                
                # Use the LLM to determine if the image is relevant
                # We provide the page text as context to help the LLM decide.
                prompt = f"""
                You are an assistant that determines if an image is relevant based on surrounding text.
                The user wants to find an image of: '{description}'.
                The text on the page where an image was found is:
                ---
                {page_text}
                ---
                Based on this text, is it likely that this image is what the user is looking for?
                Respond with only 'yes' or 'no'.
                """
                
                # We use a separate, lightweight LLM call here inside the tool
                llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
                response = llm.complete(prompt)
                print(f"  LLM response: {response.text.strip()}")
                
                # Check the LLM's decision
                if response.text.strip().lower() == 'yes':
                    print(f"  LLM confirmed image on page {page_num + 1} matches description.")
                    image_filename = f"extracted_page{page_num+1}_img{img_index+1}.{image_ext}"
                    image_filepath = join(FILE_LOCATIONS.images_dir, image_filename)
                    
                    # Save the image
                    FILE_LOCATIONS.ensure_images_dir()
                    pil_image.save(image_filepath)
                    print(f"  Saved image to '{image_filepath}'")
                    image_files.append(image_filename)
                    
                    if len(image_files) >= limit:
                        break
                        
            if len(image_files) >= limit:
                print(f"Reached limit of {limit} image files, stopping early.")
                break

        doc.close()

        if len(image_files) > 0:
            print(f"Successfully extracted {len(image_files)} image(s) matching '{description}' and saved them in the '{FILE_LOCATIONS.images_dir}' directory.")
            return image_files
        else:
            print(f"Could not find any images matching the description '{description}' in the document.")
            return None

    except FileNotFoundError as e:
        raise ImageExtractError(f"Error: The file at '{pdf_path}' was not found.") from e
    except Exception as e:
        raise ImageExtractError(f"An unexpected error occurred: {e}") from e