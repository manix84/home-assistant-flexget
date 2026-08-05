"""Tests for user-facing translation resources."""

import json
from pathlib import Path

import pytest

RESOURCE_PATHS = (
    Path("custom_components/flexget/strings.json"),
    Path("custom_components/flexget/translations/en.json"),
)


@pytest.mark.parametrize("path", RESOURCE_PATHS)
def test_config_step_titles_do_not_require_placeholders(path: Path) -> None:
    """Ensure Home Assistant can preformat every config-step title."""
    resource = json.loads(path.read_text(encoding="utf-8"))
    for step in resource["config"]["step"].values():
        assert "{" not in step["title"]
        assert "}" not in step["title"]


@pytest.mark.parametrize("path", RESOURCE_PATHS)
def test_api_token_fields_explain_how_to_find_token(path: Path) -> None:
    """Keep token retrieval help alongside every token input."""
    resource = json.loads(path.read_text(encoding="utf-8"))
    steps = (*resource["config"]["step"].values(), *resource["options"]["step"].values())

    token_steps = [step for step in steps if "token" in step.get("data", {})]
    assert token_steps
    for step in token_steps:
        description = step["data_description"]["token"]
        assert "flexget web showtoken" in description
        assert "flexget -c /path/to/config.yml web showtoken" in description
