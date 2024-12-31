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
        self.base_url = "https://id.loc.gov/search/?q={keyword}&q=cs:http://id.loc.gov/authorities/subjects"
        self.last_request_time = 0
        self.min_request_interval = 1  # Minimum time between requests in seconds
        self.client = httpx.Client(timeout=30.0)

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
        
        # Construct search URL with the exact format
        encoded_query = quote(query)
        search_url = self.base_url.format(keyword=encoded_query)
        
        logger.info(f"Searching for term: {query}")
        logger.info(f"Using URL: {search_url}")
        
        try:
            self._wait_for_rate_limit()
            response = self.client.get(search_url)
            response.raise_for_status()
            
            logger.info(f"Response status code: {response.status_code}")
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the results table
            table = soup.find('table', class_='id-std')
            if table:
                # Find all result groups
                entries = table.find_all('tbody', class_='tbody-group')
                logger.info(f"Found {len(entries)} entries in the response")
                
                for entry in entries:
                    # Find the main row in each group
                    row = entry.find('tr')
                    if row:
                        # Get the link from the second cell (td)
                        link_cell = row.find_all('td')[1]
                        link = link_cell.find('a')
                        if link:
                            term = link.text.strip()
                            href = link.get('href', '')
                            
                            # Get the ID from the last cell
                            id_cell = row.find_all('td')[-1]
                            lcsh_id = id_cell.text.strip()
                            
                            if term and lcsh_id:
                                full_url = f"https://id.loc.gov{href}" if href.startswith('/') else href
                                results.append({
                                    "term": term,
                                    "id": lcsh_id,
                                    "url": full_url
                                })
            
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