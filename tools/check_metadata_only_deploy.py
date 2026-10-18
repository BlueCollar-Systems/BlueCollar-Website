#!/usr/bin/env python3
"""Refuse a release deploy that would publish more than new download metadata.

An importer's product-release dispatch deploys the site by itself, so the
version badges and Download buttons follow each release without a separate
GO (owner decision O13, deploy-only). Every other website change still goes
live only through a manual website-ci run with deploy_production=true. This
guard keeps the automatic deploy to that job:

1. Find the commit that is live now: the head commit of the newest website-ci
   run whose "Deploy to Cloudflare Pages" step succeeded (GitHub Actions API,
   read back through the newest 1,000 runs of each dispatch kind).
2. Build two public folders the same clean way, each in its own new temporary
   git worktree and its own new output folder: one from the commit about to
   be deployed, one from the live commit. Each worktree gets the same freshly
   synced repo-metadata.json, and each commit's OWN tools do the work, run as
   a subprocess with that worktree as the working folder and only that
   worktree's tools importable (python -B -E -s):
     - tools/sync_repo_metadata.py stamp_html_versions(payload) stamps the
       version badges in the worktree's *.html pages;
     - python tools/build_site.py --source . --out <folder> builds the folder.
   So a change on main to the public file list or to the badge stamping
   builds differently from the live commit, and counts as a website change.
3. Require the _site folder about to be uploaded to be byte-for-byte the clean
   build of its own commit (no leftover or uncommitted file rides along), and
   that clean build to be byte-for-byte the live commit's build.

So only repo-metadata.json and the badges stamped from it can differ from
production. If main holds any other public change that was never deployed,
the deploy stops before upload and names the files; the manual deploy
publishes them (and the new downloads) once they are approved. When the live
commit cannot be found, fetched or rebuilt with its own tools (for example a
commit older than tools/build_site.py), the guard refuses too: it never
guesses, and the manual deploy is the way forward.

Read-only for the site: it never deploys or pushes. Usage, from the
repository root after tools/sync_repo_metadata.py and tools/build_site.py:
    python tools/check_metadata_only_deploy.py [--site _site] [--deployed-sha SHA]

Exit codes: 0 only metadata differs from production, 1 refused (nothing may
deploy).
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

WORKFLOW_FILE = "website-ci.yml"
DEPLOY_JOB = "deploy-pages"
DEPLOY_STEP = "Deploy to Cloudflare Pages"
PRODUCTION_BRANCH = "main"
DEFAULT_SITE = "_site"

# The run history is read newest first, 100 runs a page. The Actions API lists
# at most 1,000 runs for one event filter, so ten pages is all there is.
RUNS_PER_PAGE = 100
MAX_RUN_PAGES = 10
# Jobs are read only for runs that could have deployed; past this many the
# guard stops looking and refuses rather than guessing.
MAX_JOB_LOOKUPS = 100
# website-ci.yml has no run-name, so GitHub titles a repository_dispatch run
# with its event type. These types only validate (deploy-pages needs
# product-release), so their runs are skipped without reading their jobs. A
# title outside this set is looked at, so a future run-name only costs calls.
VALIDATION_ONLY_DISPATCHES = frozenset({"product-update", "steel-shapes-release", "steel-shapes-update"})

# What a commit must hold for the guard to rebuild its public folder.
BUILD_TOOL = "tools/build_site.py"
STAMP_TOOL = "tools/sync_repo_metadata.py"
# The stamp driver's exit code for "this commit's sync tool has no usable
# stamp_html_versions()".
EXIT_TOOLS_UNSUPPORTED = 64
# Seconds one stamp or build subprocess may take.
TOOL_TIMEOUT = 600
# Git checkout/fetch/cleanup must also finish or refuse within a bounded time.
GIT_TIMEOUT = 60

# Runs in the worktree (cwd) with -B -E -s, so the only sync_repo_metadata it
# can import is that commit's own tools/sync_repo_metadata.py. It calls
# stamp_html_versions(payload) with the payload alone: every version of the
# function stamps the *.html pages of the working folder.
STAMP_DRIVER = f"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools"))
try:
    import sync_repo_metadata
    stamp = sync_repo_metadata.stamp_html_versions
except (ImportError, AttributeError, SyntaxError) as exc:
    print(f"{STAMP_TOOL} has no usable stamp_html_versions(): {{exc!r}}", file=sys.stderr)
    raise SystemExit({EXIT_TOOLS_UNSUPPORTED})
if not callable(stamp):
    print("{STAMP_TOOL} stamp_html_versions is not a function", file=sys.stderr)
    raise SystemExit({EXIT_TOOLS_UNSUPPORTED})
stamp(json.loads(Path("repo-metadata.json").read_text(encoding="utf-8")))
"""

MANUAL_DEPLOY_HINT = (
    "Run website-ci manually on main with deploy_production=true when the site is ready; "
    "it publishes the approved site and the new downloads together."
)


class GuardError(RuntimeError):
    """The live commit could not be found or rebuilt; nothing may deploy."""


class ToolsUnsupported(GuardError):
    """A commit's own tools cannot rebuild its public folder the guard's way."""


# ---------------------------------------------------------------------------
# Which commit is live
# ---------------------------------------------------------------------------

def _api_get(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bluecollar-website-release-deploy-guard/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def runs_url(repo: str, event: str, page: int) -> str:
    return (
        f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs"
        f"?event={event}&status=completed&exclude_pull_requests=true"
        f"&per_page={RUNS_PER_PAGE}&page={page}"
    )


def jobs_url(repo: str, run_id: Any) -> str:
    return f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?filter=all&per_page=100"


def _completed_runs(repo: str, event: str, api_get: Callable[[str], Any]) -> tuple[list[dict[str, Any]], int, bool]:
    """(runs newest first, total the API reports, True if the API had more)."""
    runs: list[dict[str, Any]] = []
    total = 0
    for page in range(1, MAX_RUN_PAGES + 1):
        data = api_get(runs_url(repo, event, page)) or {}
        batch = [run for run in data.get("workflow_runs") or [] if isinstance(run, dict)]
        try:
            total = max(total, int(data.get("total_count") or 0))
        except (TypeError, ValueError):
            pass
        for run in batch:
            run.setdefault("event", event)
        runs.extend(batch)
        if len(batch) < RUNS_PER_PAGE:
            return runs, max(total, len(runs)), False
    return runs, max(total, len(runs)), True


def _could_have_deployed(run: dict[str, Any], current_run_id: str | None) -> bool:
    if current_run_id and str(run.get("id")) == str(current_run_id):
        return False
    if run.get("head_branch") != PRODUCTION_BRANCH or not run.get("head_sha"):
        return False
    if run.get("event") == "repository_dispatch" and run.get("display_title") in VALIDATION_ONLY_DISPATCHES:
        return False
    return True


def _uploaded(jobs: Any) -> bool:
    for job in (jobs or {}).get("jobs") or []:
        if job.get("name") != DEPLOY_JOB:
            continue
        for step in job.get("steps") or []:
            if step.get("name") == DEPLOY_STEP and step.get("conclusion") == "success":
                return True
    return False


def find_deployed_commit(
    repo: str,
    api_get: Callable[[str], Any],
    *,
    current_run_id: str | None = None,
) -> tuple[str, int]:
    """(head commit, run id) of the newest run that uploaded the site."""
    read: list[str] = []
    candidates: list[dict[str, Any]] = []
    for event in ("workflow_dispatch", "repository_dispatch"):
        runs, total, more = _completed_runs(repo, event, api_get)
        read.append(
            f"the newest {len(runs)} of {total} {event} runs (the Actions API lists no more)"
            if more else f"all {len(runs)} completed {event} runs"
        )
        candidates.extend(run for run in runs if _could_have_deployed(run, current_run_id))
    candidates.sort(key=lambda run: run.get("run_started_at") or run.get("created_at") or "", reverse=True)

    for run in candidates[:MAX_JOB_LOOKUPS]:
        if _uploaded(api_get(jobs_url(repo, run.get("id")))):
            return str(run["head_sha"]), int(run["id"])

    checked = min(len(candidates), MAX_JOB_LOOKUPS)
    why = (
        f"It read {' and '.join(read)} of {WORKFLOW_FILE}. {len(candidates)} of them could have deployed "
        f"(manual runs and product-release dispatches on {PRODUCTION_BRANCH}); the jobs of "
        f"{'all of them' if checked == len(candidates) else f'the newest {checked}'} were read and none "
        f"has a successful '{DEPLOY_STEP}' step."
    )
    if checked < len(candidates):
        why += f" The guard reads at most {MAX_JOB_LOOKUPS} runs' jobs, so the last deploy is older than that."
    elif any("lists no more" in part for part in read):
        why += " The last deploy is older than the run history the Actions API lists."
    raise GuardError(f"The live commit is unknown, so the guard cannot compare against it. {why}")


# ---------------------------------------------------------------------------
# Clean builds, each with its own commit's tools
# ---------------------------------------------------------------------------

def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise GuardError(f"Git {' '.join(args[:2])} took longer than {GIT_TIMEOUT} s.") from exc


def _require_commit(repo_root: Path, sha: str) -> None:
    if _git(repo_root, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0:
        return
    fetched = _git(repo_root, "fetch", "--no-tags", "--depth=1", "origin", sha)
    if fetched.returncode != 0 or _git(repo_root, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        raise GuardError(f"Could not fetch commit {sha}: {fetched.stderr.strip() or 'not found'}.")


_SECRET_NAME = re.compile(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|(^|_)KEY$", re.IGNORECASE)


def _tool_env() -> dict[str, str]:
    """The environment for a commit's tools: no tokens or other secrets."""
    return {name: value for name, value in os.environ.items() if not _SECRET_NAME.search(name)}


def _tail(text: str, lines: int = 12) -> str:
    kept = [line for line in (text or "").strip().splitlines() if line.strip()][-lines:]
    return " | ".join(kept) or "no output"


def _run_tool(worktree: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run Python in `worktree` so that only its own files are importable."""
    command = [sys.executable, "-B", "-E", "-s", "-X", "utf8", *args]
    try:
        return subprocess.run(
            command, cwd=str(worktree), env=_tool_env(), check=False,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TOOL_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise GuardError(f"{' '.join(args[:1])} in {worktree.name} took longer than {TOOL_TIMEOUT} s.") from exc


def build_commit_site(repo_root: Path, sha: str, metadata: Path, workdir: Path, label: str) -> Path:
    """The public folder `sha` makes with this metadata, built by its own tools.

    The commit is checked out in a new worktree under workdir and built into
    a new folder beside it, so nothing of another build can leak in. The
    worktree is removed again; the built folder is returned.
    """
    short = sha[:12]
    source = workdir / f"{label}-source"
    out = workdir / f"{label}-site"
    for path in (source, out):
        if path.exists():
            raise GuardError(f"Refusing to reuse {path}: every build starts from a new folder.")
    _require_commit(repo_root, sha)
    no_hooks = workdir / "no-git-hooks"
    added = _git(repo_root, "-c", f"core.hooksPath={no_hooks}", "worktree", "add", "--detach", str(source), sha)
    if added.returncode != 0:
        raise GuardError(f"Could not check out commit {sha}: {added.stderr.strip()}")
    try:
        missing = [name for name in (BUILD_TOOL, STAMP_TOOL) if not (source / name).is_file()]
        if missing:
            raise ToolsUnsupported(
                f"Commit {short} has no {' or '.join(missing)}, so the guard cannot rebuild what it publishes."
            )
        shutil.copyfile(metadata, source / "repo-metadata.json")

        stamped = _run_tool(source, ["-c", STAMP_DRIVER])
        if stamped.returncode == EXIT_TOOLS_UNSUPPORTED:
            raise ToolsUnsupported(f"Commit {short} cannot stamp version badges: {_tail(stamped.stderr)}")
        if stamped.returncode != 0:
            raise GuardError(
                f"Commit {short}'s badge stamping failed (exit {stamped.returncode}): {_tail(stamped.stderr)}"
            )

        built = _run_tool(source, [BUILD_TOOL, "--source", ".", "--out", str(out)])
        if built.returncode == 2 and "usage:" in (built.stderr or ""):
            raise ToolsUnsupported(
                f"Commit {short}'s {BUILD_TOOL} does not accept --source and --out: {_tail(built.stderr)}"
            )
        if built.returncode != 0:
            raise GuardError(
                f"Commit {short} does not build with its own {BUILD_TOOL} "
                f"(exit {built.returncode}): {_tail(built.stderr or built.stdout)}"
            )
        if not out.is_dir() or not any(out.iterdir()):
            raise ToolsUnsupported(f"Commit {short}'s {BUILD_TOOL} did not write the folder given with --out.")
    finally:
        _git(repo_root, "worktree", "remove", "--force", str(source))
        shutil.rmtree(source, ignore_errors=True)
        _git(repo_root, "worktree", "prune")
    return out


def _files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def compare_sites(new_site: Path, live_site: Path) -> list[str]:
    """One line per public file that differs between two built folders."""
    new_files, live_files = _files(new_site), _files(live_site)
    problems = [f"new public file: {name}" for name in sorted(new_files - live_files)]
    problems += [f"removed public file: {name}" for name in sorted(live_files - new_files)]
    for name in sorted(new_files & live_files):
        if not filecmp.cmp(new_site / name, live_site / name, shallow=False):
            problems.append(f"changed: {name}")
    return problems


def check(
    repo_root: Path,
    site: Path,
    metadata: Path,
    deployed_sha: str,
    head_sha: str,
    workdir: Path,
) -> list[str]:
    """Public files that differ from production; GuardError if unprovable."""
    head_site = build_commit_site(repo_root, head_sha, metadata, workdir, "deploy")
    leftovers = compare_sites(site, head_site)
    if leftovers:
        raise GuardError(
            f"The folder about to be deployed ({site}) is not the clean build of its commit "
            f"{head_sha[:12]} with this metadata, so it holds uncommitted or leftover files: "
            + "; ".join(leftovers)
        )
    if deployed_sha == head_sha:
        print(f"The commit about to be deployed is the live one ({head_sha[:12]}); only metadata can change.")
        return []
    live_site = build_commit_site(repo_root, deployed_sha, metadata, workdir, "live")
    return compare_sites(head_site, live_site)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", type=Path, default=Path(DEFAULT_SITE),
                        help="the built folder about to be deployed (default: _site)")
    parser.add_argument("--metadata", type=Path, default=Path("repo-metadata.json"),
                        help="the freshly synced metadata about to be deployed")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "BlueCollar-Systems/BlueCollar-Website"))
    parser.add_argument("--deployed-sha", help="the live commit, instead of reading it from the run history")
    args = parser.parse_args(argv)

    repo_root = Path(".").resolve()
    head = _git(repo_root, "rev-parse", "HEAD")
    if head.returncode != 0:
        print(f"::error::Release deploy refused, nothing was deployed: not a git checkout: {head.stderr.strip()}")
        return 1
    head_sha = head.stdout.strip()

    try:
        if args.deployed_sha:
            deployed_sha, source = args.deployed_sha, "given on the command line"
        else:
            token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
            deployed_sha, run_id = find_deployed_commit(
                args.repo, lambda url: _api_get(url, token),
                current_run_id=os.getenv("GITHUB_RUN_ID"),
            )
            source = f"deployed by run {run_id}"
        print(f"Live commit: {deployed_sha} ({source}); about to deploy: {head_sha}")
        with tempfile.TemporaryDirectory(prefix="metadata-only-deploy-") as temp:
            problems = check(repo_root, args.site.resolve(), args.metadata.resolve(),
                             deployed_sha, head_sha, Path(temp))
    except ToolsUnsupported as exc:
        print(f"::error::Release deploy refused, nothing was deployed: {exc} "
              f"The live site cannot be checked this way, so a manual deploy is needed. {MANUAL_DEPLOY_HINT}")
        return 1
    except (GuardError, urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"::error::Release deploy refused, nothing was deployed: {exc} {MANUAL_DEPLOY_HINT}")
        return 1

    if problems:
        print("::error::Release deploy refused, nothing was deployed: main has website changes "
              f"that are not live yet (live commit {deployed_sha[:12]}). A release deploy may only "
              "refresh download metadata. Run website-ci manually on main with "
              "deploy_production=true once these changes are approved; it publishes them and the "
              "new downloads together.")
        for line in problems:
            print(f"  {line}")
        return 1
    print("Only repo-metadata.json and the version badges stamped from it differ from production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
