#!/usr/bin/env python3
"""Refuse a release deploy that would publish more than new download metadata.

An importer's product-release dispatch deploys the site by itself, so the
version badges and Download buttons follow each release without a separate
GO (owner decision O13, deploy-only). Every other website change still goes
live only through a manual website-ci run with deploy_production=true. This
guard keeps the automatic deploy to that job:

1. Find the approved commit: the head commit of the newest MANUAL website-ci
   run (workflow_dispatch on main, so deploy_production=true) whose "Deploy to
   Cloudflare Pages" step succeeded (GitHub Actions API, read back through the
   newest 1,000 manual runs). Release deploys never become this baseline. A
   release deploy uploads a commit that was only proven to build the same as
   the approved commit for that day's metadata; if its tools behave
   differently for some later metadata, that difference was never approved.
   So every release deploy is compared with the last manually deployed commit,
   and what it uploads is always what that commit builds with the new
   metadata.
2. Build two public folders the same clean way, each in its own new temporary
   git worktree and its own new output folder: one from the commit about to
   be deployed, one from the approved commit. Each worktree gets the same freshly
   synced repo-metadata.json, and each commit's OWN tools do the work, run as
   a subprocess with that worktree as the working folder and only that
   worktree's tools importable (python -B -E -s):
     - tools/sync_repo_metadata.py stamp_html_versions(payload) stamps the
       version badges in the worktree's *.html pages;
     - python tools/build_site.py --source . --out <folder> builds the folder.
   So a change on main to the public file list or to the badge stamping
   builds differently from the approved commit, and counts as a website change.
3. Require the _site folder about to be uploaded to be byte-for-byte the clean
   build of its own commit (no leftover or uncommitted file rides along), and
   that clean build to be byte-for-byte the approved commit's build.

The folder is the whole upload: website-ci runs Wrangler from a new empty
folder outside the checkout and hands it the absolute path of _site, so no
repository file outside _site reaches Cloudflare. (Run from the repository
root, Wrangler 4.83.0 would also build and upload Pages Functions from
./functions, read a wrangler.toml/json/jsonc found in that folder or any
parent, and load .env and .env.local; none of those are compared here.)
Wrangler follows links when it walks that folder, so a link, junction or any
entry that is not a plain file or folder, in _site or in either clean build,
is refused rather than compared.

The guard runs from tools/ of the checkout it judges. website-ci starts it
with python -I, so that folder is not on sys.path; when started without -I it
drops every sys.path entry inside the repository before its first import and
refuses to run if any loaded module comes from the repository. A
tools/json.py or tools/filecmp.py on main therefore cannot stand in for the
standard library inside the guard.

So only repo-metadata.json and the badges stamped from it can differ from
production. If main holds any other public change that was never deployed,
the deploy stops before upload and names the files; the manual deploy
publishes them (and the new downloads) once they are approved. When the
approved commit cannot be found, fetched or rebuilt with its own tools (for example a
commit older than tools/build_site.py), the guard refuses too: it never
guesses, and the manual deploy is the way forward.

Read-only for the site: it never deploys or pushes. Usage, from the
repository root after tools/sync_repo_metadata.py and tools/build_site.py:
    python -I tools/check_metadata_only_deploy.py [--site _site] [--deployed-sha SHA]

Exit codes: 0 only metadata differs from production, 1 refused (nothing may
deploy).
"""

# No "from __future__ import": it imports a module through sys.path before
# anything below could run.
import os
import sys


def _inside(path: str, folder: str) -> bool:
    """True when path (any form) resolves to folder or something in it."""
    try:
        path, folder = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(folder))
    except (OSError, ValueError):
        return True  # cannot tell: treat it as the repository's
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


# The repository this copy of the guard belongs to (tools/..).
_REPOSITORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

if __name__ == "__main__":
    # Python puts the script's own folder, tools/, first on sys.path (and
    # PYTHONPATH may add more), so a tools/<standard module>.py would be
    # imported in place of the real one. Drop every entry inside the
    # repository (a relative entry counts from the working folder, as for
    # imports) before the imports below. sys is built in and os is frozen
    # into the interpreter (or already loaded), so neither is read from
    # sys.path; _repository_modules() confirms that before the guard runs.
    sys.path[:] = [entry for entry in sys.path
                   if isinstance(entry, str) and not _inside(entry or os.curdir, _REPOSITORY)]

import argparse
import filecmp
import json
import re
import shutil
import stat
import subprocess
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

# Only manual runs can set the approved baseline. A repository_dispatch run
# (a release deploy among them) is never read, so dispatch traffic cannot push
# the last manual deploy out of the listing either.
BASELINE_EVENT = "workflow_dispatch"
# The run history is read newest first, 100 runs a page. The Actions API lists
# at most 1,000 runs for one event filter, so ten pages is all there is.
RUNS_PER_PAGE = 100
MAX_RUN_PAGES = 10
# Jobs are read only for manual runs on main; past this many the guard stops
# looking and refuses rather than guessing.
MAX_JOB_LOOKUPS = 100

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


def _repository_modules(repository: str = _REPOSITORY, modules: dict | None = None) -> list[str]:
    """Loaded modules (other than the guard itself) whose code is inside the repository."""
    found = []
    for name, module in list((sys.modules if modules is None else modules).items()):
        if name == "__main__" or module is None:
            continue
        spec = getattr(module, "__spec__", None)
        places = [getattr(module, "__file__", None)]
        if getattr(spec, "has_location", False):  # not "built-in" or "frozen"
            places.append(getattr(spec, "origin", None))
        try:
            places += list(getattr(module, "__path__", None) or [])
        except TypeError:
            pass
        for place in places:
            if isinstance(place, str) and place and _inside(place, repository):
                found.append(f"{name} ({place})")
                break
    return sorted(found)


def _refuse_repository_modules() -> bool:
    """Print the refusal and return True when repository code was imported."""
    loaded = _repository_modules()
    if not loaded:
        return False
    print("::error::Release deploy refused, nothing was deployed: the guard imported code from the "
          "repository it is checking instead of the standard library, so its result cannot be trusted: "
          + "; ".join(loaded) + f". Run it as python -I tools/check_metadata_only_deploy.py. {MANUAL_DEPLOY_HINT}")
    return True


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
        if not isinstance(data, dict) or not isinstance(data.get("workflow_runs") or [], list):
            raise GuardError(f"The Actions API returned an unexpected run listing ({type(data).__name__}).")
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
    """A manual run on main: the only kind whose upload sets the baseline."""
    if current_run_id and str(run.get("id")) == str(current_run_id):
        return False
    if run.get("event") != BASELINE_EVENT:
        return False
    if run.get("head_branch") != PRODUCTION_BRANCH or not run.get("head_sha"):
        return False
    return True


def _uploaded(jobs: Any) -> bool:
    jobs = {} if jobs is None else jobs
    if not isinstance(jobs, dict) or not isinstance(jobs.get("jobs") or [], list):
        raise GuardError(f"The Actions API returned an unexpected jobs listing ({type(jobs).__name__}).")
    for job in jobs.get("jobs") or []:
        if not isinstance(job, dict) or job.get("name") != DEPLOY_JOB:
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict) and step.get("name") == DEPLOY_STEP and step.get("conclusion") == "success":
                return True
    return False


def find_deployed_commit(
    repo: str,
    api_get: Callable[[str], Any],
    *,
    current_run_id: str | None = None,
) -> tuple[str, int]:
    """(head commit, run id) of the newest manual run that uploaded the site.

    Release deploys (repository_dispatch runs) are never read: they are not an
    approval, so they never become the commit a release deploy is held to.
    """
    runs, total, more = _completed_runs(repo, BASELINE_EVENT, api_get)
    candidates = [run for run in runs if _could_have_deployed(run, current_run_id)]
    candidates.sort(key=lambda run: run.get("run_started_at") or run.get("created_at") or "", reverse=True)

    for run in candidates[:MAX_JOB_LOOKUPS]:
        if _uploaded(api_get(jobs_url(repo, run.get("id")))):
            return str(run["head_sha"]), int(run["id"])

    read = (
        f"the newest {len(runs)} of {total} {BASELINE_EVENT} runs (the Actions API lists no more)"
        if more else f"all {len(runs)} completed {BASELINE_EVENT} runs"
    )
    checked = min(len(candidates), MAX_JOB_LOOKUPS)
    why = (
        f"It read {read} of {WORKFLOW_FILE}. {len(candidates)} of them ran on {PRODUCTION_BRANCH}; "
        f"the jobs of {'all of them' if checked == len(candidates) else f'the newest {checked}'} were "
        f"read and none has a successful '{DEPLOY_STEP}' step, so none was a manual "
        "deploy_production=true deploy. Release deploys do not count: they are not an approval."
    )
    if checked < len(candidates):
        why += f" The guard reads at most {MAX_JOB_LOOKUPS} runs' jobs, so the last manual deploy is older than that."
    elif more:
        why += " The last manual deploy is older than the run history the Actions API lists."
    raise GuardError(f"The approved live commit is unknown, so the guard cannot compare against it. {why}")


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


_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _odd_kind(info: os.stat_result) -> str | None:
    """None for a plain file or folder; otherwise what the entry is."""
    if stat.S_ISLNK(info.st_mode):
        return "symbolic link"
    if getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
        return "junction or other reparse point"
    if stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode):
        return None
    return "special file"


def _files(root: Path) -> set[str]:
    """The plain files under root, as POSIX paths relative to it.

    Wrangler follows links when it walks the upload folder, so a link would
    upload whatever it points at, while a comparison that does not follow it
    sees nothing there. Any link, junction, reparse point or other entry that
    is not a plain file or folder, anywhere in the folder or as the folder
    itself, is refused instead. Nothing is followed while looking.
    """
    root = Path(root)
    try:
        top = os.lstat(root)
    except OSError as exc:
        raise GuardError(f"Cannot read the folder {root}: {exc}") from exc
    kind = _odd_kind(top)
    if kind or not stat.S_ISDIR(top.st_mode):
        raise GuardError(f"{root} is a {kind or 'file'}, not a plain folder, so it cannot be compared.")

    def unreadable(exc: OSError) -> None:
        raise GuardError(f"Cannot read {exc.filename} in {root}: {exc}")

    files: set[str] = set()
    odd: list[str] = []
    for current, folders, names in os.walk(root, onerror=unreadable, followlinks=False):
        plain_folders = []
        for name in folders + names:
            path = os.path.join(current, name)
            rel = Path(path).relative_to(root).as_posix()
            try:
                info = os.lstat(path)
            except OSError as exc:
                raise GuardError(f"Cannot read {rel} in {root}: {exc}") from exc
            kind = _odd_kind(info)
            if kind:
                odd.append(f"{rel} ({kind})")
            elif stat.S_ISDIR(info.st_mode):
                plain_folders.append(name)
            else:
                files.add(rel)
        folders[:] = [name for name in folders if name in plain_folders]
    if odd:
        raise GuardError(
            f"{root} holds entries that are not plain files or folders. Wrangler would follow or upload "
            "them, but the guard cannot compare what they point at, so nothing may deploy: "
            + ", ".join(sorted(odd))
        )
    return files


def compare_sites(new_site: Path, live_site: Path) -> list[str]:
    """One line per public file that differs between two built folders.

    Both folders must hold nothing but plain files and folders (see _files).
    """
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
        print(f"The commit about to be deployed is the approved live commit ({head_sha[:12]}); only metadata can change.")
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
    parser.add_argument("--deployed-sha", help="the approved commit, instead of reading the last manual deploy from the run history")
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
            source = f"the last manual deploy, run {run_id}"
        print(f"Approved live commit: {deployed_sha} ({source}); about to deploy: {head_sha}")
        with tempfile.TemporaryDirectory(prefix="metadata-only-deploy-") as temp:
            # absolute(), not resolve(): a _site that is itself a link is refused, not followed.
            problems = check(repo_root, args.site.absolute(), args.metadata.resolve(),
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
              f"that were never approved by a manual deploy (approved live commit {deployed_sha[:12]}). "
              "A release deploy may only "
              "refresh download metadata. Run website-ci manually on main with "
              "deploy_production=true once these changes are approved; it publishes them and the "
              "new downloads together.")
        for line in problems:
            print(f"  {line}")
        return 1
    print("Only repo-metadata.json and the version badges stamped from it differ from production.")
    return 0


if __name__ == "__main__":
    # Checked before the guard starts and again before a pass is reported,
    # in case a later import was served from the repository.
    if _refuse_repository_modules():
        raise SystemExit(1)
    status = main()
    if _refuse_repository_modules():
        status = 1
    raise SystemExit(status)
