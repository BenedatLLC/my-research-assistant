"""Uses the google custom search api to find papers
See https://developers.google.com/custom-search/v1/introduction for details.
You need a custom search engine that restricts searches to arxiv.org (so we only
get arXiv papers as the matches).

There are two environment variables that must be set to use this:
GOOGLE_SEARCH_API_KEY   - this is your API key (used by Google for rate limiting, etc.)
GOOGLE_SEARCH_ENGINE_ID - this is the id of your custom search engine
"""
import requests
import json
import os
import re
import logging

from . import constants

logger = logging.getLogger(__name__)

# Get API credentials from environment variables
API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY", None)
SEARCH_ENGINE_ID = os.environ.get("GOOGLE_SEARCH_ENGINE_ID", None)

class GoogleSearchNotConfigured(Exception):
    """Raised when google search keys have not been configured"""
    pass


def extract_arxiv_id(url: str) -> str | None:
    """
    Extract arXiv identifier from an arXiv URL.
    
    Supports both modern (post-April 2007) and legacy (pre-April 2007) identifier formats:
    - Modern: YYMM.NNNNN or YYMM.NNNNvV (e.g., 2510.11694, 2504.16736v3)
    - Legacy: archive-name/YYMMNNN (e.g., hep-th/9901001)
    
    Args:
        url: The arXiv URL (e.g., https://arxiv.org/abs/2510.11694)
        
    Returns:
        The arXiv identifier without the 'arxiv:' prefix, or None if not found
        
    Examples:
        >>> extract_arxiv_id("https://arxiv.org/abs/2510.11694")
        '2510.11694'
        >>> extract_arxiv_id("https://arxiv.org/pdf/2510.11694")
        '2510.11694'
        >>> extract_arxiv_id("https://arxiv.org/html/2510.11694v1")
        '2510.11694v1'
        >>> extract_arxiv_id("https://arxiv.org/abs/2504.16736v3")
        '2504.16736v3'
        >>> extract_arxiv_id("https://arxiv.org/abs/hep-th/9901001")
        'hep-th/9901001'
    """
    # Pattern for modern identifiers (YYMM.NNNNN or YYMM.NNNNvV)
    # Matches: 2510.11694, 2504.16736v3, 0704.0001, 1501.00001v2
    modern_pattern = r'(\d{4}\.\d{4,5}(?:v\d+)?)'
    
    # Pattern for legacy identifiers (archive-name/YYMMNNN)
    # Matches: hep-th/9901001, astro-ph/0703123, math.GT/0601001
    legacy_pattern = r'([a-z\-]+(?:\.[A-Z]{2})?/\d{7})'
    
    # Try modern pattern first
    modern_match = re.search(modern_pattern, url)
    if modern_match:
        return modern_match.group(1)
    
    # Try legacy pattern
    legacy_match = re.search(legacy_pattern, url)
    if legacy_match:
        return legacy_match.group(1)
    
    return None


def google_search_arxiv(query: str, k: int = constants.GOOGLE_SEARCH_RESULT_COUNT, verbose: bool = False) -> list[str]:
    """
    Search for arXiv papers using Google Custom Search API.

    Args:
        query: The search query string
        k: Number of search results to return (max 10 for one call)
        verbose: If True, print out title, link, and snippet for each result

    Returns:
        A list of arXiv paper identifiers (without 'arxiv:' prefix)

    Raises:
        GoogleSearchNotConfigured: If API_KEY or SEARCH_ENGINE_ID are not set
    """
    logger.info(f"Google search for: '{query[:100]}...' (k={k})")
    assert k <= 10, \
        f"google_search_archive was called with k={k}, but this API is currently limited to one batch (10 results)"
    # Check if credentials are configured
    if not API_KEY or not SEARCH_ENGINE_ID:
        logger.error("Google Search API credentials not configured")
        raise GoogleSearchNotConfigured(
            "❌ Google Search API credentials not configured. "
            "Please set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables."
        )
    
    # Base URL for the Custom Search API
    SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
    
    # Parameters for the API request
    params = {
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'q': query,
        'num': min(k, 10)  # Number of search results to return (max 10 for one call)
    }
    
    # Make the GET request to the API
    logger.debug(f"Making Google Search API request: {SEARCH_URL}")
    response = requests.get(SEARCH_URL, params=params)

    paper_ids = []

    # Check for a successful response (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        search_data = response.json()

        # Check if 'items' (search results) are present
        if 'items' in search_data:
            logger.info(f"Google search found {len(search_data['items'])} results")
            if verbose:
                print(f"--- Search Results for: '{query}' ---")

            for i, item in enumerate(search_data['items'], 1):
                title = item.get('title')
                link = item.get('link')
                snippet = item.get('snippet')

                # Extract arXiv ID from URL
                if link:
                    arxiv_id = extract_arxiv_id(link)
                    if arxiv_id:
                        paper_ids.append(arxiv_id)
                        logger.debug(f"Extracted arXiv ID: {arxiv_id} from {link}")

                # Print details if verbose mode is enabled
                if verbose:
                    print(f"\n{i}. {title}")
                    print(f"   URL: {link}")
                    print(f"   Snippet: {snippet}")
        else:
            logger.warning(f"No search results found for query: '{query[:100]}...'")
            if verbose:
                print("No search results found.")
    else:
        # Print an error message if the request failed
        error_msg = f"❌ API request failed with status code {response.status_code}"
        logger.error(f"Google Search API request failed: status={response.status_code}")
        if verbose:
            print(error_msg)
            try:
                error_details = response.json()
                error_message = error_details.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Google Search API error details: {error_message}")
                print(f"Details: {error_message}")
            except json.JSONDecodeError:
                logger.error("Could not decode error response from Google Search API")
                print("Could not decode error response.")
        else:
            raise Exception(f"❌ {error_msg}")
    
    return paper_ids

