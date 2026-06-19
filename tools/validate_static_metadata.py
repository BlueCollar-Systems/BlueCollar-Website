#!/usr/bin/env python3
"""Validate static repository version fallbacks against repo-metadata.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

VERSION_ELEMENT_PATTERN = re.compile(
    r"<[A-Za-z0-9]+(?P<attrs>[^>]*)>(?P<label>[^<]*)</[A-Za-z0-9]+>"
)
ATTR_PATTERN = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
_TAG_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def _parse_semver(text: str) -> tuple[int, int, int] | None:
    match = _TAG_RE.search(text.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _label_covers_release(label: str, tag: str) -> bool:
    """True when the static fallback is at least the published release tag."""
    if tag in label:
        return True
    label_ver = _parse_semver(label)
    tag_ver = _parse_semver(tag)
    if label_ver is None or tag_ver is None:
        return False
    return label_ver >= tag_ver


def main() -> int:
    metadata_path = Path("repo-metadata.json")
    if not metadata_path.exists():
        raise SystemExit("repo-metadata.json not found")

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    repos = payload.get("repos")
    if not isinstance(repos, dict):
        raise SystemExit("repo-metadata.json is missing a repos object")

    checked = 0
    failures: list[str] = []
    for page in sorted(Path(".").glob("*.html")):
        text = page.read_text(encoding="utf-8")
        for match in VERSION_ELEMENT_PATTERN.finditer(text):
            attrs = dict(ATTR_PATTERN.findall(match.group("attrs")))
            repo_key = attrs.get("data-repo-version")
            if not repo_key:
                continue
            label = match.group("label")
            repo = repos.get(repo_key)
            release_key = (
                "steel_release"
                if attrs.get("data-release-channel") == "steel"
                else "latest_release"
            )
            release = (repo or {}).get(release_key) if isinstance(repo, dict) else None
            tag = release.get("tag") if isinstance(release, dict) else None
            if not tag:
                continue
            checked += 1
            if not _label_covers_release(label, tag):
                failures.append(
                    f"{page}: {repo_key} static label {label!r} is behind release {tag!r}"
                )

    if failures:
        raise SystemExit(
            "Static repo version labels are stale:\n" + "\n".join(failures)
        )

    if checked == 0:
        raise SystemExit("No static repo version labels with release metadata found")

    print(f"Static metadata fallback check passed ({checked} labels).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
