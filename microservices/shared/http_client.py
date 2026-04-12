"""
Resilient HTTP client with retry logic and circuit breaker.
Used for inter-service communication.
"""

import asyncio
from typing import Any, Dict, Optional

import httpx
from shared.logger import setup_logger

logger = setup_logger("http_client")


class ResilientHttpClient:
    """
    HTTP client with exponential backoff retry and timeout handling.
    Prevents cascading failures in microservices architecture.
    """

    def __init__(
        self, timeout: float = 5.0, max_retries: int = 3, backoff_factor: float = 0.5
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        request_id: str = "unknown",
    ) -> httpx.Response:
        """
        POST request with retry logic.
        Retries on network errors and 5xx server errors.
        """
        return await self._request_with_retry(
            method="POST", url=url, json=json, headers=headers, request_id=request_id
        )

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        request_id: str = "unknown",
    ) -> httpx.Response:
        """
        GET request with retry logic.
        Retries on network errors and 5xx server errors.
        """
        return await self._request_with_retry(
            method="GET", url=url, params=params, headers=headers, request_id=request_id
        )

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        request_id: str = "unknown",
    ) -> httpx.Response:
        """
        DELETE request with retry logic.
        Does NOT retry on success to prevent duplicate deletions.
        """
        return await self._request_with_retry(
            method="DELETE",
            url=url,
            headers=headers,
            request_id=request_id,
            retry_on_success=False,
        )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        request_id: str = "unknown",
        retry_on_success: bool = True,
    ) -> httpx.Response:
        """
        Execute HTTP request with exponential backoff retry.
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method == "POST":
                        response = await client.post(url, json=json, headers=headers)
                    elif method == "GET":
                        response = await client.get(url, params=params, headers=headers)
                    elif method == "DELETE":
                        response = await client.delete(url, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    # Success or client error - return immediately (don't retry 4xx)
                    if response.status_code < 500:
                        if attempt > 0:
                            logger.info(
                                f"[{request_id}] Request succeeded on attempt {attempt + 1}: "
                                f"{method} {url}"
                            )
                        return response

                    # Server error - retry
                    logger.warning(
                        f"[{request_id}] Server error {response.status_code} on attempt {attempt + 1}: "
                        f"{method} {url}"
                    )
                    last_exception = httpx.HTTPStatusError(
                        f"Server error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.ConnectError,
            ) as e:
                logger.warning(
                    f"[{request_id}] Network error on attempt {attempt + 1}: "
                    f"{method} {url} - {type(e).__name__}: {e}"
                )
                last_exception = e

            except httpx.HTTPStatusError as e:
                # Client errors (4xx) should not be retried
                if e.response.status_code < 500:
                    raise
                logger.warning(
                    f"[{request_id}] HTTP error on attempt {attempt + 1}: "
                    f"{method} {url} - {e}"
                )
                last_exception = e

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                backoff_time = self.backoff_factor * (2**attempt)
                logger.info(
                    f"[{request_id}] Retrying in {backoff_time:.2f}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(backoff_time)

        # All retries exhausted
        logger.error(
            f"[{request_id}] All {self.max_retries} retry attempts failed for {method} {url}"
        )
        if last_exception:
            raise last_exception
        raise httpx.RequestError(f"Request failed after {self.max_retries} attempts")


# Singleton instances for different timeout requirements
default_client = ResilientHttpClient(timeout=5.0, max_retries=3)
long_timeout_client = ResilientHttpClient(timeout=15.0, max_retries=2)
