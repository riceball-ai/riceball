from fastapi import APIRouter, HTTPException, Depends
from src.users.models import User
from src.auth import current_active_user
from src.rag.scraper import WebScraper
from .schemas import ScrapeRequest, ScrapeResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

scraper = WebScraper()

@router.post("/scrape", response_model=ScrapeResponse, summary="Scrape webpage content")
async def scrape_webpage(
    request: ScrapeRequest,
    user: User = Depends(current_active_user)
):
    """
    Scrape content from a URL.
    Returns the cleaned text and metadata.
    """
    try:
        # Check if URL is valid (basic check)
        if not request.url.startswith("http"):
             raise HTTPException(status_code=400, detail="Invalid URL protocol")
             
        result = await scraper.scrape(request.url)
        if not result:
            raise HTTPException(status_code=400, detail="Failed to scrape content or empty result")
        
        return ScrapeResponse(
            url=result.url,
            title=result.title,
            content=result.content,
            metadata=result.metadata
        )
    except Exception as e:
        logger.error(f"Scrape API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
