"""Tests for token-safe diagnostics."""

from datetime import UTC, datetime
from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flexget.const import CONF_TOKEN, DOMAIN
from custom_components.flexget.diagnostics import async_get_config_entry_diagnostics
from custom_components.flexget.models import (
    FailedEntrySummary,
    FlexGetData,
    PendingApprovalSummary,
)


async def test_diagnostics_redact_token(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOKEN: "data-secret"},
        options={CONF_TOKEN: "option-secret"},
    )
    entry.runtime_data = SimpleNamespace(
        last_update_success=True,
        data=FlexGetData(
            version="3.15.31",
            latest_version=None,
            api_version="1.8",
            task_count=2,
            configured_tasks=("one", "two"),
            queued_count=0,
            queued_tasks=(),
            active_task=None,
            schedule_count=1,
            scheduled_tasks=("one",),
            accepted_count=10,
            last_accepted_task="one",
            last_accepted_at="2026-08-05T13:05:49.010966",
            last_execution=None,
            latest_failed_execution=None,
            failed_entries=FailedEntrySummary(None, None, None, None, None, None),
            next_scheduled_run=None,
            scheduler_enabled=True,
            pending_approvals=PendingApprovalSummary(None, None),
            response_time_ms=25,
            last_success=datetime.now(UTC),
        ),
        consecutive_failures=0,
    )
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["entry"]["data"][CONF_TOKEN] == "**REDACTED**"
    assert result["entry"]["options"][CONF_TOKEN] == "**REDACTED**"
    assert "data-secret" not in str(result)
    assert "option-secret" not in str(result)
