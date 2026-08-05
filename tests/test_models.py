"""Tests for API response normalization."""

from custom_components.flexget.models import (
    count_tasks,
    parse_history_summary,
    parse_queue,
    parse_queued_task_names,
    parse_schedules,
    parse_task_names,
    parse_version,
)


def test_parse_version() -> None:
    assert parse_version(
        {"flexget_version": "3.15.31", "latest_version": "3.16.0", "api_version": "1.8"}
    ) == ("3.15.31", "3.16.0", "1.8")


def test_count_tasks_handles_supported_shapes() -> None:
    assert count_tasks([{"name": "one"}, {"name": "two"}]) == 2
    assert count_tasks({"tasks": {"one": {}, "two": {}}}) == 2
    assert count_tasks({"total": 5}) == 5
    assert count_tasks("bad response") == 0


def test_parse_task_names_handles_live_list_shape() -> None:
    """Parse the string-list response returned by the Sort daemon."""
    assert parse_task_names(["sort_tv", "extract_all"]) == ("extract_all", "sort_tv")


def test_parse_queue_with_active_task() -> None:
    queued, active = parse_queue(
        {
            "queued": [{"name": "next"}],
            "active": {"task": "download", "phase": "output", "plugin": "move"},
        }
    )
    assert queued == 1
    assert active is not None
    assert active.name == "download"
    assert active.phase == "output"
    assert active.plugin == "move"


def test_parse_queue_list_does_not_count_active_as_queued() -> None:
    queued, active = parse_queue(
        [{"name": "running", "status": "running"}, {"name": "waiting", "status": "queued"}]
    )
    assert queued == 1
    assert active is not None
    assert active.name == "running"


def test_parse_queued_task_names() -> None:
    """Exclude running entries while retaining waiting task names."""
    data = [
        {"name": "running", "status": "running"},
        {"task": "waiting", "status": "pending"},
    ]
    assert parse_queued_task_names(data) == ("waiting",)


def test_parse_schedules_and_history() -> None:
    """Normalize live schedule and history summary shapes."""
    assert parse_schedules([{"tasks": ["sort_*", "extract_all"]}, {"tasks": "nightly"}]) == (
        2,
        ("extract_all", "nightly", "sort_*"),
    )
    assert parse_history_summary(
        [{"task": "sort_anime", "time": "2026-08-05T13:05:49.010966"}], 100
    ) == (100, "sort_anime", "2026-08-05T13:05:49.010966")
