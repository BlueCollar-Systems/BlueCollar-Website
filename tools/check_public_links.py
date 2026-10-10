#!/usr/bin/env python3
"""Check every website link and download the way a stranger sees them.

No login and no token: a link that only works for a signed-in team member
(for example a download in a private GitHub repo) is reported as broken,
because that is what a visitor gets.

What is checked:
  * Every href/src in the root *.html pages and p/index.html.
    - On-site links (/feedback, /styles.css, https://bluecollar-systems.com/...)
      must exist in this checkout under Cloudflare Pages rules (/x -> x.html,
      /p/<id> -> p/index.html through _redirects, trailing / -> index.html).
      This part needs no network.
    - Other http(s) links get one small anonymous GET (Range: bytes=0-0).
  * The download links nav.js puts on the buttons at page load, picked from
    repo-metadata.json with the same rules nav.js uses.
  * With --base URL (after a deploy): every page and on-site link is also
    requested from that live site.

Usage:
    python tools/check_public_links.py               # checkout + external links
    python tools/check_public_links.py --offline     # checkout only, no network
    python tools/check_public_links.py --base https://bluecollar-systems.com

Exit code 1 when anything is broken; each problem names the page and URL.
Standard library only.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_site  # noqa: E402  (shared Cloudflare Pages path rules)

USER_AGENT = "Mozilla/5.0 (BlueCollar Website public link check)"
TIMEOUT_SECONDS = 20
RETRY_DELAY_SECONDS = 3
MAX_WORKERS = 8

# Links that are allowed to fail, each with a dated reason and who approved
# it. Keep this empty unless the owner agrees a link may stay broken for a
# while; an entry is reported as "skipped", never as passing.
#     "https://example.invalid/page": "2026-10-10: reason (approved by ...)",
KNOWN_EXCEPTIONS: dict[str, str] = {}

# Mirrors nav.js isPrimaryPdfImporterAsset / primaryAssetRank. A test checks
# that nav.js still contains these patterns, so the two cannot drift apart.
_PRIMARY_ASSET_PATTERNS = (
    re.compile(r"^(SketchUp|FreeCAD|LibreCAD|Blender)-PDF-Importer_v\d+(?:\.\d+){2}\.(rbz|zip)$", re.I),
    re.compile(r"^FreeCAD-PDF-Importer-Setup_v\d+(?:\.\d+){2}\.exe$", re.I),
    re.compile(r"^LibreCAD-PDF-Importer-Setup_v\d+(?:\.\d+){2}\.exe$", re.I),
    re.compile(r"^LibreCAD-PDF-Importer-Windows-Portable_v\d+(?:\.\d+){2}\.zip$", re.I),
)
_SETUP_EXE = re.compile(r"-(Setup)_v\d+(?:\.\d+){2}\.exe$", re.I)
_LIBRECAD_PORTABLE = re.compile(r"^LibreCAD-PDF-Importer-Windows-Portable_v\d+(?:\.\d+){2}\.zip$", re.I)
_LIBRECAD_PLAIN_ZIP = re.compile(r"^LibreCAD-PDF-Importer_v\d+(?:\.\d+){2}\.zip$", re.I)
_FALLBACK_EXTENSIONS = (".rbz", ".zip", ".aab", ".apk")


def is_primary_asset(name: Any) -> bool:
    return isinstance(name, str) and any(p.search(name) for p in _PRIMARY_ASSET_PATTERNS)


def primary_asset_rank(name: Any) -> int:
    if not name or not is_primary_asset(name):
        return 999
    if _SETUP_EXE.search(name):
        return 0
    if _LIBRECAD_PORTABLE.search(name):
        return 1
    if _LIBRECAD_PLAIN_ZIP.search(name):
        return 20
    return 5


def find_download_asset(assets: Any, preferred_name: str | None = None) -> dict | None:
    """The asset nav.js puts on a download button (same order of choice)."""
    if not isinstance(assets, list):
        return None
    if preferred_name:
        for asset in assets:
            if isinstance(asset, dict) and asset.get("name") == preferred_name:
                return asset
        return None
    best, best_rank = None, 999
    for asset in assets:
        if not isinstance(asset, dict) or not is_primary_asset(asset.get("name")):
            continue
        rank = primary_asset_rank(asset.get("name"))
        if rank < best_rank:
            best, best_rank = asset, rank
    if best is not None:
        return best
    for asset in assets:
        name = asset.get("name") if isinstance(asset, dict) else None
        if isinstance(name, str) and name.lower().endswith(_FALLBACK_EXTENSIONS):
            return asset
    return None


def _release_for(repo: dict, channel: str | None) -> dict | None:
    if not isinstance(repo, dict):
        return None
    release = repo.get("steel_release") if channel == "steel" else repo.get("latest_release")
    return release if isinstance(release, dict) else None


class _DynamicLinkParser(HTMLParser):
    """Elements whose href nav.js replaces at page load."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: (v or "") for k, v in attrs}
        if "data-repo-asset-link" in values or "data-repo-release-link" in values:
            self.elements.append(values)


def nav_js_links(html: str, metadata: dict) -> list[tuple[str, str]]:
    """(description, url) for every link nav.js would set on this page."""
    repos = metadata.get("repos") if isinstance(metadata, dict) else None
    repos = repos if isinstance(repos, dict) else {}
    parser = _DynamicLinkParser()
    parser.feed(html)
    parser.close()
    links: list[tuple[str, str]] = []
    for element in parser.elements:
        channel = element.get("data-release-channel") or None
        if "data-repo-asset-link" in element:
            key = element["data-repo-asset-link"]
            preferred = element.get("data-asset-name") or None
            release = _release_for(repos.get(key), channel)
            # No release in the metadata: nav.js leaves the static href,
            # which is already checked as an ordinary link.
            asset = find_download_asset(release.get("assets"), preferred) if release else None
            if asset and asset.get("url"):
                links.append((f"download button for {key}", asset["url"]))
            elif release and not preferred and release.get("url"):
                links.append((f"download button for {key}", release["url"]))
        if "data-repo-release-link" in element:
            key = element["data-repo-release-link"]
            repo = repos.get(key)
            release = _release_for(repo, channel)
            if release and release.get("url"):
                links.append((f"release notes link for {key}", release["url"]))
            elif isinstance(repo, dict) and repo.get("repo_url"):
                links.append((f"release notes link for {key}", repo["repo_url"]))
    return links


def site_pages(root: Path) -> list[Path]:
    pages = sorted(p for p in Path(root).glob("*.html") if p.is_file())
    part_page = Path(root) / "p" / "index.html"
    if part_page.is_file():
        pages.append(part_page)
    return pages


def collect_links(root: Path, metadata: dict) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return ({site path: sources}, {external url: sources})."""
    root = Path(root)
    site: dict[str, set[str]] = {}
    external: dict[str, set[str]] = {}
    for page in site_pages(root):
        rel = page.relative_to(root).as_posix()
        html = page.read_text(encoding="utf-8")
        for ref in build_site.html_references(html):
            kind = build_site.classify_reference(build_site.page_route(rel), ref)
            if kind is None:
                continue
            target = kind[1] if kind[0] == "site" else urllib.parse.urldefrag(kind[1])[0]
            bucket = site if kind[0] == "site" else external
            bucket.setdefault(target, set()).add(f"{rel} ({ref})" if kind[0] == "site" else rel)
        for description, url in nav_js_links(html, metadata):
            kind = build_site.classify_reference(build_site.page_route(rel), url)
            if kind is None:
                continue
            bucket = site if kind[0] == "site" else external
            bucket.setdefault(kind[1], set()).add(f"{rel} ({description})")
    return site, external


def check_url(
    url: str,
    *,
    opener: Callable | None = None,
    sleep: Callable = time.sleep,
    attempts: int = 2,
    timeout: float = TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    """Anonymous ranged GET. Returns (ok, short result such as 'HTTP 206')."""
    open_url = opener or urllib.request.urlopen
    result = "no response"
    for attempt in range(1, attempts + 1):
        # Deliberately no Authorization header: check what a stranger gets.
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Range": "bytes=0-0",
                "Cache-Control": "no-cache",
                "Accept": "*/*",
            },
        )
        try:
            with open_url(request, timeout=timeout) as response:
                status = response.getcode()
        except urllib.error.HTTPError as exc:
            status = exc.code
        except (OSError, http.client.HTTPException, ValueError) as exc:
            status = None
            result = f"network error: {exc}"
        if status is not None:
            result = f"HTTP {status}"
            if status < 400:
                return True, result
        if attempt < attempts:
            sleep(RETRY_DELAY_SECONDS)
    return False, result


def run_checks(
    root: Path,
    *,
    offline: bool = False,
    base: str | None = None,
    opener: Callable | None = None,
    sleep: Callable = time.sleep,
    verbose: bool = False,
) -> tuple[list[str], int]:
    """Return (problem lines, number of links checked)."""
    root = Path(root)
    problems: list[str] = []
    metadata_path = root / "repo-metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"repo-metadata.json could not be read ({exc}); download buttons cannot be checked"], 0

    site, external = collect_links(root, metadata)
    redirects = build_site.load_redirects(root)
    for path in sorted(site):
        if build_site.resolve_site_path(root, path, redirects) is None:
            for source in sorted(site[path]):
                problems.append(f"BROKEN {source}: {path} is not a file on the site")

    to_fetch: dict[str, set[str]] = {}
    if not offline:
        for url, sources in external.items():
            to_fetch.setdefault(url, set()).update(sources)
    if base:
        origin = base.rstrip("/")
        for page in site_pages(root):
            rel = page.relative_to(root).as_posix()
            if rel != "404.html":
                to_fetch.setdefault(origin + build_site.page_route(rel), set()).add(f"{rel} (the page itself)")
        for path, sources in site.items():
            to_fetch.setdefault(origin + path, set()).update(sources)

    skipped = sorted(url for url in to_fetch if url in KNOWN_EXCEPTIONS)
    for url in skipped:
        print(f"SKIPPED {url}: {KNOWN_EXCEPTIONS[url]}")
    urls = sorted(url for url in to_fetch if url not in KNOWN_EXCEPTIONS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(lambda u: check_url(u, opener=opener, sleep=sleep), urls))
    for url, (ok, result) in zip(urls, results):
        if verbose:
            print(f"{'ok    ' if ok else 'BROKEN'} {result:<10} {url}")
        if not ok:
            for source in sorted(to_fetch[url]):
                problems.append(f"BROKEN {source}: {url} ({result})")
    return problems, len(site) + len(urls)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path("."), help="website checkout (default: .)")
    parser.add_argument("--offline", action="store_true", help="check on-site links only; no network")
    parser.add_argument("--base", help="also request every page and on-site link from this live site")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every link and its result")
    args = parser.parse_args(argv)
    if args.base and not urllib.parse.urlsplit(args.base).scheme.startswith("http"):
        parser.error("--base must start with http:// or https://")
    problems, checked = run_checks(args.root, offline=args.offline, base=args.base, verbose=args.verbose)
    for line in problems:
        print(line, file=sys.stderr)
    if problems:
        print(f"Public link check failed: {len(problems)} broken of {checked} links checked.", file=sys.stderr)
        return 1
    scope = "on-site only, no network" if args.offline else "no login, no token"
    print(f"Public link check passed: {checked} links checked ({scope}), 0 broken.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
