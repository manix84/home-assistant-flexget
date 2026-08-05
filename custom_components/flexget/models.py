"""Data normalization for FlexGet API responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ActiveTask:
    """Normalized active task information."""

    name: str
    phase: str | None = None
    plugin: str | None = None
    state_since: datetime | None = None

    @property
    def signature(self) -> tuple[str, str | None, str | None]:
        return (self.name, self.phase, self.plugin)


@dataclass(frozen=True, slots=True)
class FlexGetData:
    """One normalized coordinator snapshot."""

    version: str
    latest_version: str | None
    api_version: str | None
    task_count: int
    queued_count: int
    active_task: ActiveTask | None
    last_success: datetime


def parse_version(data: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """Parse known FlexGet version response shapes."""
    version = data.get("flexget_version", data.get("version"))
    latest = data.get("latest_version")
    api_version = data.get("api_version")
    return str(version), _optional_str(latest), _optional_str(api_version)


def count_tasks(data: Any) -> int:
    """Count task records across common paginated response shapes."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("tasks", "items", "entries"):
            value = data.get(key)
            if isinstance(value, (list, dict)):
                return len(value)
        for key in ("total", "count"):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return 0


def parse_queue(data: Any) -> tuple[int, ActiveTask | None]:
    """Normalize queued count and current active task."""
    if isinstance(data, list):
        entries = data
        active = next((item for item in entries if _is_active(item)), None)
        queued = sum(1 for item in entries if not _is_active(item))
    elif isinstance(data, dict):
        entries = _first_list(data, "queue", "queued", "items", "tasks")
        queued_value = data.get("queued_count")
        queued = (
            queued_value
            if isinstance(queued_value, int) and not isinstance(queued_value, bool)
            else len(entries)
        )
        active = data.get("active") or data.get("current")
        if not isinstance(active, dict):
            active = next((item for item in entries if _is_active(item)), None)
            if active is not None and queued_value is None:
                queued = max(0, queued - 1)
    else:
        return 0, None

    return max(0, queued), _parse_active(active)


def _parse_active(value: Any) -> ActiveTask | None:
    if not isinstance(value, dict):
        return None
    name = value.get("name") or value.get("task") or value.get("task_name")
    if not name:
        return None
    return ActiveTask(
        name=str(name),
        phase=_optional_str(value.get("phase")),
        plugin=_optional_str(value.get("plugin")),
    )


def _is_active(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    status = str(value.get("status", value.get("state", ""))).lower()
    return status in {"active", "running", "executing"} or bool(value.get("active"))


def _first_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
