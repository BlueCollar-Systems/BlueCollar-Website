#!/usr/bin/env python3
"""Generate repository metadata for dynamic website version display."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_PRIMARY_PDF_IMPORTER_ASSET = re.compile(
    r"^(?:SketchUp|FreeCAD|LibreCAD|Blender)-PDF-Importer_v\d+(?:\.\d+){2}\.(?:rbz|zip)$"
    r"|^FreeCAD-PDF-Importer-Setup_v\d+(?:\.\d+){2}\.exe$"
    r"|^LibreCAD-PDF-Importer-Setup_v\d+(?:\.\d+){2}\.exe$"
    r"|^LibreCAD-PDF-Importer-Windows-Portable_v\d+(?:\.\d+){2}\.zip$"
)


def _asset_priority(asset: dict[str, Any]) -> tuple[int, str]:
    name = (asset or {}).get("name") or ""
    if not _PRIMARY_PDF_IMPORTER_ASSET.match(name):
        return (999, name)
    if re.search(r"-Setup_v\d+(?:\.\d+){2}\.exe$", name):
        return (0, name)
    if re.match(r"^LibreCAD-PDF-Importer-Windows-Portable_v\d+(?:\.\d+){2}\.zip$", name):
        return (1, name)
    if re.match(r"^LibreCAD-PDF-Importer_v\d+(?:\.\d+){2}\.zip$", name):
        return (20, name)
    return (5, name)


def _prioritize_release_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    for asset in assets:
        name = (asset or {}).get("name") or ""
        if _PRIMARY_PDF_IMPORTER_ASSET.match(name):
            primary.append(asset)
        else:
            other.append(asset)
    return sorted(primary, key=_asset_priority) or other

REPOS: tuple[str, ...] = (
    "BlueCollar-Systems/PDF-Importer-SketchUp",
    "BlueCollar-Systems/PDF-Importer-FreeCAD",
    "BlueCollar-Systems/PDF-Importer-Blender",
    "BlueCollar-Systems/PDF-Importer-LibreCAD",
)

PDF_IMPORTER_RELEASE_REPOS: frozenset[str] = frozenset(
    {
        "BlueCollar-Systems/PDF-Importer-SketchUp",
        "BlueCollar-Systems/PDF-Importer-FreeCAD",
        "BlueCollar-Systems/PDF-Importer-Blender",
        "BlueCollar-Systems/PDF-Importer-LibreCAD",
    }
)

STEEL_RELEASE_REPOS: frozenset[str] = frozenset(
    {
        "BlueCollar-Systems/PDF-Importer-SketchUp",
        "BlueCollar-Systems/PDF-Importer-FreeCAD",
    }
)


def _json_get(url: str, token: str | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bluecollar-website-metadata-sync/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _release_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "tag": data.get("tag_name"),
        "name": data.get("name"),
        "url": data.get("html_url"),
        "published_at": data.get("published_at"),
        "assets": _prioritize_release_assets(
            [
                {
                    "name": asset.get("name"),
                    "url": asset.get("browser_download_url"),
                    "size": asset.get("size"),
                    "content_type": asset.get("content_type"),
                }
                for asset in data.get("assets", [])
            ]
        ),
    }


def _safe_latest_release(repo: str, token: str | None) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = _json_get(url, token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    return _release_summary(data)


def _safe_latest_tagged_release(
    repo: str, token: str | None, tag_prefix: str
) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{repo}/releases?per_page=100"
    try:
        releases = _json_get(url, token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    if not isinstance(releases, list):
        return None

    for release in releases:
        release = release or {}
        # R21-11: a PAT in the website-ci token chain sees drafts via
        # /releases, so a draft (or prerelease) tag could be stamped live
        # before its assets exist. Only published, final releases count.
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name") or ""
        if tag.startswith(tag_prefix):
            return _release_summary(release)
    return None


def _load_previous_repos(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    repos = payload.get("repos")
    return repos if isinstance(repos, dict) else {}


def build_metadata(token: str | None, previous_repos: dict[str, Any] | None = None) -> dict[str, Any]:
    previous_repos = previous_repos or {}
    repos: dict[str, Any] = {}
    for repo in REPOS:
        previous = previous_repos.get(repo, {}) if isinstance(previous_repos, dict) else {}
        repo_api = f"https://api.github.com/repos/{repo}"
        try:
            repo_data = _json_get(repo_api, token)
            repo_error = None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                repos[repo] = {
                    "error": "not_found_or_private",
                    "default_branch": previous.get("default_branch"),
                    "pushed_at": previous.get("pushed_at"),
                    "repo_url": previous.get("repo_url", f"https://github.com/{repo}"),
                    "latest_release": previous.get("latest_release"),
                    "steel_release": previous.get("steel_release"),
                    "from_previous_snapshot": bool(previous),
                }
                if previous.get("latest_release"):
                    print(f"  using previous release snapshot for {repo} (repo not accessible with current token)")
                continue
            raise

        if repo in PDF_IMPORTER_RELEASE_REPOS:
            latest_release = _safe_latest_tagged_release(repo, token, "v")
        else:
            latest_release = _safe_latest_release(repo, token)
        if latest_release is None and previous.get("latest_release"):
            latest_release = previous["latest_release"]
            print(f"  using previous release snapshot for {repo} (no latest release via API)")

        steel_release = None
        if repo in STEEL_RELEASE_REPOS:
            steel_release = _safe_latest_tagged_release(repo, token, "steel-v")
            if steel_release is None and previous.get("steel_release"):
                steel_release = previous["steel_release"]
                print(f"  using previous steel release snapshot for {repo}")

        repos[repo] = {
            "error": repo_error,
            "default_branch": repo_data.get("default_branch"),
            "pushed_at": repo_data.get("pushed_at"),
            "repo_url": repo_data.get("html_url"),
            "latest_release": latest_release,
            "steel_release": steel_release,
        }

    return {
        "generated_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "source_event": os.getenv("GITHUB_EVENT_NAME", "local"),
        "repos": repos,
    }


def stamp_html_versions(payload: dict[str, Any]) -> None:
    """Write latest release tags into static HTML as fallback content."""
    import re

    repos = payload.get("repos", {})
    for page in sorted(Path(".").glob("*.html")):
        html = page.read_text(encoding="utf-8")
        changed = False
        for repo_key, repo_data in repos.items():
            release_attr = (
                r'(?:data-release-channel="steel"[^>]*data-repo-version="'
                + re.escape(repo_key)
                + r'"|data-repo-version="'
                + re.escape(repo_key)
                + r'"[^>]*data-release-channel="steel")'
            )
            steel_pattern = re.compile(r"(<[^>]*" + release_attr + r"[^>]*>)([^<]*)(</[A-Za-z0-9]+>)")

            release = (repo_data or {}).get("steel_release")
            if release and release.get("tag"):
                tag = release["tag"]

                def steel_repl(match: re.Match[str]) -> str:
                    current = match.group(2).strip().lower()
                    value = f"Latest: {tag}" if current.startswith("latest:") else tag
                    return f"{match.group(1)}{value}{match.group(3)}"

                html, n = steel_pattern.subn(steel_repl, html)
                if n > 0:
                    changed = True
                    print(f"  stamped {page.name}: {repo_key} steel -> {tag}")

            release = (repo_data or {}).get("latest_release")
            if not release or not release.get("tag"):
                continue
            tag = release["tag"]
            # Match: data-repo-version="<repo_key>">anything</span|p|...>
            pattern = re.compile(
                r'(<(?![^>]*data-release-channel="steel")[^>]*data-repo-version="'
                + re.escape(repo_key)
                + r'"[^>]*>)([^<]*)(</[A-Za-z0-9]+>)'
            )

            def repl(match: re.Match[str]) -> str:
                current = match.group(2).strip().lower()
                value = f"Latest: {tag}" if current.startswith("latest:") else tag
                return f"{match.group(1)}{value}{match.group(3)}"

            html, n = pattern.subn(repl, html)
            if n > 0:
                changed = True
                print(f"  stamped {page.name}: {repo_key} -> {tag}")

        if changed:
            page.write_text(html, encoding="utf-8")
            print(f"updated {page.name} with static version badges")


def main() -> int:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    output = Path("repo-metadata.json")
    payload = build_metadata(token, _load_previous_repos(output))
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    stamp_html_versions(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
