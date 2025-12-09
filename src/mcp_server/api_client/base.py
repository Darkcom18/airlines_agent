"""
Base HTTP client with retry and error handling.
"""
import asyncio
from typing import Any, Optional

import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = structlog.get_logger()


class APIError(Exception):
    """Base API error."""
    def __init__(self, message: str, status_code: int = 0, response: Any = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class APITimeoutError(APIError):
    """API timeout error."""
    pass


class APIValidationError(APIError):
    """API validation error."""
    pass


class BaseAPIClient:
    """Base async HTTP client with retry logic."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[dict] = None,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make an HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"
        client = await self._get_client()

        log = logger.bind(
            method=method,
            url=url,
            params=params
        )

        try:
            log.info("Making API request", json_body=json_data, headers=headers)

            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params
            )

            log = log.bind(status_code=response.status_code)

            if response.status_code >= 400:
                error_body = response.text
                try:
                    error_body = response.json()
                except Exception:
                    pass

                log.error("API request failed", error=error_body)

                if response.status_code == 422:
                    raise APIValidationError(
                        f"Validation error: {error_body}",
                        status_code=response.status_code,
                        response=error_body
                    )

                raise APIError(
                    f"API error: {error_body}",
                    status_code=response.status_code,
                    response=error_body
                )

            result = response.json()
            log.info("API request successful")
            return result

        except httpx.TimeoutException as e:
            log.error("API request timeout", error=str(e))
            raise APITimeoutError(f"Request timeout: {e}")
        except httpx.NetworkError as e:
            log.error("API network error", error=str(e))
            raise APIError(f"Network error: {e}")

    async def get(
        self,
        endpoint: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make a GET request."""
        return await self._request("GET", endpoint, headers=headers, params=params)

    async def post(
        self,
        endpoint: str,
        headers: Optional[dict] = None,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make a POST request."""
        return await self._request(
            "POST",
            endpoint,
            headers=headers,
            json_data=json_data,
            params=params
        )
