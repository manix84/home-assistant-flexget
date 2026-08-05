"""Tests for token-safe diagnostics."""

from datetime import UTC, datetime
from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flexget.const import CONF_TOKEN, DOMAIN
from custom_components.flexget.diagnostics import async_get_config_entry_diagnostics
from custom_components.flexget.models import FlexGetData


async def test_diagnostics_redact_token(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOKEN: "data-secret"},
        options={CONF_TOKEN: "option-secret"},
    )
    entry.runtime_data = SimpleNamespace(
        last_update_success=True,
        data=FlexGetData("3.15.31", None, "1.8", 2, 0, None, datetime.now(UTC)),
    )
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["entry"]["data"][CONF_TOKEN] == "**REDACTED**"
    assert result["entry"]["options"][CONF_TOKEN] == "**REDACTED**"
    assert "data-secret" not in str(result)
    assert "option-secret" not in str(result)
