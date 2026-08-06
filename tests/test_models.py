"""Tests for API response normalization."""

from datetime import datetime

from custom_components.flexget.models import (
    count_tasks,
    parse_failed_summary,
    parse_history_summary,
    parse_next_scheduled_run,
    parse_operational_stats,
    parse_pending_summary,
    parse_queue,
    parse_queued_task_names,
    parse_schedules,
    parse_task_controls,
    parse_task_names,
    parse_task_status,
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


def test_parse_task_controls_uses_manual_setting() -> None:
    controls = parse_task_controls(
        [
            {"name": "automatic", "config": {"rss": "https://example.test/feed"}},
            {"name": "manual", "config": {"manual": True}},
        ]
    )
    assert [(control.name, control.automatic_execution) for control in controls] == [
        ("automatic", True),
        ("manual", False),
    ]


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


def test_parse_monitoring_summaries() -> None:
    status = [
        {
            "name": "sort",
            "last_execution": {
                "start": "2026-08-05T10:00:00+00:00",
                "end": "2026-08-05T10:00:05+00:00",
                "succeeded": False,
                "produced": 3,
                "accepted": 1,
                "rejected": 1,
                "failed": 1,
                "abort_reason": "test failure",
            },
        }
    ]
    latest, failed = parse_task_status(status)
    assert latest == failed
    assert latest is not None
    assert latest.task == "sort"
    assert latest.accepted == 1

    retry = parse_failed_summary(
        [{"title": "Example", "count": 2, "retry_time": "2026-08-05T11:00:00+00:00"}],
        4,
        datetime.fromisoformat("2026-08-05T12:00:00+00:00"),
    )
    assert retry.count == 4
    assert retry.latest_attempt_count == 2
    assert retry.overdue_count == 1
    assert retry.highest_attempt_count == 2
    assert parse_failed_summary(None, None).count is None

    pending = parse_pending_summary([{"added": "2026-08-05T09:00:00+00:00"}], 2)
    assert pending.count == 2
    assert pending.oldest_at == "2026-08-05T09:00:00+00:00"
    assert (
        parse_next_scheduled_run(
            [
                {"next_run_time": "2026-08-05T12:00:00+00:00"},
                {"next_run_time": "2026-08-05T11:00:00+00:00"},
            ]
        )
        == "2026-08-05T11:00:00+00:00"
    )

    stats = parse_operational_stats(
        [{"id": 1, "last_execution": {}}, {"id": 2, "last_execution": {"id": 3}}],
        [
            [
                {"succeeded": True, "accepted": 3, "rejected": 1, "failed": 0},
                {"succeeded": False, "accepted": 0, "rejected": 0, "failed": 2},
            ]
        ],
    )
    assert stats.successful_executions == 1
    assert stats.failed_executions == 1
    assert stats.accepted == 3
    assert stats.failed_entries == 2
    assert stats.never_run_tasks == 1
    assert stats.success_rate == 50.0
