"""Asynchronous client for the FlexGet REST API."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from math import ceil
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

    async def async_get_tasks(self, *, include_config: bool = False) -> Any:
        """Fetch configured tasks without their full configuration."""
        return await self._get(
            "tasks/", params={"include_config": "true" if include_config else "false"}
        )

    async def async_get_task(self, task_name: str) -> dict[str, Any]:
        """Fetch one task's latest user configuration."""
        data, _headers = await self._request_with_headers("GET", f"tasks/{task_name}/")
        if not isinstance(data, dict) or not isinstance(data.get("config"), dict):
            raise FlexGetResponseError("Task response must contain a configuration object")
        if data.get("name") != task_name:
            raise FlexGetResponseError("Task response name does not match the request")
        return data

    async def async_update_task(self, task_name: str, config: dict[str, Any]) -> None:
        """Replace one task configuration using the FlexGet API."""
        await self._request_with_headers(
            "PUT",
            f"tasks/{task_name}/",
            json={"name": task_name, "config": config},
        )

    async def async_execute_task(self, task_name: str) -> None:
        """Queue one explicit task execution without streaming logs."""
        data, _headers = await self._request_with_headers(
            "POST", "tasks/execute/", json={"tasks": [task_name]}
        )
        tasks = data.get("tasks") if isinstance(data, dict) else None
        if not isinstance(tasks, list) or not any(
            isinstance(task, dict) and task.get("name") == task_name for task in tasks
        ):
            raise FlexGetResponseError("FlexGet did not confirm the queued task")

    async def async_get_queue(self) -> Any:
        """Fetch queued and active task state."""
        return await self._get("tasks/queue/")

    async def async_get_schedules(self) -> Any:
        """Fetch configured daemon schedules."""
        return await self._get("schedules/")

    async def async_get_history_summary(self) -> tuple[Any, int | None]:
        """Fetch the newest accepted entry and total history count."""
        data, headers = await self._get_with_headers(
            "history/", params={"per_page": "1", "page": "1", "order": "desc"}
        )
        total = headers.get("Total-Count")
        try:
            return data, int(total) if total is not None else None
        except ValueError:
            return data, None

    async def async_get_task_status(self) -> Any:
        """Fetch the latest execution for each task."""
        params = {
            "per_page": "100",
            "page": "1",
            "sort_by": "last_execution_time",
            "order": "desc",
            "include_execution": "true",
        }
        data, headers = await self._get_with_headers(
            "tasks/status/",
            params=params,
        )
        total = self._header_int(headers, "Total-Count")
        if total is None or total <= 100:
            return data
        remaining = await asyncio.gather(
            *(
                self._get("tasks/status/", params={**params, "page": str(page)})
                for page in range(2, ceil(total / 100) + 1)
            )
        )
        statuses = list(data) if isinstance(data, list) else []
        for page in remaining:
            if isinstance(page, list):
                statuses.extend(page)
        return statuses

    async def async_get_failed_summary(self) -> tuple[Any, int | None]:
        """Fetch the newest retry failure and total count."""
        data, total = await self._get_paginated_summary(
            "failed/", per_page="100", sort_by="failure_time", order="desc"
        )
        if total is None or total <= 100:
            return data, total
        remaining = await asyncio.gather(
            *(
                self._get(
                    "failed/",
                    params={
                        "per_page": "100",
                        "page": str(page),
                        "sort_by": "failure_time",
                        "order": "desc",
                    },
                )
                for page in range(2, ceil(total / 100) + 1)
            )
        )
        entries = list(data) if isinstance(data, list) else []
        for page in remaining:
            if isinstance(page, list):
                entries.extend(page)
        return entries, total

    async def async_get_pending_approval_summary(self) -> tuple[Any, int | None]:
        """Fetch the oldest unapproved entry and total count."""
        return await self._get_paginated_summary(
            "pending/", sort_by="added", order="asc", approved="false"
        )

    async def async_get_schedule_details(self, schedules: Any) -> list[Any]:
        """Fetch runtime details for configured schedules."""
        if not isinstance(schedules, list):
            return []
        requests = [
            self._get(f"schedules/{schedule['id']}/")
            for schedule in schedules
            if isinstance(schedule, dict) and isinstance(schedule.get("id"), int)
        ]
        return list(await asyncio.gather(*requests))

    async def async_get_recent_executions(self, statuses: Any, since: datetime) -> list[Any]:
        """Fetch up to 100 executions per task since the requested time."""
        if not isinstance(statuses, list):
            return []
        requests = [
            self._get(
                f"tasks/status/{status['id']}/executions/",
                params={
                    "per_page": "100",
                    "page": "1",
                    "sort_by": "start",
                    "order": "desc",
                    "start_date": since.isoformat(),
                    "succeeded": "false",
                    "produced": "false",
                },
            )
            for status in statuses
            if isinstance(status, dict) and isinstance(status.get("id"), int)
        ]
        return list(await asyncio.gather(*requests))

    async def _get_paginated_summary(self, endpoint: str, **params: str) -> tuple[Any, int | None]:
        params.setdefault("per_page", "1")
        params["page"] = "1"
        data, headers = await self._get_with_headers(endpoint, params=params)
        return data, self._header_int(headers, "Total-Count")

    @staticmethod
    def _header_int(headers: dict[str, str], name: str) -> int | None:
        value = headers.get(name)
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None

    async def _get(self, endpoint: str, **kwargs: Any) -> Any:
        data, _headers = await self._get_with_headers(endpoint, **kwargs)
        return data

    async def _get_with_headers(self, endpoint: str, **kwargs: Any) -> tuple[Any, dict[str, str]]:
        return await self._request_with_headers("GET", endpoint, **kwargs)

    async def _request_with_headers(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> tuple[Any, dict[str, str]]:
        url = f"{self.endpoint.base_url}/{quote(endpoint, safe='/')}"
        try:
            async with async_timeout.timeout(self._timeout):
                response = await self._session.request(
                    method,
                    url,
                    headers={"Authorization": f"Token {self._token}"},
                    **kwargs,
                )
                data = await self._decode_response(response)
                return data, dict(response.headers)
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
