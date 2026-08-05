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
