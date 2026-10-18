#!/usr/bin/env python3
"""Fail when the live site's downloads have lagged GitHub releases for too long.

Reads the public https://bluecollar-systems.com/repo-metadata.json (the file
every Download button on the site uses) and, for each importer repository the
site tracks, the release a deploy would publish now: the newest published,
final ``v*`` release (sync_repo_metadata.importer_tag_prefix(); a tracked repo
outside the PDF importers uses GitHub's /releases/latest instead), plus the
newest ``steel-v*`` shape-pack release in the repositories that host one. That
is the selection rule of tools/sync_repo_metadata.py, read from it, so a
deploy always clears what this reports.

Shape-pack releases never deploy the site by themselves (the
steel-shapes-release workflow publishes them with GITHUB_TOKEN, which starts
no notify-website-deploy run), so the report asks for the manual deploy.

A difference younger than the grace period (24 hours) is only a warning: the
release deploy normally closes it within minutes. An older one fails the
check. The age is measured from the publish time of the first GitHub release
the site is missing. A live release that GitHub no longer lists as published
(deleted, turned back into a draft or a prerelease) fails at once, because
its download link may already be dead.

Read-only: it never deploys, builds or changes anything. Usage:
    python tools/check_release_drift.py [--report drift.md] [--grace-hours 24]

Exit codes: 0 in sync or within the grace period, 1 stale beyond it,
2 the check could not run (site or GitHub API unreachable, or any unexpected
error in this tool). Only a report that found stale downloads carries
STALE_MARKER; the drift workflow opens its issue only on exit 1 with that
marker, so a crash can never read as drift.
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_repo_metadata as sync  # noqa: E402  (shared release selection rule)

DEFAULT_URL = "https://bluecollar-systems.com/repo-metadata.json"
DEFAULT_GRACE_HOURS = 24.0
# The drift workflow finds its one open issue by this marker.
ISSUE_MARKER = "<!-- release-drift-check -->"
# Written only into a finished report that found stale downloads.
STALE_MARKER = "<!-- release-drift-stale -->"

IMPORTER = "importer"
SHAPE_PACK = "shape pack"

EXIT_IN_SYNC = 0
EXIT_STALE = 1
EXIT_UNCHECKED = 2


class CheckError(RuntimeError):
    """The live metadata or the GitHub releases could not be read."""


def channels(repo: str) -> list[tuple[str, str | None, str]]:
    """(metadata field, tag prefix or None for /releases/latest, label) per channel.

    The same rule tools/sync_repo_metadata.py publishes with.
    """
    found: list[tuple[str, str | None, str]] = [
        ("latest_release", sync.importer_tag_prefix(repo), IMPORTER),
    ]
    if repo in sync.STEEL_RELEASE_REPOS:
        found.append(("steel_release", sync.STEEL_TAG_PREFIX, SHAPE_PACK))
    return found


class ChannelResult(NamedTuple):
    repo: str
    channel: str
    live_tag: str | None
    github_tag: str | None
    # When the site started to lag; None for "already broken, no grace".
    behind_since: dt.datetime | None
    in_sync: bool
    note: str = ""

    def age_hours(self, now: dt.datetime) -> float | None:
        if self.behind_since is None:
            return None
        return max(0.0, (now - self.behind_since).total_seconds() / 3600)

    def is_stale(self, now: dt.datetime, grace_hours: float) -> bool:
        if self.in_sync:
            return False
        age = self.age_hours(now)
        return age is None or age > grace_hours


def parse_time(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _download_view(release: dict[str, Any] | None) -> tuple:
    """What a visitor's download button depends on: the tag and its files."""
    if not isinstance(release, dict):
        return (None, ())
    # Order-insensitive: only which files are offered matters, not the order
    # GitHub happened to list them in.
    assets = tuple(sorted(
        tuple(str((asset or {}).get(key) or "") for key in ("name", "url", "digest"))
        for asset in release.get("assets") or []
    ))
    return (release.get("tag"), assets)


def _candidates(
    releases: list[dict[str, Any]],
    tag_prefix: str | None,
    latest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """The channel's published, final releases, the one a deploy picks first."""
    if tag_prefix is not None:
        return sync.final_tagged_releases(releases, tag_prefix)
    # GitHub's /releases/latest: the sync publishes exactly that release. The
    # rest of the listing only dates how far behind the site is.
    if not isinstance(latest, dict) or not latest.get("tag_name") or latest.get("draft") or latest.get("prerelease"):
        return []
    rest = [r for r in sync.final_tagged_releases(releases, "") if r.get("tag_name") != latest.get("tag_name")]
    return [latest, *rest]


def compare_channel(
    repo: str,
    channel: str,
    live_release: dict[str, Any] | None,
    releases: list[dict[str, Any]],
    tag_prefix: str | None,
    live_generated_at: dt.datetime | None,
    latest: dict[str, Any] | None = None,
) -> ChannelResult:
    """Compare one release channel of one repo with what GitHub publishes.

    ``releases`` is the raw /releases listing (newest first). The expected
    release is its first published, final entry with the channel prefix, or,
    when tag_prefix is None, ``latest`` (GitHub's /releases/latest answer).
    """
    candidates = _candidates(releases, tag_prefix, latest)
    live_tag = live_release.get("tag") if isinstance(live_release, dict) else None
    if not candidates:
        # The deploy keeps the previous snapshot when GitHub lists nothing,
        # so a deploy would not change this channel either.
        return ChannelResult(repo, channel, live_tag, None, None, True, "no published GitHub release")

    expected = sync._release_summary(candidates[0])
    github_tag = expected.get("tag")
    if _download_view(live_release) == _download_view(expected):
        return ChannelResult(repo, channel, live_tag, github_tag, None, True)

    if live_tag == github_tag:
        # Same tag, different files: an asset was added, replaced or removed
        # after the deploy. Count from the release's publish time.
        return ChannelResult(
            repo, channel, live_tag, github_tag,
            parse_time(expected.get("published_at")), False,
            "same tag, but the download files differ",
        )

    if live_tag:
        tags = [release.get("tag_name") for release in candidates]
        if live_tag not in tags:
            if isinstance(releases, list) and len(releases) >= 100:
                reason = "is not among the 100 newest GitHub releases (far behind, or withdrawn)"
            else:
                reason = "is no longer a published GitHub release (deleted, draft or prerelease), so its download may be dead"
            return ChannelResult(
                repo, channel, live_tag, github_tag, None, False, f"the live release {live_tag} {reason}",
            )
        newer = candidates[: tags.index(live_tag)]
    else:
        # The site shows no release for this channel. Releases published
        # after the live snapshot was generated are the ones it is missing.
        newer = [
            release for release in candidates
            if live_generated_at is not None
            and (parse_time(release.get("published_at")) or live_generated_at) > live_generated_at
        ]
        if not newer:
            return ChannelResult(
                repo, channel, None, github_tag, None, False,
                "the live site shows no release although GitHub has one",
            )

    known = [
        moment for moment in (parse_time(release.get("published_at")) for release in newer)
        if moment is not None
    ]
    behind_since = min(known) if known else None
    count = len(newer)
    note = f"{count} newer release{'s' if count != 1 else ''} on GitHub"
    if behind_since is None:
        note += " (publish time unknown)"
    return ChannelResult(repo, channel, live_tag, github_tag, behind_since, False, note)


def compare(
    live: dict[str, Any],
    releases_by_repo: dict[str, list[dict[str, Any]]],
    latest_by_repo: dict[str, dict[str, Any] | None] | None = None,
) -> list[ChannelResult]:
    """Every tracked repo and channel, in a stable order."""
    live_repos = live.get("repos") if isinstance(live.get("repos"), dict) else {}
    generated_at = parse_time(live.get("generated_at"))
    latest_by_repo = latest_by_repo or {}
    results: list[ChannelResult] = []
    for repo in sync.REPOS:
        entry = live_repos.get(repo)
        for field, prefix, label in channels(repo):
            if not isinstance(entry, dict):
                results.append(ChannelResult(
                    repo, label, None, None, None, False,
                    "the repository is missing from the live metadata",
                ))
                continue
            results.append(compare_channel(
                repo, label, entry.get(field), releases_by_repo.get(repo, []), prefix, generated_at,
                latest_by_repo.get(repo),
            ))
    return results


# ---------------------------------------------------------------------------
# Network reads
# ---------------------------------------------------------------------------

def fetch_live_metadata(
    url: str = DEFAULT_URL,
    *,
    attempts: int = 3,
    delay: float = 10,
    timeout: float = 15,
    opener: Callable | None = None,
    sleep: Callable = time.sleep,
) -> dict[str, Any]:
    """The metadata visitors get, bypassing caches like the deploy check does."""
    open_url = opener or urllib.request.urlopen
    parsed = urllib.parse.urlsplit(url)
    last_error = "no response"
    for attempt in range(1, attempts + 1):
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        query.append(("drift_check", uuid.uuid4().hex))
        request = urllib.request.Request(
            urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query), fragment="")),
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache, no-store",
                "Pragma": "no-cache",
                "User-Agent": "Mozilla/5.0 (BlueCollar Website release drift check)",
            },
        )
        try:
            with open_url(request, timeout=timeout) as response:
                if response.getcode() != 200:
                    raise CheckError(f"HTTP {response.getcode()}")
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("repos"), dict):
                raise CheckError("the live metadata has no repos object")
            return payload
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
        except (OSError, http.client.HTTPException, ValueError, CheckError) as exc:
            last_error = str(exc)
        print(f"Live metadata attempt {attempt}/{attempts}: {last_error}", file=sys.stderr)
        if attempt < attempts:
            sleep(delay)
    raise CheckError(f"could not read {url}: {last_error}")


def fetch_releases(token: str | None) -> dict[str, list[dict[str, Any]]]:
    releases: dict[str, list[dict[str, Any]]] = {}
    for repo in sync.REPOS:
        try:
            listing = sync._json_get(sync.releases_url(repo), token)
        except urllib.error.HTTPError as exc:
            raise CheckError(f"GitHub API answered HTTP {exc.code} for {repo} releases") from exc
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise CheckError(f"could not read {repo} releases: {exc}") from exc
        if not isinstance(listing, list):
            raise CheckError(f"unexpected GitHub API answer for {repo} releases")
        releases[repo] = listing
    return releases


def fetch_latest_releases(token: str | None) -> dict[str, dict[str, Any] | None]:
    """GitHub's /releases/latest for each repo whose importer channel uses it."""
    latest: dict[str, dict[str, Any] | None] = {}
    for repo in sync.REPOS:
        if sync.importer_tag_prefix(repo) is not None:
            continue
        try:
            answer = sync._json_get(sync.latest_release_url(repo), token)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                latest[repo] = None  # no release yet; the sync keeps its last snapshot
                continue
            raise CheckError(f"GitHub API answered HTTP {exc.code} for {repo} latest release") from exc
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise CheckError(f"could not read {repo} latest release: {exc}") from exc
        if not isinstance(answer, dict):
            raise CheckError(f"unexpected GitHub API answer for {repo} latest release")
        latest[repo] = answer
    return latest


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _short(repo: str) -> str:
    return repo.split("/", 1)[-1]


def _age_text(result: ChannelResult, now: dt.datetime) -> str:
    age = result.age_hours(now)
    if age is None:
        return "no grace (fix now)"
    if age < 48:
        return f"{age:.0f} h"
    return f"{age / 24:.1f} days"


def render_report(
    results: list[ChannelResult],
    now: dt.datetime,
    grace_hours: float,
    url: str = DEFAULT_URL,
    live_generated_at: str | None = None,
) -> str:
    stale = [r for r in results if r.is_stale(now, grace_hours)]
    waiting = [r for r in results if not r.in_sync and not r.is_stale(now, grace_hours)]
    if stale:
        headline = (
            f"**The live site has offered old downloads for more than {grace_hours:g} hours.** "
            "Visitors pressing Download get the version in the Live column."
        )
    elif waiting:
        headline = (
            f"The live site is behind GitHub, but for less than {grace_hours:g} hours. "
            "The release deploy normally closes this within minutes; the check fails if it lasts."
        )
    else:
        headline = "The live site offers the latest GitHub release of every importer."

    lines = [ISSUE_MARKER]
    if stale:
        lines.append(STALE_MARKER)
    lines += [
        "## Live site downloads compared with GitHub releases",
        "",
        headline,
        "",
        "| Repository | Channel | Live site | GitHub latest | Behind for | Status |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        if result.in_sync:
            status, behind = "in sync", "-"
        else:
            status = "STALE" if result.is_stale(now, grace_hours) else "within grace"
            behind = _age_text(result, now)
        if result.note and not result.in_sync:
            status += f": {result.note}"
        lines.append(
            f"| {_short(result.repo)} | {result.channel} | {result.live_tag or 'none'} "
            f"| {result.github_tag or 'none'} | {behind} | {status} |"
        )
    lines += [
        "",
        f"Checked {now.strftime('%Y-%m-%d %H:%M')} UTC against {url}"
        + (f" (generated {live_generated_at})" if live_generated_at else "")
        + f". Grace period: {grace_hours:g} hours.",
    ]
    if stale:
        lines += [
            "",
            "**How to fix:** run the `website-ci` workflow on `main` with `deploy_production` "
            "set to true. It fetches the current releases, checks every download link, "
            "deploys and verifies the live metadata. This issue closes itself on the first "
            "daily check that finds the site in sync.",
            "",
            "If an importer release did not deploy the site by itself, look at the "
            "`website-ci` run its `product-release` dispatch started: a failed check, or a "
            "refused metadata-only deploy because `main` holds website changes that were "
            "never deployed, leaves the old downloads live.",
        ]
    if any(r.channel == SHAPE_PACK and not r.in_sync for r in results):
        lines += [
            "",
            "**A shape pack (`steel-v*`) release needs the manual deploy.** Shape pack "
            "releases never deploy the site by themselves: the `steel-shapes-release` "
            "workflow in the SketchUp and FreeCAD repos publishes them with `GITHUB_TOKEN`, "
            "which starts no `notify-website-deploy` run, so no `product-release` dispatch "
            "reaches the website. After every shape pack release, run `website-ci` on `main` "
            "with `deploy_production` set to true.",
        ]
    return "\n".join(lines) + "\n"


def evaluate(
    live: dict[str, Any],
    releases_by_repo: dict[str, list[dict[str, Any]]],
    now: dt.datetime,
    grace_hours: float,
    url: str = DEFAULT_URL,
    latest_by_repo: dict[str, dict[str, Any] | None] | None = None,
) -> tuple[int, str, list[ChannelResult]]:
    results = compare(live, releases_by_repo, latest_by_repo)
    report = render_report(results, now, grace_hours, url, live.get("generated_at"))
    code = EXIT_STALE if any(r.is_stale(now, grace_hours) for r in results) else EXIT_IN_SYNC
    return code, report, results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL, help="live metadata URL")
    parser.add_argument("--grace-hours", type=float, default=DEFAULT_GRACE_HOURS)
    parser.add_argument("--report", type=Path, help="also write the Markdown report to this file")
    parser.add_argument("--now", help="ISO time to judge ages against (tests); default: now")
    args = parser.parse_args(argv)
    if args.grace_hours < 0:
        parser.error("--grace-hours must not be negative")

    now = parse_time(args.now) if args.now else dt.datetime.now(dt.UTC)
    if now is None:
        parser.error("--now must be an ISO date and time")
    try:
        return _check(args, now)
    except CheckError as exc:
        return _could_not_run(args.report, str(exc))
    except Exception as exc:  # noqa: BLE001 - any crash is "could not check", never "stale"
        traceback.print_exc()
        return _could_not_run(args.report, f"unexpected error in check_release_drift.py: {type(exc).__name__}: {exc}")


def _could_not_run(report: Path | None, reason: str) -> int:
    """Status 2, with a report that cannot be mistaken for drift."""
    if report:
        try:
            report.write_text(
                f"{ISSUE_MARKER}\n## Release drift check could not run\n\n{reason}\n\n"
                "This is not a drift finding: the check did not finish, so it says nothing "
                "about the live downloads.\n",
                encoding="utf-8", newline="\n",
            )
        except OSError as exc:
            print(f"Could not write {report}: {exc}", file=sys.stderr)
    print(f"::error::Release drift check could not run: {reason}")
    return EXIT_UNCHECKED


def _check(args: argparse.Namespace, now: dt.datetime) -> int:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    live = fetch_live_metadata(args.url)
    releases = fetch_releases(token)
    latest = fetch_latest_releases(token)

    code, report, results = evaluate(live, releases, now, args.grace_hours, args.url, latest)
    if args.report:
        args.report.write_text(report, encoding="utf-8", newline="\n")
    print(report)
    for result in results:
        if result.in_sync:
            continue
        where = f"{_short(result.repo)} {result.channel}"
        detail = f"live {result.live_tag or 'none'}, GitHub {result.github_tag or 'none'}"
        if result.note:
            detail += f"; {result.note}"
        if result.channel == SHAPE_PACK:
            detail += "; shape pack releases need the manual deploy (deploy_production=true)"
        if result.is_stale(now, args.grace_hours):
            print(f"::error::{where} downloads are stale ({detail}).")
        else:
            print(f"::warning::{where} downloads are behind, within the grace period ({detail}).")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
