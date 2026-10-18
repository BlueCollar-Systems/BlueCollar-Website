#!/usr/bin/env python3
"""Generate repository metadata for dynamic website version display."""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
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
    # Keep the install/download artifacts first so nav.js selects the same
    # user-friendly default, but retain verification sidecars (for example an
    # installer attestation) in the downstream release snapshot as well.
    return sorted(primary, key=_asset_priority) + other

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
        # Bind the downstream snapshot to the exact product source revision,
        # not only to a mutable branch name or a human-readable tag.
        "target_commitish": data.get("target_commitish"),
        # A digest identifies the current bytes; GitHub release immutability
        # proves those bytes cannot later be replaced under the same URL.
        "immutable": data.get("immutable"),
        "assets": _prioritize_release_assets(
            [
                {
                    "name": asset.get("name"),
                    "url": asset.get("browser_download_url"),
                    "size": asset.get("size"),
                    "content_type": asset.get("content_type"),
                    # GitHub computes this digest from the stored release
                    # asset. Keep it in the downstream snapshot so a site
                    # update is bound to final bytes, not only a filename.
                    "digest": asset.get("digest"),
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


def releases_url(repo: str) -> str:
    """The API listing the site reads a repo's releases from (newest first)."""
    return f"https://api.github.com/repos/{repo}/releases?per_page=100"


def final_tagged_releases(releases: Any, tag_prefix: str) -> list[dict[str, Any]]:
    """Published, final releases whose tag starts with tag_prefix, in API order.

    The first entry is the release the site publishes for that channel.
    tools/check_release_drift.py uses the same rule, so the drift check and
    the deploy can never disagree about which release is the latest.
    """
    if not isinstance(releases, list):
        return []
    found: list[dict[str, Any]] = []
    for release in releases:
        release = release or {}
        # R21-11: a PAT in the website-ci token chain sees drafts via
        # /releases, so a draft (or prerelease) tag could be stamped live
        # before its assets exist. Only published, final releases count.
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name") or ""
        if tag.startswith(tag_prefix):
            found.append(release)
    return found


def _safe_latest_tagged_release(
    repo: str, token: str | None, tag_prefix: str
) -> dict[str, Any] | None:
    try:
        releases = _json_get(releases_url(repo), token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    candidates = final_tagged_releases(releases, tag_prefix)
    return _release_summary(candidates[0]) if candidates else None


def _load_previous_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _load_previous_repos(path: Path) -> dict[str, Any]:
    payload = _load_previous_payload(path) or {}
    repos = payload.get("repos")
    return repos if isinstance(repos, dict) else {}


# Written fresh on every run; no visitor ever sees them.
_RUN_ONLY_FIELDS: tuple[str, ...] = ("generated_at", "source_event")


class _SteelBadgeParser(HTMLParser):
    """Collects data-repo-version keys of badges on the steel channel."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.repos: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        key = values.get("data-repo-version")
        if key and values.get("data-release-channel") == "steel":
            self.repos.add(key)


def steel_badge_repos(pages_root: Path = Path(".")) -> set[str]:
    """Repos that have a steel-channel version badge on any root *.html page."""
    found: set[str] = set()
    for page in sorted(Path(pages_root).glob("*.html")):
        parser = _SteelBadgeParser()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeDecodeError):
            continue
        found |= parser.repos
    return found


def _pushed_at_is_shown(
    repo_key: str,
    repo_data: dict[str, Any],
    steel_badges: frozenset[str] | set[str] = STEEL_RELEASE_REPOS,
) -> bool:
    """True when nav.js would show this repo's push date on a badge.

    nav.js shows "Updated: <pushed_at>" only where the badge's release
    channel has no tag: the importer channel (latest_release) for every repo,
    plus the steel channel (steel_release) for every repo with a steel badge.
    """
    latest = repo_data.get("latest_release") or {}
    if not (isinstance(latest, dict) and latest.get("tag")):
        return True
    if repo_key in steel_badges:
        steel = repo_data.get("steel_release") or {}
        if not (isinstance(steel, dict) and steel.get("tag")):
            return True
    return False


def visible_metadata(
    payload: dict[str, Any],
    steel_badges: frozenset[str] | set[str] = STEEL_RELEASE_REPOS,
) -> dict[str, Any]:
    """The part of a snapshot that can change what a visitor sees.

    Drops the per-run timestamp fields and any push date that no badge
    shows. Tags, names, links, sizes, digests and immutability all stay, so
    any real change still rewrites the snapshot. steel_badges names the
    repos with a steel-channel badge (main() reads them from the pages).
    """
    view = copy.deepcopy(payload)
    for field in _RUN_ONLY_FIELDS:
        view.pop(field, None)
    repos = view.get("repos")
    if isinstance(repos, dict):
        for repo_key, repo_data in repos.items():
            if isinstance(repo_data, dict) and not _pushed_at_is_shown(repo_key, repo_data, steel_badges):
                repo_data.pop("pushed_at", None)
    return view


def build_metadata(token: str | None, previous_repos: dict[str, Any] | None = None) -> dict[str, Any]:
    previous_repos = previous_repos or {}
    repos: dict[str, Any] = {}
    for repo in REPOS:
        previous = previous_repos.get(repo, {}) if isinstance(previous_repos, dict) else {}
        repo_api = f"https://api.github.com/repos/{repo}"
        try:
            repo_data = _json_get(repo_api, token)
            repo_error = None
            if isinstance(repo_data, dict) and repo_data.get("private") is True:
                # A token that can read private repos must never publish
                # their download links on the public website.
                raise SystemExit(
                    f"Refusing to publish {repo}: it is a private repository, so its "
                    "download links would be dead for visitors. Make it public or "
                    "remove it from REPOS in tools/sync_repo_metadata.py."
                )
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


def stamp_html_versions(payload: dict[str, Any], pages_root: Path = Path(".")) -> None:
    """Write latest release tags into static HTML as fallback content."""
    import re

    repos = payload.get("repos", {})
    for page in sorted(Path(pages_root).glob("*.html")):
        original = html = page.read_text(encoding="utf-8")
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

                stamped = steel_pattern.sub(steel_repl, html)
                if stamped != html:
                    print(f"  stamped {page.name}: {repo_key} steel -> {tag}")
                html = stamped

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

            stamped = pattern.sub(repl, html)
            if stamped != html:
                print(f"  stamped {page.name}: {repo_key} -> {tag}")
            html = stamped

        # Rewrite only on a real change, with the repository's LF endings, so
        # an unchanged badge never shows up as a modified file.
        if html != original:
            page.write_text(html, encoding="utf-8", newline="\n")
            print(f"updated {page.name} with static version badges")


def main() -> int:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    output = Path("repo-metadata.json")
    previous = _load_previous_payload(output)
    previous_repos = (previous or {}).get("repos")
    payload = build_metadata(token, previous_repos if isinstance(previous_repos, dict) else {})
    # A steel badge added to a page later still refreshes its "Updated" date,
    # even before its repo joins STEEL_RELEASE_REPOS.
    steel_badges = STEEL_RELEASE_REPOS | steel_badge_repos(Path("."))
    if previous is not None and visible_metadata(previous, steel_badges) == visible_metadata(payload, steel_badges):
        # Keep the exact bytes so the badge-stamp step finds nothing to
        # commit. Only generated_at/source_event or an unshown push date moved.
        print(f"metadata unchanged (timestamps only); kept {output} as is")
        stamp_html_versions(previous)
        return 0
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {output}")
    stamp_html_versions(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
