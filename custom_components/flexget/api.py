"""Asynchronous client for the FlexGet REST API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import async_timeout
from aiohttp import ClientError, ClientResponse, ClientSession


class FlexGetError(Exception):
    """Base FlexGet client error."""


class FlexGetConnectionError(FlexGetError):
    """The FlexGet API could not be reached."""


class FlexGetTimeoutError(FlexGetConnectionError):
    """The FlexGet API request timed out."""


class FlexGetAuthenticationError(FlexGetError):
    """The FlexGet API rejected the token."""


class FlexGetUnsupportedApiError(FlexGetError):
    """The endpoint is not compatible with this integration."""


class FlexGetResponseError(FlexGetError):
    """The FlexGet API returned malformed data."""


@dataclass(frozen=True, slots=True)
class FlexGetEndpoint:
    """Connection coordinates for one FlexGet daemon."""

    host: str
    port: int
    api_path: str = "/api"

    @property
    def base_url(self) -> str:
        """Return the normalized HTTP API URL."""
        host = self.host.strip().rstrip(".").lower()
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        path = normalize_api_path(self.api_path)
        return f"http://{host}:{self.port}{path}"

    @property
    def unique_id(self) -> str:
        """Return a stable identifier for the configured endpoint."""
        return f"{self.host.strip().rstrip('.').lower()}:{self.port}"


def normalize_api_path(path: str) -> str:
    """Normalize an API base path without accepting a full URL."""
    normalized = path.strip() or "/api"
    if "://" in normalized or "?" in normalized or "#" in normalized:
        raise ValueError("API path must be a URL path")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/") or "/api"


class FlexGetClient:
    """Small token-authenticated client for one FlexGet daemon."""

    def __init__(
        self,
        session: ClientSession,
        endpoint: FlexGetEndpoint,
        token: str,
        *,
        timeout: int = 10,
    ) -> None:
        self._session = session
        self.endpoint = endpoint
        self._token = token
        self._timeout = timeout

    async def async_get_version(self) -> dict[str, Any]:
        """Fetch server and API version information."""
        data = await self._get("server/version/")
        if not isinstance(data, dict):
            raise FlexGetResponseError("Version response must be an object")
        if not any(key in data for key in ("flexget_version", "version")):
            raise FlexGetUnsupportedApiError("Version response has no FlexGet version")
        return data

    async def async_get_tasks(self) -> Any:
        """Fetch configured tasks without their full configuration."""
        return await self._get("tasks/", params={"include_config": "false"})

    async def async_get_queue(self) -> Any:
        """Fetch queued and active task state."""
        return await self._get("tasks/queue/")

    async def _get(self, endpoint: str, **kwargs: Any) -> Any:
        url = f"{self.endpoint.base_url}/{quote(endpoint, safe='/')}"
        try:
            async with async_timeout.timeout(self._timeout):
                response = await self._session.get(
                    url,
                    headers={"Authorization": f"Token {self._token}"},
                    **kwargs,
                )
                return await self._decode_response(response)
        except TimeoutError as err:
            raise FlexGetTimeoutError("FlexGet request timed out") from err
        except ClientError as err:
            raise FlexGetConnectionError("Could not connect to FlexGet") from err

    @staticmethod
    async def _decode_response(response: ClientResponse) -> Any:
        if response.status in (401, 403):
            await response.read()
            raise FlexGetAuthenticationError("FlexGet rejected the API token")
        if response.status in (404, 405):
            await response.read()
            raise FlexGetUnsupportedApiError("Required FlexGet API endpoint is unavailable")
        if response.status >= 400:
            await response.read()
            raise FlexGetResponseError(f"FlexGet returned HTTP {response.status}")
        try:
            return await response.json(content_type=None)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as err:
            raise FlexGetResponseError("FlexGet returned invalid JSON") from err
