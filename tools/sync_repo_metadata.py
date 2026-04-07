#!/usr/bin/env python3
"""Generate repository metadata for dynamic website version display."""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPOS: tuple[str, ...] = (
    "BlueCollar-Systems/Steel-Shapes",
    "BlueCollar-Systems/SU-PDFimporter",
    "BlueCollar-Systems/FC-PDFimporter",
    "BlueCollar-Systems/BL-PDFimporter",
    "BlueCollar-Systems/LC-PDFimporter",
    "BlueCollar-Systems/Structural-Steel-SU-Shapes",
    "BlueCollar-Systems/Structural-Steel-DXF-DWG-Shapes",
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


def _safe_latest_release(repo: str, token: str | None) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = _json_get(url, token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    return {
        "tag": data.get("tag_name"),
        "name": data.get("name"),
        "url": data.get("html_url"),
        "published_at": data.get("published_at"),
        "assets": [
            {
                "name": asset.get("name"),
                "url": asset.get("browser_download_url"),
                "size": asset.get("size"),
                "content_type": asset.get("content_type"),
            }
            for asset in data.get("assets", [])
        ],
    }


def build_metadata(token: str | None) -> dict[str, Any]:
    repos: dict[str, Any] = {}
    for repo in REPOS:
        repo_api = f"https://api.github.com/repos/{repo}"
        try:
            repo_data = _json_get(repo_api, token)
            repo_error = None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                repos[repo] = {
                    "error": "not_found_or_private",
                    "repo_url": f"https://github.com/{repo}",
                    "latest_release": None,
                }
                continue
            raise

        latest_release = _safe_latest_release(repo, token)
        repos[repo] = {
            "error": repo_error,
            "default_branch": repo_data.get("default_branch"),
            "pushed_at": repo_data.get("pushed_at"),
            "repo_url": repo_data.get("html_url"),
            "latest_release": latest_release,
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
    index = Path("index.html")
    if not index.exists():
        return

    html = index.read_text(encoding="utf-8")
    changed = False
    for repo_key, repo_data in repos.items():
        release = (repo_data or {}).get("latest_release")
        if not release or not release.get("tag"):
            continue
        tag = release["tag"]
        # Match: data-repo-version="<repo_key>">anything</span>
        pattern = (
            r'(data-repo-version="'
            + re.escape(repo_key)
            + r'"[^>]*>)[^<]*(</span>)'
        )
        new_html, n = re.subn(pattern, rf"\g<1>{tag}\2", html)
        if n > 0:
            html = new_html
            changed = True
            print(f"  stamped {repo_key} -> {tag}")

    if changed:
        index.write_text(html, encoding="utf-8")
        print("updated index.html with static version badges")


def main() -> int:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    output = Path("repo-metadata.json")
    payload = build_metadata(token)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    stamp_html_versions(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
