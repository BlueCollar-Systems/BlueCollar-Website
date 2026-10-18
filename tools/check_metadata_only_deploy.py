#!/usr/bin/env python3
"""Refuse a release deploy that would publish more than new download metadata.

An importer's product-release dispatch deploys the site by itself, so the
version badges and Download buttons follow each release without a separate
GO (owner decision O13, deploy-only). Every other website change still goes
live only through a manual website-ci run with deploy_production=true. This
guard keeps the automatic deploy to that job:

1. Find the commit that is live now: the head commit of the newest website-ci
   run whose "Deploy to Cloudflare Pages" step succeeded (GitHub API).
2. Check that commit out in a temporary worktree, give it the same freshly
   synced repo-metadata.json, stamp its version badges and build its public
   folder with tools/build_site.py.
3. Require that folder to be byte-for-byte identical to the _site folder
   about to be deployed.

So only repo-metadata.json and the badges stamped from it can differ from
production. If main holds any other public change that was never deployed,
the deploy stops before upload and names the files; the manual deploy
publishes them (and the new downloads) once they are approved.

Read-only for the site: it never deploys or pushes. Usage, from the
repository root after tools/sync_repo_metadata.py and tools/build_site.py:
    python tools/check_metadata_only_deploy.py [--site _site] [--deployed-sha SHA]
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_site  # noqa: E402  (the same public-file allowlist the deploy uses)
import sync_repo_metadata as sync  # noqa: E402  (the same badge stamping)

WORKFLOW_FILE = "website-ci.yml"
DEPLOY_JOB = "deploy-pages"
DEPLOY_STEP = "Deploy to Cloudflare Pages"
PRODUCTION_BRANCH = "main"
# Runs are read newest first; a deploy older than this many runs is not
# looked for, and the guard refuses rather than guessing.
MAX_RUNS_CHECKED = 60


class GuardError(RuntimeError):
    """The live commit could not be found or rebuilt; nothing may deploy."""


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


def find_deployed_commit(
    repo: str,
    api_get: Callable[[str], Any],
    *,
    current_run_id: str | None = None,
) -> tuple[str, int]:
    """(head commit, run id) of the newest run that uploaded the site."""
    base = f"https://api.github.com/repos/{repo}/actions"
    runs: list[dict[str, Any]] = []
    for event in ("workflow_dispatch", "repository_dispatch"):
        data = api_get(
            f"{base}/workflows/{WORKFLOW_FILE}/runs?event={event}&status=completed&per_page=50"
        )
        runs.extend((data or {}).get("workflow_runs") or [])
    runs.sort(key=lambda run: run.get("run_started_at") or run.get("created_at") or "", reverse=True)

    for run in runs[:MAX_RUNS_CHECKED]:
        run_id = run.get("id")
        if current_run_id and str(run_id) == str(current_run_id):
            continue
        if run.get("head_branch") != PRODUCTION_BRANCH or not run.get("head_sha"):
            continue
        jobs = (api_get(f"{base}/runs/{run_id}/jobs?filter=all&per_page=100") or {}).get("jobs") or []
        for job in jobs:
            if job.get("name") != DEPLOY_JOB:
                continue
            for step in job.get("steps") or []:
                if step.get("name") == DEPLOY_STEP and step.get("conclusion") == "success":
                    return str(run["head_sha"]), int(run_id)
    raise GuardError(
        f"No earlier {WORKFLOW_FILE} run on {PRODUCTION_BRANCH} with a successful "
        f"'{DEPLOY_STEP}' step was found, so the live commit is unknown."
    )


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False, capture_output=True, text=True,
    )


def _require_commit(repo_root: Path, sha: str) -> None:
    if _git(repo_root, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0:
        return
    fetched = _git(repo_root, "fetch", "--no-tags", "--depth=1", "origin", sha)
    if fetched.returncode != 0 or _git(repo_root, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        raise GuardError(f"Could not fetch the live commit {sha}: {fetched.stderr.strip()}")


def build_reference_site(
    repo_root: Path, sha: str, metadata: Path, workdir: Path
) -> Path:
    """The public folder production would get from `sha` with this metadata."""
    _require_commit(repo_root, sha)
    source = workdir / "live-source"
    out = workdir / "live-site"
    added = _git(repo_root, "worktree", "add", "--detach", str(source), sha)
    if added.returncode != 0:
        raise GuardError(f"Could not check out the live commit {sha}: {added.stderr.strip()}")
    try:
        shutil.copyfile(metadata, source / "repo-metadata.json")
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        sync.stamp_html_versions(payload, source)
        try:
            build_site.build_site(source, out)
        except build_site.BuildError as exc:
            raise GuardError(f"The live commit {sha} does not build with today's file list: {exc}") from exc
    finally:
        _git(repo_root, "worktree", "remove", "--force", str(source))
        shutil.rmtree(source, ignore_errors=True)
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
    if deployed_sha == head_sha:
        print(f"main is the commit already live ({head_sha[:12]}); only metadata can change.")
        return []
    reference = build_reference_site(repo_root, deployed_sha, metadata, workdir)
    return compare_sites(site, reference)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", type=Path, default=Path(build_site.DEFAULT_OUT),
                        help="the built folder about to be deployed (default: _site)")
    parser.add_argument("--metadata", type=Path, default=Path("repo-metadata.json"),
                        help="the freshly synced metadata about to be deployed")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "BlueCollar-Systems/BlueCollar-Website"))
    parser.add_argument("--deployed-sha", help="the live commit, instead of reading it from the run history")
    args = parser.parse_args(argv)

    repo_root = Path(".").resolve()
    head = _git(repo_root, "rev-parse", "HEAD")
    if head.returncode != 0:
        print(f"::error::Not a git checkout: {head.stderr.strip()}")
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
    except (GuardError, urllib.error.URLError, OSError, ValueError) as exc:
        print(f"::error::Release deploy refused, nothing was deployed: {exc} "
              "Run website-ci manually on main with deploy_production=true when the site is ready.")
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
