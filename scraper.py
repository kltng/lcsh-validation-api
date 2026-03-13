"""
Library of Congress Subject Headings (LCSH) Scraper

This module provides functionality to search and retrieve LCSH terms from the Library of Congress
website (id.loc.gov). It uses web scraping to fetch authorized subject headings and returns
structured data including terms, IDs, and URLs.

Example:
    scraper = LCSHScraper()
    results = scraper.search_terms("China--History--Republic, 1912-1949")
    for result in results:
        print(f"Term: {result['term']}")
        print(f"ID: {result['id']}")
        print(f"URL: {result['url']}")
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
from urllib.parse import quote
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LCSHScraper:
    """
    A scraper for the Library of Congress Subject Headings (LCSH) search interface.
    
    This class provides methods to search and retrieve LCSH terms, including their
    identifiers and URLs. It implements rate limiting to be respectful to the LOC servers
    and handles parsing of the HTML search results.

    Attributes:
        base_url (str): The template URL for LOC subject heading searches
        last_request_time (float): Timestamp of the last request made
        min_request_interval (int): Minimum time in seconds between requests
        client (httpx.Client): HTTP client for making requests
    """

    def __init__(self):
        """
        Initialize the LCSH scraper with default settings.
        
        Sets up the base URL for searches and initializes the HTTP client with
        appropriate timeout settings. Also initializes rate limiting parameters.
        """
        self.base_url = "https://id.loc.gov/authorities/subjects/suggest2"
        self.last_request_time = 0
        self.min_request_interval = 3  # Respect LOC robots.txt crawl-delay
        self.max_retries = 2
        headers = {"User-Agent": "LCSH-Validation-API/1.0 (https://github.com/kltng/lcsh-validation-api)"}
        self.client = httpx.Client(timeout=30.0, headers=headers)

    def _wait_for_rate_limit(self):
        """
        Implement rate limiting for requests to the LOC server.
        
        Ensures that subsequent requests are spaced by at least min_request_interval
        seconds. If a request would occur too soon after the previous one, the method
        sleeps for the remaining time.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    def _request_with_retry(self, params):
        """Make a request with retry on 429/503."""
        for attempt in range(self.max_retries + 1):
            response = self.client.get(self.base_url, params=params)
            if response.status_code in (429, 503) and attempt < self.max_retries:
                delay = 2 ** (attempt + 1)
                logger.warning(f"LOC API returned {response.status_code}, retrying in {delay}s...")
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        return response

    def search_terms(self, query: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """
        Search for LCSH terms matching the provided query.

        Makes a request to the LOC website, parses the HTML response, and extracts
        relevant information about matching subject headings.

        Args:
            query (str): The search query (e.g., "China--History--Republic, 1912-1949")
            max_pages (int, optional): Maximum number of pages to retrieve. Defaults to 3.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, each containing:
                - term: The subject heading text
                - id: The LOC identifier (e.g., "sh85024107")
                - url: The full URL to the term's page

        Example returned dictionary:
            {
                "term": "China--History--Republic, 1912-1949",
                "id": "sh85024107",
                "url": "https://id.loc.gov/authorities/subjects/sh85024107"
            }
        """
        results = []
        
        params = {
            "q": query,
            "searchtype": "keyword"
        }
        
        logger.info(f"Searching for term: {query}")
        logger.info(f"Using URL: {self.base_url} with params: {params}")
        
        try:
            self._wait_for_rate_limit()
            response = self._request_with_retry(params)
            
            logger.info(f"Response status code: {response.status_code}")
            
            # Parse the JSON response
            data = response.json()
            
            if data and "hits" in data and isinstance(data["hits"], list):
                hits = data["hits"]
                logger.info(f"Found {len(hits)} hits in the response")

                for hit in hits:
                    term = hit.get("suggestLabel") or hit.get("aLabel") # Use suggestLabel, fallback to aLabel
                    uri = hit.get("uri")

                    if term and uri:
                        # Extract ID from URI
                        lcsh_id = uri.split('/')[-1]
                        results.append({
                            "term": term,
                            "id": lcsh_id,
                            "url": uri
                        })
                    else:
                        logger.warning(f"Skipping hit due to missing term or URI: {hit}")
            else:
                logger.warning(f"No 'hits' found in the response or 'hits' is not a list. Response data: {data}")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503):
                logger.warning(f"LOC API returned {e.response.status_code}, retries exhausted")
            else:
                logger.error(f"Error fetching results: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Error fetching results: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
        
        logger.info(f"Returning {len(results)} results")
        return results

    def __del__(self):
        """
        Cleanup method to ensure the HTTP client is properly closed.
        
        This method is automatically called when the scraper instance is destroyed,
        ensuring that network resources are properly released.
        """
        self.client.close()