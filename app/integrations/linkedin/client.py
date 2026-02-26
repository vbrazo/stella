import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LinkedInScraperClient:
    """Client for Relevance AI LinkedIn scraper (same as api-v2's ScrapperService)."""

    def __init__(self):
        self.api_url = settings.relevance_ai_api_url
        self.auth_token = settings.relevance_ai_authorization_token

    @property
    def configured(self) -> bool:
        return bool(self.api_url and self.auth_token)

    async def scrape(self, linkedin_url: str) -> dict | None:
        """Scrape a LinkedIn profile and return structured data."""
        if not self.configured:
            logger.warning("LinkedIn scraper not configured")
            return None

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.api_url,
                json={"url": linkedin_url},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self.auth_token,
                },
            )

            if response.status_code >= 400:
                logger.error("LinkedIn scrape failed: %d %s", response.status_code, response.text)
                return None

            return response.json()

    def extract_profile_data(self, scraped: dict) -> dict:
        """Extract key fields from scraped LinkedIn data."""
        data = scraped.get("data", scraped)
        return {
            "name": data.get("full_name"),
            "role": data.get("job_title") or data.get("title"),
            "company": data.get("company"),
            "location": data.get("location"),
            "avatar_url": data.get("profile_image_url"),
            "headline": data.get("headline"),
            "summary": data.get("summary"),
        }
