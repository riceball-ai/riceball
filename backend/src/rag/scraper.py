import logging
import asyncio
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
import trafilatura

import httpx

logger = logging.getLogger(__name__)

class ScrapedContent(BaseModel):
    url: str
    title: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = {}

class WebScraper:
    """
    A unified interface for web scraping using Trafilatura for robust article extraction.
    """
    
    def __init__(self):
        # Only use executor for CPU-bound parsing
        self._executor = ThreadPoolExecutor(max_workers=5)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def scrape(self, url: str) -> ScrapedContent:
        """
        Asynchronously scrape a URL and return cleaned content.
        Uses httpx for downloading (browser-like) and trafilatura for parsing.
        """
        try:
            # 1. Async Download with Browser Headers
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=self.headers) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    raise ValueError(f"Failed to retrieve content from {url}, status: {response.status_code}")
                html_content = response.text

            # 2. Extract (CPU bound, run in thread pool)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, self._parse_html, url, html_content)

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise e

    def _parse_html(self, url: str, html_content: str) -> ScrapedContent:
        # 3. Extract Metadata
        metadata = trafilatura.extract_metadata(html_content)
        
        # metadata.as_dict() values can be complex types, ensure they are serializable
        meta_dict = {}
        if metadata:
            raw_dict = metadata.as_dict()
            for k, v in raw_dict.items():
                # Check if value is serializable (basic types), skip complex ones like lxml elements
                if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                    meta_dict[k] = v
                else:
                    meta_dict[k] = str(v) # Fallback to string representation

        # 4. Extract Content
        content = trafilatura.extract(
            html_content, 
            include_links=True, 
            include_images=False,
            favor_recall=True,
            url=url # Improve extraction hints
        )
        
        if not content:
            content = ""

        return ScrapedContent(
            url=url,
            title=meta_dict.get('title'),
            content=content,
            metadata=meta_dict
        )

    # Legacy method kept for reference if needed, but not used by main scrape flow anymore
    def _scrape_sync(self, url: str) -> ScrapedContent:
        try:
            # 1. Download
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                raise ValueError(f"Failed to retrieve content from {url}")

            # 2. Extract Metadata
            metadata = trafilatura.extract_metadata(downloaded)
            # metadata.as_dict() values can be complex types, ensure they are serializable
            meta_dict = {}
            if metadata:
                raw_dict = metadata.as_dict()
                for k, v in raw_dict.items():
                    # Check if value is serializable (basic types), skip complex ones like lxml elements
                    if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                        meta_dict[k] = v
                    else:
                        meta_dict[k] = str(v) # Fallback to string representation

            # 3. Extract Content (Text for now, we can enhance to Markdown later if needed)
            # Trafilatura does a great job at removing ads/menus and giving just the article text.
            content = trafilatura.extract(
                downloaded, 
                include_links=True, 
                include_images=False,
                favor_recall=True
            )
            
            if not content:
                # Fallback or empty
                content = ""

            return ScrapedContent(
                url=url,
                title=meta_dict.get('title'),
                content=content,
                metadata=meta_dict
            )

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise e
