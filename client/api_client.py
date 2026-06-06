import os
import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ApiClient:
    def __init__(self):
        self.base_url = os.getenv("BACKEND_BASE_URL", "http://backend:8080")
        self.api_key = os.getenv("SCRAPER_API_KEY", "change-me")
        self.headers = {
            "X-Scraper-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def post_events(self, events: List[Dict[str, Any]]):
        url = f"{self.base_url}/api/v1/internal/scraper/events"
        return self._post(url, events)

    def post_fights(self, fights: List[Dict[str, Any]]):
        url = f"{self.base_url}/api/v1/internal/scraper/fights"
        return self._post(url, fights)

    def post_results(self, results: List[Dict[str, Any]]):
        url = f"{self.base_url}/api/v1/internal/scraper/results"
        return self._post(url, results)

    def post_logs(self, log_data: Dict[str, Any]):
        url = f"{self.base_url}/api/v1/internal/scraper/logs"
        return self._post(url, log_data)

    def post_roster(self, roster_data: Dict[str, Any]):
        url = f"{self.base_url}/api/v1/internal/scraper/roster"
        return self._post(url, roster_data)

    def _post(self, url: str, data: Any):
        try:
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Successfully posted data to {url}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post data to {url}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
