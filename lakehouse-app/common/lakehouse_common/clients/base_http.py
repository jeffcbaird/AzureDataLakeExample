"""Base HTTP client.

Provides retry-with-backoff (tenacity), a pluggable pagination hook,
and two auth strategies: Bearer token (OAuth) and API key header.

Typical usage::

    class MySalesClient(BaseHttpClient):
        BASE_URL = "https://api.example.com/v2"

        def __init__(self):
            super().__init__(auth=ApiKeyAuth("X-Api-Key", os.environ["SALES_API_KEY"]))

        def list_orders(self, page_size: int = 200) -> list[dict]:
            return list(self.paginate("/orders", params={"limit": page_size}))
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Generator, Optional
from urllib.parse import urljoin

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth strategies
# ---------------------------------------------------------------------------

class AuthStrategy(ABC):
    """Attach credentials to an outgoing request."""

    @abstractmethod
    def apply(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        ...


class BearerTokenAuth(AuthStrategy):
    """OAuth 2.0 Bearer token. Token string is resolved lazily via a callable
    so it can be refreshed between retries."""

    def __init__(self, token_provider: Callable[[], str]) -> None:
        self._token_provider = token_provider

    def apply(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        request.headers["Authorization"] = f"Bearer {self._token_provider()}"
        return request


class ApiKeyAuth(AuthStrategy):
    """Static API key sent as a request header (e.g. X-Api-Key)."""

    def __init__(self, header_name: str, api_key: str) -> None:
        self._header_name = header_name
        self._api_key = api_key

    def apply(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        request.headers[self._header_name] = self._api_key
        return request


class NoAuth(AuthStrategy):
    """No authentication."""

    def apply(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        return request


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

_RETRYABLE = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)

_retry = retry(
    retry=retry_if_exception_type(_RETRYABLE),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Base client
# ---------------------------------------------------------------------------

class BaseHttpClient:
    """Subclass and set BASE_URL to get retry, auth, and pagination for free."""

    BASE_URL: str = ""

    def __init__(
        self,
        auth: AuthStrategy | None = None,
        timeout: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self._auth = auth or NoAuth()
        self._timeout = timeout
        self._session = session or requests.Session()

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """GET with retry. Raises on non-2xx."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        """POST with retry. Raises on non-2xx."""
        return self._request("POST", path, **kwargs)

    @_retry
    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = urljoin(self.BASE_URL, path) if self.BASE_URL else path
        # timeout is a send() kwarg, not a Request() kwarg
        timeout = kwargs.pop("timeout", self._timeout)
        req = requests.Request(method, url, **kwargs)
        prepared = self._session.prepare_request(req)
        prepared = self._auth.apply(prepared)
        logger.debug("%s %s", method, url)
        resp = self._session.send(prepared, timeout=timeout)
        resp.raise_for_status()
        return resp

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        next_page_fn: Callable[[requests.Response], str | None] | None = None,
        results_key: str | None = None,
    ) -> Generator[Any, None, None]:
        """Yield individual records across paginated responses.

        Parameters
        ----------
        path:
            API path for the first page.
        params:
            Query-string parameters for the first request.
        next_page_fn:
            Callable ``(response) -> next_url | None``. When None, looks for
            ``"next"`` or ``"next_url"`` keys in the JSON envelope.
        results_key:
            JSON key whose value is the list of records per page. When None
            the entire response body is expected to be a list.
        """
        params = dict(params or {})
        url: str | None = path

        while url is not None:
            resp = self.get(url, params=params)
            body = resp.json()

            records = body[results_key] if results_key else body
            if not isinstance(records, list):
                records = [records]
            yield from records

            # Advance to next page
            params = {}
            if next_page_fn is not None:
                url = next_page_fn(resp)
            elif isinstance(body, dict):
                url = body.get("next") or body.get("next_url")
            else:
                url = None
