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
class TaskExecution:
    """Normalized task execution information."""

    task: str
    started_at: str | None
    finished_at: str | None
    succeeded: bool | None
    produced: int | None
    accepted: int | None
    rejected: int | None
    failed: int | None
    abort_reason: str | None


@dataclass(frozen=True, slots=True)
class FailedEntrySummary:
    """Normalized retry-failure summary."""

    count: int | None
    latest_at: str | None
    latest_title: str | None
    latest_reason: str | None
    latest_attempt_count: int | None
    next_retry_at: str | None


@dataclass(frozen=True, slots=True)
class PendingApprovalSummary:
    """Normalized pending-approval summary."""

    count: int | None
    oldest_at: str | None


@dataclass(frozen=True, slots=True)
class FlexGetData:
    """One normalized coordinator snapshot."""

    version: str
    latest_version: str | None
    api_version: str | None
    task_count: int
    configured_tasks: tuple[str, ...]
    queued_count: int
    queued_tasks: tuple[str, ...]
    active_task: ActiveTask | None
    schedule_count: int
    scheduled_tasks: tuple[str, ...]
    accepted_count: int | None
    last_accepted_task: str | None
    last_accepted_at: str | None
    last_execution: TaskExecution | None
    latest_failed_execution: TaskExecution | None
    failed_entries: FailedEntrySummary
    next_scheduled_run: str | None
    scheduler_enabled: bool | None
    pending_approvals: PendingApprovalSummary
    response_time_ms: int
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


def parse_task_names(data: Any) -> tuple[str, ...]:
    """Return sorted task names from supported task-list shapes."""
    if isinstance(data, list):
        names = [item if isinstance(item, str) else item.get("name") for item in data]
    elif isinstance(data, dict):
        tasks = data.get("tasks", data.get("items", data.get("entries", data)))
        if isinstance(tasks, dict):
            names = list(tasks)
        elif isinstance(tasks, list):
            names = [item if isinstance(item, str) else item.get("name") for item in tasks]
        else:
            names = []
    else:
        names = []
    return tuple(sorted(str(name) for name in names if name))


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


def parse_queued_task_names(data: Any) -> tuple[str, ...]:
    """Return task names waiting in the execution queue."""
    if isinstance(data, list):
        entries = [item for item in data if not _is_active(item)]
    elif isinstance(data, dict):
        entries = _first_list(data, "queue", "queued", "items", "tasks")
        entries = [item for item in entries if not _is_active(item)]
    else:
        entries = []
    names = []
    for item in entries:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            name = item.get("name") or item.get("task") or item.get("task_name")
            if name:
                names.append(str(name))
    return tuple(names)


def parse_schedules(data: Any) -> tuple[int, tuple[str, ...]]:
    """Return schedule count and unique task patterns."""
    schedules = data if isinstance(data, list) else []
    task_names: set[str] = set()
    for schedule in schedules:
        if not isinstance(schedule, dict):
            continue
        tasks = schedule.get("tasks", [])
        if isinstance(tasks, list):
            task_names.update(str(task) for task in tasks)
        elif isinstance(tasks, str):
            task_names.add(tasks)
    return len(schedules), tuple(sorted(task_names))


def parse_history_summary(
    data: Any, total_count: int | None
) -> tuple[int | None, str | None, str | None]:
    """Return total accepted entries and newest task/time metadata."""
    entries = data if isinstance(data, list) else []
    latest = entries[0] if entries and isinstance(entries[0], dict) else {}
    count = total_count if total_count is not None else len(entries)
    return count, _optional_str(latest.get("task")), _optional_str(latest.get("time"))


def parse_task_status(data: Any) -> tuple[TaskExecution | None, TaskExecution | None]:
    """Return the newest execution and newest latest-per-task failure."""
    statuses = data if isinstance(data, list) else []
    executions: list[TaskExecution] = []
    for status in statuses:
        if not isinstance(status, dict):
            continue
        execution = status.get("last_execution")
        if not isinstance(execution, dict) or not execution:
            continue
        task = status.get("name")
        if not task:
            continue
        executions.append(
            TaskExecution(
                task=str(task),
                started_at=_optional_str(execution.get("start")),
                finished_at=_optional_str(execution.get("end")),
                succeeded=_optional_bool(execution.get("succeeded")),
                produced=_optional_int(execution.get("produced")),
                accepted=_optional_int(execution.get("accepted")),
                rejected=_optional_int(execution.get("rejected")),
                failed=_optional_int(execution.get("failed")),
                abort_reason=_optional_str(execution.get("abort_reason")),
            )
        )
    newest = max(executions, key=_execution_sort_key, default=None)
    newest_failure = max(
        (execution for execution in executions if execution.succeeded is False),
        key=_execution_sort_key,
        default=None,
    )
    return newest, newest_failure


def parse_failed_summary(data: Any, total_count: int | None) -> FailedEntrySummary:
    """Return remembered failure count and newest retry metadata."""
    entries = data if isinstance(data, list) else []
    latest = entries[0] if entries and isinstance(entries[0], dict) else {}
    return FailedEntrySummary(
        count=total_count
        if total_count is not None
        else (len(entries) if data is not None else None),
        latest_at=_optional_str(latest.get("added_at")),
        latest_title=_optional_str(latest.get("title")),
        latest_reason=_optional_str(latest.get("reason")),
        latest_attempt_count=_optional_int(latest.get("count")),
        next_retry_at=_optional_str(latest.get("retry_time")),
    )


def parse_pending_summary(data: Any, total_count: int | None) -> PendingApprovalSummary:
    """Return unapproved entry count and oldest creation time."""
    entries = data if isinstance(data, list) else []
    oldest = entries[0] if entries and isinstance(entries[0], dict) else {}
    return PendingApprovalSummary(
        count=total_count
        if total_count is not None
        else (len(entries) if data is not None else None),
        oldest_at=_optional_str(oldest.get("added")),
    )


def parse_next_scheduled_run(data: Any) -> str | None:
    """Return the earliest next-run timestamp from schedule details."""
    schedules = data if isinstance(data, list) else []
    values = [
        str(schedule["next_run_time"])
        for schedule in schedules
        if isinstance(schedule, dict) and schedule.get("next_run_time")
    ]
    return min(values, default=None)


def _execution_sort_key(execution: TaskExecution) -> str:
    return execution.finished_at or execution.started_at or ""


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


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None
