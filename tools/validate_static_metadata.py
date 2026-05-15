#!/usr/bin/env python3
"""Validate static repository version fallbacks against repo-metadata.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

VERSION_PATTERN = re.compile(
    r'data-repo-version="([^"]+)"[^>]*>([^<]*)</[A-Za-z0-9]+>'
)


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
        for repo_key, label in VERSION_PATTERN.findall(text):
            repo = repos.get(repo_key)
            release = (repo or {}).get("latest_release") if isinstance(repo, dict) else None
            tag = release.get("tag") if isinstance(release, dict) else None
            if not tag:
                continue
            checked += 1
            if tag not in label:
                failures.append(
                    f"{page}: {repo_key} static label {label!r} does not include {tag!r}"
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
