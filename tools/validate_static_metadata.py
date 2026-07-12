#!/usr/bin/env python3
"""Validate static repository version fallbacks against repo-metadata.json."""

from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

VERSION_ELEMENT_PATTERN = re.compile(
    r"<[A-Za-z0-9]+(?P<attrs>[^>]*)>(?P<label>[^<]*)</[A-Za-z0-9]+>"
)
ATTR_PATTERN = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
_TAG_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")

# --- R21-4: <code> asset filenames must match real release asset names ------
# Install cards name downloadable release assets in <code> tags. Those names
# silently drifted from the published assets for 17 days (index.html named an
# unversioned FreeCAD-PDF-Importer-Setup.exe that never existed). Any <code>
# text that looks like a product release asset (.exe/.zip/.rbz containing
# "PDF-Importer") must match, up to its version token, an asset name present
# in repo-metadata.json. Bundled in-archive tools (lcpdf-gui.exe, pdf2dxf.exe)
# carry no "PDF-Importer" marker and are intentionally out of scope.
_CODE_RE = re.compile(r"<code[^>]*>([^<]+)</code>")
_ASSET_EXTENSIONS = (".exe", ".zip", ".rbz")
# Accepts a real semver (v4.0.65), the docs convention vX.Y.Z, or v<version>.
_VERSION_TOKEN_RE = re.compile(r"v(?:\d+(?:\.\d+){2}|X\.Y\.Z|<version>)")


def _normalize_asset_name(name: str) -> str:
    """Collapse any version token so patterns compare version-independently."""
    return _VERSION_TOKEN_RE.sub("v{VER}", name.strip())


def _asset_name_patterns(repos: dict) -> set[str]:
    patterns: set[str] = set()
    for repo in repos.values():
        if not isinstance(repo, dict):
            continue
        for channel in ("latest_release", "steel_release"):
            release = repo.get(channel)
            if not isinstance(release, dict):
                continue
            for asset in release.get("assets") or []:
                name = (asset or {}).get("name")
                if isinstance(name, str) and name:
                    patterns.add(_normalize_asset_name(name))
    return patterns


def _check_code_asset_names(
    page: Path, text: str, patterns: set[str], failures: list[str]
) -> int:
    checked = 0
    for match in _CODE_RE.finditer(text):
        candidate = html_lib.unescape(match.group(1)).strip()
        if not candidate.lower().endswith(_ASSET_EXTENSIONS):
            continue
        if "PDF-Importer" not in candidate:
            continue
        checked += 1
        if _normalize_asset_name(candidate) not in patterns:
            failures.append(
                f"{page}: <code>{candidate}</code> matches no release asset "
                f"name pattern in repo-metadata.json "
                f"(known: {', '.join(sorted(patterns))})"
            )
    return checked


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
    if "BlueCollar-Systems/Steel-Shapes" in repos:
        raise SystemExit(
            "repo-metadata.json must not publish private Steel-Shapes release assets; "
            "use public importer-hosted steel-v release assets instead"
        )

    checked = 0
    asset_names_checked = 0
    failures: list[str] = []
    asset_patterns = _asset_name_patterns(repos)
    for page in sorted(Path(".").glob("*.html")):
        text = page.read_text(encoding="utf-8")
        asset_names_checked += _check_code_asset_names(
            page, text, asset_patterns, failures
        )
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
            "Static metadata checks failed (stale version label or drifted "
            "asset filename):\n" + "\n".join(failures)
        )

    if checked == 0:
        raise SystemExit("No static repo version labels with release metadata found")

    if asset_names_checked == 0:
        raise SystemExit(
            "No <code> release asset filenames found in any page; the install "
            "cards should name at least one downloadable asset (R21-4)"
        )

    print(
        f"Static metadata fallback check passed "
        f"({checked} labels, {asset_names_checked} asset filenames)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
