"""
SEC EDGAR HTTP Client.

Handles network requests to SEC EDGAR with rate limiting, automatic backoff on 429,
proper headers, and connection pooling.
"""

import time
from typing import Any, Dict, Optional
import requests

from .config import RATE_LIMIT_DELAY, SEC_USER_AGENT


class SecClient:
    """Resilient HTTP client for querying SEC EDGAR APIs."""

    def __init__(
        self,
        user_agent: str = SEC_USER_AGENT,
        rate_limit_delay: float = RATE_LIMIT_DELAY,
        timeout: int = 30,
    ) -> None:
        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/html, */*",
        })

    def get(self, url: str, is_json: bool = True, max_attempts: int = 3) -> Any:
        """
        Executes an HTTP GET request respecting SEC rate limits and handling retries.
        """
        if self.rate_limit_delay > 0:
            time.sleep(self.rate_limit_delay)

        for attempt in range(max_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout)

                # Handle SEC rate limit backoff (HTTP 429)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 2.0 * (attempt + 1)))
                    print(f"  [Rate Limited] SEC 429 received. Backing off for {retry_after:.1f}s...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()

                if is_json:
                    return response.json()

                # SEC documents often lack charset headers, causing requests to default to ISO-8859-1.
                # Overriding with apparent_encoding or utf-8 prevents character corruption.
                if response.encoding is None or response.encoding == "ISO-8859-1":
                    response.encoding = response.apparent_encoding or "utf-8"
                return response.text

            except requests.exceptions.RequestException as e:
                if attempt >= max_attempts - 1:
                    raise RuntimeError(f"Failed to fetch {url} after {max_attempts} attempts: {e}")
                time.sleep(1.5 * (attempt + 1))

        raise RuntimeError(f"Request failed for {url} after {max_attempts} attempts.")

    def close(self) -> None:
        """Closes the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "SecClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
