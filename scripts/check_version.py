#!/usr/bin/env python3
"""Verify that every published integration version agrees."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _read_versions() -> dict[str, str]:
    """Read each file that publishes the integration version."""
    with (ROOT / "custom_components/flexget/manifest.json").open(encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    with (ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)
    with (ROOT / "release-please-config.json").open(encoding="utf-8") as release_file:
        release_config = json.load(release_file)
    release_manifest = json.loads(
        (ROOT / ".release-please-manifest.json").read_text(encoding="utf-8")
    )
    release_version = release_manifest.get(".", release_config["packages"]["."]["initial-version"])
    return {
        "version.txt": (ROOT / "version.txt").read_text(encoding="utf-8").strip(),
        "manifest.json": manifest["version"],
        "pyproject.toml": pyproject["project"]["version"],
        "release-please": release_version,
    }


def main() -> int:
    """Return a failing status when versions or release notes disagree."""
    versions = _read_versions()
    expected = versions["version.txt"]
    errors = [
        f"{source} has {version!r}; expected {expected!r}"
        for source, version in versions.items()
        if version != expected
    ]
    if not SEMVER.fullmatch(expected):
        errors.append(f"version.txt must contain stable SemVer, got {expected!r}")

    release_headings = [
        line
        for line in (ROOT / "WHATSNEW.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    ]
    if not any(expected in heading for heading in release_headings):
        errors.append(f"WHATSNEW.md has no release heading for {expected}")

    if errors:
        print("Version consistency check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Version {expected} is consistent across release files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
