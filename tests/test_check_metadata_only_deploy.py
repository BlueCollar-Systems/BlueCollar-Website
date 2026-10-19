"""Regression tests for tools/check_metadata_only_deploy.py.

The end-to-end cases build real public folders from a throwaway git
repository that holds a copy of this site's public files and of its two
build tools (tools/build_site.py, tools/sync_repo_metadata.py), so they
exercise the same worktree checkouts, per-commit badge stamping and per-commit
tools/build_site.py runs the release deploy uses. Nothing is fetched from the
network.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import py_compile
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GUARD = _load("check_metadata_only_deploy")
BUILD = _load("build_site")

REPO = "BlueCollar-Systems/BlueCollar-Website"
API = f"https://api.github.com/repos/{REPO}/actions"
BLENDER = "BlueCollar-Systems/PDF-Importer-Blender"

# A temporary folder on a drive that records no file owner (FAT, exFAT) makes
# git refuse the throwaway repositories as "dubious ownership". Trust them for
# this test process only (environment config, nothing is written anywhere).
_count = int(os.environ.get("GIT_CONFIG_COUNT", "0") or 0)
os.environ[f"GIT_CONFIG_KEY_{_count}"] = "safe.directory"
os.environ[f"GIT_CONFIG_VALUE_{_count}"] = "*"
os.environ["GIT_CONFIG_COUNT"] = str(_count + 1)


# ---------------------------------------------------------------------------
# Which commit is live
# ---------------------------------------------------------------------------

def _run(run_id: int, sha: str, started: str, *, branch: str = "main", title: str | None = None) -> dict:
    run = {"id": run_id, "head_sha": sha, "head_branch": branch, "run_started_at": started}
    if title is not None:
        run["display_title"] = title
    return run


def _jobs(deploy_step: str | None) -> dict:
    """Jobs of one run; deploy_step is the Cloudflare step's conclusion."""
    jobs = [{"name": "static-checks", "steps": [{"name": "Checkout", "conclusion": "success"}]}]
    if deploy_step is not None:
        jobs.append({"name": "deploy-pages", "steps": [
            {"name": "Build site folder", "conclusion": "success"},
            {"name": GUARD.DEPLOY_STEP, "conclusion": deploy_step},
        ]})
    return {"jobs": jobs}


class FakeActions:
    """The Actions API: paged run listings per event, and jobs per run."""

    def __init__(self, manual: list[dict], dispatched: list[dict], jobs: dict[int, dict]) -> None:
        self.runs = {"workflow_dispatch": manual, "repository_dispatch": dispatched}
        self.jobs = jobs
        self.calls: list[str] = []

    def job_calls(self) -> list[int]:
        return [int(url.split("/runs/", 1)[1].split("/", 1)[0]) for url in self.calls if "/jobs?" in url]

    def __call__(self, url: str):
        self.calls.append(url)
        parts = urlsplit(url)
        query = {key: values[0] for key, values in parse_qs(parts.query).items()}
        if parts.path == f"/repos/{REPO}/actions/workflows/website-ci.yml/runs":
            assert query["status"] == "completed", url
            per_page, page = int(query["per_page"]), int(query["page"])
            runs = self.runs[query["event"]]
            return {"total_count": len(runs), "workflow_runs": runs[(page - 1) * per_page: page * per_page]}
        match = re.fullmatch(rf"/repos/{REPO}/actions/runs/(\d+)/jobs", parts.path)
        if match and int(match.group(1)) in self.jobs:
            return self.jobs[int(match.group(1))]
        raise AssertionError(f"unexpected API call {url}")


def _stamp(day: int, minute: int) -> str:
    return f"2026-10-{day:02d}T{minute // 60:02d}:{minute % 60:02d}:00Z"


class FindDeployedCommitTests(unittest.TestCase):
    def find(self, api: FakeActions, current: str | None = None):
        return GUARD.find_deployed_commit(REPO, api, current_run_id=current)

    def assertNoDispatchRunsRead(self, api: FakeActions) -> None:
        self.assertFalse([url for url in api.calls if "event=repository_dispatch" in url])

    def test_newest_manual_upload_wins_and_release_deploys_never_count(self) -> None:
        # The review's probe: a newer product-release run (head b...) that
        # uploaded must not beat the older manual deploy (head a...). A
        # release deploy is not an approval, so it never becomes the baseline.
        api = FakeActions(
            manual=[
                _run(30, "c" * 40, "2026-10-18T18:00:00Z"),  # validation only
                _run(10, "a" * 40, "2026-10-12T12:00:00Z"),  # the manual deploy
                _run(5, "0" * 40, "2026-10-01T12:00:00Z"),   # an older manual deploy
            ],
            dispatched=[_run(20, "b" * 40, "2026-10-18T17:00:00Z", title="product-release")],
            jobs={30: _jobs(None), 20: _jobs("success"), 10: _jobs("success"), 5: _jobs("success")},
        )
        self.assertEqual(self.find(api), ("a" * 40, 10))
        self.assertEqual(api.job_calls(), [30, 10])
        self.assertNoDispatchRunsRead(api)

    def test_a_run_that_failed_after_uploading_still_counts(self) -> None:
        # The Cloudflare step succeeded, a later verification failed: the
        # upload is what visitors get, so that commit is the live one.
        api = FakeActions(
            manual=[_run(40, "d" * 40, "2026-10-18T18:00:00Z"), _run(10, "a" * 40, "2026-10-12T12:00:00Z")],
            dispatched=[],
            jobs={40: _jobs("success"), 10: _jobs("success")},
        )
        self.assertEqual(self.find(api)[0], "d" * 40)

    def test_failed_upload_other_branch_and_current_run_are_skipped(self) -> None:
        api = FakeActions(
            manual=[
                _run(60, "9" * 40, "2026-10-18T20:00:00Z"),
                _run(50, "e" * 40, "2026-10-18T19:00:00Z"),
                _run(45, "f" * 40, "2026-10-18T18:30:00Z", branch="claude/x"),
                _run(10, "a" * 40, "2026-10-12T12:00:00Z"),
            ],
            dispatched=[],
            jobs={60: _jobs("success"), 50: _jobs("failure"), 45: _jobs("success"), 10: _jobs("success")},
        )
        self.assertEqual(self.find(api, current="60"), ("a" * 40, 10))
        self.assertNotIn(45, api.job_calls())
        self.assertNotIn(60, api.job_calls())

    def test_a_listed_run_from_another_event_is_skipped(self) -> None:
        # Belt and braces: even if the listing returned a dispatch run, its
        # upload would not set the baseline.
        stray = _run(70, "b" * 40, "2026-10-18T20:00:00Z", title="product-release")
        stray["event"] = "repository_dispatch"
        api = FakeActions(
            manual=[stray, _run(10, "a" * 40, "2026-10-12T12:00:00Z")],
            dispatched=[],
            jobs={70: _jobs("success"), 10: _jobs("success")},
        )
        self.assertEqual(self.find(api), ("a" * 40, 10))
        self.assertEqual(api.job_calls(), [10])

    def test_months_of_dispatch_traffic_cannot_hide_the_manual_deploy(self) -> None:
        # Dispatch runs are never listed, so no amount of them (about three a
        # day filled the old 60-run window in under three weeks) pushes the
        # last manual deploy out of reach: one page, one job lookup.
        dispatched = [
            _run(10_000 - n, "7" * 40, _stamp(18 - n // 300, 1439 - n % 300), title="product-update")
            for n in range(2_000)
        ]
        api = FakeActions(
            manual=[_run(10, "a" * 40, "2026-07-01T12:00:00Z")],
            dispatched=dispatched,
            jobs={10: _jobs("success")},
        )
        self.assertEqual(self.find(api), ("a" * 40, 10))
        self.assertEqual(api.job_calls(), [10])
        self.assertEqual(len([url for url in api.calls if "/runs?" in url]), 1)
        self.assertNoDispatchRunsRead(api)

    def test_pages_back_through_the_manual_run_history(self) -> None:
        # Manual runs on other branches cost no job lookup; the listing is
        # paged until the deploy on main turns up.
        manual = [_run(9_000 - n, "c" * 40, _stamp(18, 1000 - n), branch="claude/x") for n in range(250)]
        manual.append(_run(10, "a" * 40, "2026-07-01T12:00:00Z"))
        api = FakeActions(manual=manual, dispatched=[], jobs={10: _jobs("success")})
        self.assertEqual(self.find(api), ("a" * 40, 10))
        self.assertEqual(len([url for url in api.calls if "event=workflow_dispatch" in url]), 3)
        self.assertEqual(api.job_calls(), [10])

    def test_no_deploy_found_says_exactly_why(self) -> None:
        api = FakeActions(
            manual=[_run(30, "c" * 40, "2026-10-18T18:00:00Z")],
            dispatched=[_run(31, "d" * 40, "2026-10-18T17:00:00Z", title="product-release")],
            jobs={30: _jobs("skipped"), 31: _jobs("success")},
        )
        with self.assertRaises(GUARD.GuardError) as caught:
            self.find(api)
        message = str(caught.exception)
        self.assertIn("The approved live commit is unknown", message)
        self.assertIn("It read all 1 completed workflow_dispatch runs of website-ci.yml", message)
        self.assertIn("1 of them ran on main", message)
        self.assertIn(f"none has a successful '{GUARD.DEPLOY_STEP}' step", message)
        self.assertIn("so none was a manual deploy_production=true deploy", message)
        self.assertIn("Release deploys do not count", message)
        self.assertNoDispatchRunsRead(api)

    def test_history_beyond_the_api_limit_is_named_in_the_refusal(self) -> None:
        full = GUARD.RUNS_PER_PAGE * GUARD.MAX_RUN_PAGES
        manual = [_run(50_000 - n, "7" * 40, _stamp(18, 0), branch="claude/x") for n in range(full + 5)]
        api = FakeActions(manual=manual, dispatched=[], jobs={})
        with self.assertRaises(GUARD.GuardError) as caught:
            self.find(api)
        message = str(caught.exception)
        self.assertIn(f"the newest {full} of {full + 5} workflow_dispatch runs (the Actions API lists no more)", message)
        self.assertIn("older than the run history the Actions API lists", message)
        self.assertEqual(len([url for url in api.calls if "event=workflow_dispatch" in url]), GUARD.MAX_RUN_PAGES)

    def test_an_unexpected_api_payload_is_a_guard_refusal(self) -> None:
        # A list where an object belongs used to end in an AttributeError
        # traceback; it is now the guard's own refusal, with a reason.
        api = FakeActions(manual=[_run(10, "a" * 40, "2026-10-12T12:00:00Z")], dispatched=[], jobs={10: []})
        with self.assertRaises(GUARD.GuardError) as caught:
            self.find(api)
        self.assertIn("unexpected jobs listing (list)", str(caught.exception))
        with self.assertRaises(GUARD.GuardError) as caught:
            GUARD.find_deployed_commit(REPO, lambda url: [{"id": 1}])
        self.assertIn("unexpected run listing (list)", str(caught.exception))

    def test_job_lookups_are_bounded_and_the_bound_is_named(self) -> None:
        manual = [_run(1000 + n, "c" * 40, _stamp(18, 1000 - n)) for n in range(GUARD.MAX_JOB_LOOKUPS + 3)]
        api = FakeActions(manual=manual, dispatched=[], jobs={run["id"]: _jobs("skipped") for run in manual})
        with self.assertRaises(GUARD.GuardError) as caught:
            self.find(api)
        self.assertEqual(len(api.job_calls()), GUARD.MAX_JOB_LOOKUPS)
        self.assertIn(f"reads at most {GUARD.MAX_JOB_LOOKUPS} runs' jobs", str(caught.exception))


# ---------------------------------------------------------------------------
# Clean builds of two commits, each with its own tools
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Guard Test", "-c", "user.email=guard@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _remove_tree(path: Path) -> None:
    """Delete a test folder, including git's read-only object files on Windows."""
    def clear_and_retry(func, name, _exc) -> None:
        try:
            os.chmod(name, stat.S_IWRITE)
            func(name)
        except OSError:
            pass
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=clear_and_retry)
    else:
        shutil.rmtree(path, onerror=clear_and_retry)


def _copy_public_files(destination: Path, *, with_tools: bool = True) -> None:
    """The site's public files and build tools, plus a README that is not published."""
    for pattern in BUILD.ALLOWED_GLOBS:
        for path in ROOT.glob(pattern):
            shutil.copyfile(path, destination / path.name)
    for name in BUILD.ALLOWED_FILES:
        shutil.copyfile(ROOT / name, destination / name)
    for name in BUILD.ALLOWED_DIRS:
        shutil.copytree(ROOT / name, destination / name, ignore=shutil.ignore_patterns("__pycache__"))
    if with_tools:
        (destination / "tools").mkdir(exist_ok=True)
        for tool in (GUARD.BUILD_TOOL, GUARD.STAMP_TOOL):
            shutil.copyfile(ROOT / tool, destination / tool)
    (destination / "README.md").write_text("repository notes\n", encoding="utf-8", newline="\n")
    (destination / ".gitignore").write_text("_site/\n__pycache__/\n", encoding="utf-8", newline="\n")


def _fresh_metadata(source: Path, tag: str) -> dict:
    """The live metadata with a new Blender release, as a release sync makes it."""
    payload = json.loads((source / "repo-metadata.json").read_text(encoding="utf-8"))
    release = payload["repos"][BLENDER]["latest_release"]
    old = release["tag"]
    release["tag"] = tag
    release["url"] = release["url"].replace(old, tag)
    for asset in release["assets"]:
        asset["name"] = asset["name"].replace(old, tag)
        asset["url"] = asset["url"].replace(old, tag)
        asset["digest"] = "sha256:" + "e" * 64
    return payload


def _marker_module(marker: Path) -> str:
    """A module that records its import in `marker` and then fails.

    The path is written into the source: the guard gives a commit's tools
    none of the test's environment variables.
    """
    return (
        f"with open({str(marker)!r}, 'a', encoding='utf-8') as _f:\n"
        "    _f.write(__name__ + '\\n')\n"
        "raise ImportError('shadow module ' + __name__ + ' was imported')\n"
    )


def _commit_cache(repo: Path, source: str) -> Path:
    """Commit tools/__pycache__/sync_repo_metadata.<tag>.pyc compiled from `source`.

    An unchecked-hash .pyc: Python uses it without looking at the .py beside
    it, and -B (which only stops caches being written) does not stop that.
    """
    cache = Path(importlib.util.cache_from_source(str(repo / "tools" / "sync_repo_metadata.py")))
    cache.parent.mkdir(exist_ok=True)
    staged = repo.parent / "cached_sync_repo_metadata.py"
    staged.write_text(source, encoding="utf-8", newline="\n")
    py_compile.compile(str(staged), cfile=str(cache), doraise=True,
                       invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
    _git(repo, "add", "-f", str(cache.relative_to(repo)))
    return cache


def _edit(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) >= count, (path, old)
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


class GuardEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(_remove_tree, self.temp)
        self.repo = self.temp / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "core.autocrlf", "false")
        _copy_public_files(self.repo)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "live site")
        self.live_sha = _git(self.repo, "rev-parse", "HEAD")
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)
        self.runs = 0

    def commit(self, message: str) -> str:
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "--allow-empty", "-m", message)
        return _git(self.repo, "rev-parse", "HEAD")

    def tool(self, *args: str) -> None:
        """Run one of the checkout's own tools the way the deploy job does."""
        result = GUARD._run_tool(self.repo, list(args))
        self.assertEqual(result.returncode, 0, result.stderr)

    def deploy_job(self, tag: str = "v9.9.9") -> tuple[Path, Path]:
        """The deploy job's steps before the guard: sync, stamp, build _site.

        main's own tools stamp and build, as in website-ci: a change to them
        shapes the folder that would be uploaded.
        """
        self.runs += 1
        metadata = self.repo / "repo-metadata.json"
        payload = _fresh_metadata(self.repo, tag)
        metadata.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        self.tool("-c", GUARD.STAMP_DRIVER)
        site = self.temp / f"site-{self.runs}"
        self.tool(GUARD.BUILD_TOOL, "--source", ".", "--out", str(site))
        return site, metadata

    def guard(self, site: Path, metadata: Path, live_sha: str | None = None) -> list[str]:
        work = self.temp / f"work-{self.runs}"
        work.mkdir()
        head = _git(self.repo, "rev-parse", "HEAD")
        return GUARD.check(self.repo, site, metadata, live_sha or self.live_sha, head, work)

    def release_deploy(self, tag: str = "v9.9.9", live_sha: str | None = None) -> list[str]:
        return self.guard(*self.deploy_job(tag), live_sha=live_sha)

    def assertNoWorktreesLeft(self) -> None:
        self.assertEqual(len(_git(self.repo, "worktree", "list").splitlines()), 1)

    # -- (c) pure metadata changes pass ------------------------------------

    def test_new_release_metadata_alone_passes(self) -> None:
        self.commit("tests only")  # a commit that changes nothing public
        self.assertEqual(self.release_deploy(), [])
        index = (self.temp / "site-1" / "index.html").read_text(encoding="utf-8")
        self.assertIn("v9.9.9", index)  # the badge really was stamped
        live_index = (self.temp / "work-1" / "live-site" / "index.html").read_text(encoding="utf-8")
        self.assertIn("v9.9.9", live_index)  # and the live commit got the same metadata
        self.assertNoWorktreesLeft()

    def test_badge_stamp_commit_after_the_last_deploy_passes(self) -> None:
        payload = _fresh_metadata(self.repo, "v9.9.8")
        (self.repo / "repo-metadata.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.tool("-c", GUARD.STAMP_DRIVER)
        self.commit("chore: stamp release badges from metadata sync [skip release]")
        self.assertEqual(self.release_deploy("v9.9.9"), [])

    def test_repository_only_changes_pass(self) -> None:
        (self.repo / "README.md").write_text("new notes\n", encoding="utf-8", newline="\n")
        (self.repo / "tools" / "helper.py").write_text("print('x')\n", encoding="utf-8", newline="\n")
        self.commit("docs and tools")
        self.assertEqual(self.release_deploy(), [])

    def test_tool_edit_that_builds_the_same_folder_passes(self) -> None:
        _edit(self.repo / GUARD.BUILD_TOOL, "# Add future root public files here.", "# Add future root files here.")
        _edit(self.repo / GUARD.STAMP_TOOL, '"""Write latest release tags', '"""Write the latest release tags')
        self.commit("reword tool comments")
        self.assertEqual(self.release_deploy(), [])

    # -- public changes that were never deployed are refused ---------------

    def test_undeployed_page_copy_change_is_refused(self) -> None:
        _edit(self.repo / "index.html", "</body>", "<p>new copy</p></body>")
        self.commit("copy change merged but not deployed")
        self.assertEqual(self.release_deploy(), ["changed: index.html"])

    def test_new_and_removed_public_files_are_refused(self) -> None:
        # p-records/ keeps a file: git checks out no empty folder, and the
        # build requires every listed folder.
        record = self.repo / "p-records" / "retired-record.json"
        record.write_text("{}\n", encoding="utf-8", newline="\n")
        self.live_sha = self.commit("live site with one more part record")
        (self.repo / "extra.css").write_text("body{}\n", encoding="utf-8", newline="\n")
        record.unlink()
        self.commit("add a stylesheet, drop a record")
        self.assertEqual(
            self.release_deploy(),
            ["new public file: extra.css", "removed public file: p-records/retired-record.json"],
        )

    def test_undeployed_public_file_list_change_is_refused(self) -> None:
        # (a) The review's reproduction: main drops app-ads.txt from the
        # allowlist. main's build leaves it out, the live commit's own build
        # keeps it, so the folders differ.
        _edit(self.repo / GUARD.BUILD_TOOL, '    "app-ads.txt",\n', "")
        self.commit("stop publishing app-ads.txt")
        site, metadata = self.deploy_job()
        self.assertFalse((site / "app-ads.txt").exists())
        self.assertEqual(self.guard(site, metadata), ["removed public file: app-ads.txt"])

    def test_undeployed_badge_stamping_change_is_refused(self) -> None:
        # (b) main changes how badges are stamped; the pages in the commit
        # are untouched. The live commit's own stamping writes the old text.
        _edit(self.repo / GUARD.STAMP_TOOL, 'else tag\n', 'else f"Version {tag}"\n', count=2)
        self.commit("new badge wording")
        # index.html carries the importer badges this wording applies to.
        self.assertEqual(self.release_deploy(), ["changed: index.html"])

    def test_undeployed_builder_transformation_is_refused(self) -> None:
        # Both commits keep identical input pages and public file lists.
        # Only main's builder appends bytes to the built index page.
        anchor = '    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())'
        replacement = (
            '    index = out / "index.html"\n'
            '    index.write_text(index.read_text(encoding="utf-8") + "<!-- builder-only -->", encoding="utf-8")\n'
            + anchor
        )
        _edit(self.repo / GUARD.BUILD_TOOL, anchor, replacement)
        self.commit("builder changes output without changing input pages")
        self.assertEqual(self.release_deploy(), ["changed: index.html"])
        self.assertNoWorktreesLeft()

    def test_undeployed_allowlist_addition_is_refused(self) -> None:
        # The bytes already exist in the live commit but are not published.
        # Only the new commit's public allowlist starts publishing them.
        (self.repo / "extra-public.txt").write_text("not yet published\n", encoding="utf-8")
        self.live_sha = self.commit("live repository holds an unpublished text file")
        _edit(self.repo / GUARD.BUILD_TOOL,
              '    # Add future root public files here.',
              '    "extra-public.txt",\n    # Add future root public files here.')
        self.commit("start publishing the existing text file")
        self.assertEqual(self.release_deploy(), ["new public file: extra-public.txt"])
        self.assertNoWorktreesLeft()

    def test_leftover_or_uncommitted_file_in_the_upload_is_refused(self) -> None:
        (self.repo / "scratch.html").write_text("<!DOCTYPE html><title>x</title>\n", encoding="utf-8", newline="\n")
        site, metadata = self.deploy_job()
        self.assertTrue((site / "scratch.html").exists())
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata)
        self.assertIn("not the clean build of its commit", str(caught.exception))
        self.assertIn("new public file: scratch.html", str(caught.exception))
        self.assertNoWorktreesLeft()

    def test_same_commit_builds_once(self) -> None:
        site, metadata = self.deploy_job()
        self.assertEqual(self.guard(site, metadata, live_sha=_git(self.repo, "rev-parse", "HEAD")), [])
        self.assertTrue((self.temp / "work-1" / "deploy-site").is_dir())
        self.assertFalse((self.temp / "work-1" / "live-site").exists())

    # -- links: Wrangler follows them, a comparison of plain files does not -

    def link(self, target: Path, link: Path) -> None:
        try:
            os.symlink(target, link, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"cannot make symbolic links here: {exc}")

    def require_links(self) -> None:
        probe = self.temp / "link-probe"
        self.link(self.temp / "repo", probe)
        os.rmdir(probe) if os.name == "nt" else probe.unlink()

    def test_folder_link_added_by_the_builder_is_refused(self) -> None:
        # Review finding B2 (A10): main publishes a new page through a folder
        # link that its build_site.py adds to the output. In the guard's
        # clean build the link dangles once the worktree is gone; in _site it
        # resolves, and Wrangler uploads what it points at.
        extra = self.repo / "public-extra"
        extra.mkdir()
        (extra / "promo.html").write_text("<!DOCTYPE html><title>promo</title>\n", encoding="utf-8", newline="\n")
        anchor = '    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())'
        _edit(self.repo / GUARD.BUILD_TOOL, anchor,
              "    import os\n"
              "    os.symlink(os.path.relpath(source / 'public-extra', out), out / 'extra', target_is_directory=True)\n"
              + anchor)
        self.commit("publish public-extra through a link")
        self.require_links()
        site, metadata = self.deploy_job()
        self.assertTrue((site / "extra" / "promo.html").is_file())  # what Wrangler would upload
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata)
        self.assertIn("extra (symbolic link)", str(caught.exception))
        self.assertIn("not plain files or folders", str(caught.exception))
        self.assertNoWorktreesLeft()

    def test_file_and_folder_links_in_the_upload_folder_are_refused(self) -> None:
        site, metadata = self.deploy_job()
        outside = self.temp / "outside"
        (outside / "deep").mkdir(parents=True)
        (outside / "deep" / "page.html").write_text("unapproved\n", encoding="utf-8")
        self.link(outside, site / "linked-folder")
        self.link(self.repo / "README.md", site / "linked-file.txt")
        self.link(self.temp / "missing", site / "dangling")
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata)
        message = str(caught.exception)
        for name in ("linked-folder", "linked-file.txt", "dangling"):
            self.assertIn(f"{name} (symbolic link)", message)
        self.assertNotIn("deep", message)  # nothing behind a link is followed

    def test_upload_folder_that_is_itself_a_link_is_refused(self) -> None:
        site, metadata = self.deploy_job()
        linked = self.temp / "linked-site"
        self.link(site, linked)
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(linked, metadata)
        self.assertIn("is a symbolic link, not a plain folder", str(caught.exception))

    @unittest.skipUnless(os.name == "nt", "junctions are a Windows folder link")
    def test_junction_in_the_upload_folder_is_refused(self) -> None:
        import _winapi
        site, metadata = self.deploy_job()
        outside = self.temp / "outside"
        outside.mkdir()
        (outside / "page.html").write_text("unapproved\n", encoding="utf-8")
        _winapi.CreateJunction(str(outside), str(site / "joined"))
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata)
        self.assertIn("joined (junction or other reparse point)", str(caught.exception))

    def test_link_in_the_approved_commits_build_is_refused(self) -> None:
        # Each built reference folder is walked the same way, not only _site.
        anchor = '    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())'
        self.require_links()
        old = self.old_live_commit(lambda: _edit(
            self.repo / GUARD.BUILD_TOOL, anchor,
            "    import os\n    os.symlink('index.html', out / 'alias.html')\n" + anchor))
        site, metadata = self.deploy_job()
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata, live_sha=old)
        message = str(caught.exception)
        self.assertIn("live-site holds entries that are not plain files or folders", message)
        self.assertIn("alias.html (symbolic link)", message)
        self.assertNoWorktreesLeft()

    # -- the guard's own imports come from the standard library -------------

    SHADOWED = ("argparse", "json", "re", "shutil", "stat", "subprocess", "tempfile",
                "typing", "pathlib", "os", "__future__")

    def plant_shadow_modules(self) -> None:
        """tools/<standard module>.py files that record any import and then fail."""
        body = (
            "import os as _os\n"
            "with open(_os.environ['SHADOW_MARKER'], 'a', encoding='utf-8') as _f:\n"
            "    _f.write(__name__ + '\\n')\n"
            "raise ImportError('shadow module ' + __name__ + ' was imported')\n"
        )
        for name in self.SHADOWED:
            (self.repo / "tools" / f"{name}.py").write_text(body, encoding="utf-8", newline="\n")
        (self.repo / "tools" / "urllib").mkdir()
        (self.repo / "tools" / "urllib" / "__init__.py").write_text(body, encoding="utf-8", newline="\n")

    def test_stdlib_named_modules_in_tools_cannot_replace_the_guards_imports(self) -> None:
        # Review finding B3 (A11): main changes index.html and adds a
        # three-line tools/filecmp.py whose cmp() says every file is equal.
        # Run as `python tools/check_metadata_only_deploy.py`, tools/ is first
        # on sys.path, so the guard compared with it and passed. Committed,
        # that file is now refused by name before anything is compared (last
        # run below); here it is first left uncommitted, so the guard gets as
        # far as comparing and must still not import it.
        shutil.copyfile(ROOT / "tools" / "check_metadata_only_deploy.py",
                        self.repo / "tools" / "check_metadata_only_deploy.py")
        self.live_sha = self.commit("the guard is part of the site's tools")
        _edit(self.repo / "index.html", "</body>", "<p>UNAPPROVED PAGE CHANGE</p></body>")
        self.commit("page change")
        (self.repo / "tools" / "filecmp.py").write_text(
            "import os\n"
            "open(os.environ['SHADOW_MARKER'], 'a', encoding='utf-8').write('filecmp\\n')\n"
            "def cmp(f1, f2, shallow=True):\n    return True\n",
            encoding="utf-8", newline="\n")
        site, metadata = self.deploy_job()
        shutil.move(str(site), str(self.repo / "_site"))
        marker = self.temp / "shadow-imports.txt"

        workflow = (ROOT / ".github" / "workflows" / "website-ci.yml").read_text(encoding="utf-8")
        command = re.search(r"(?m)^        run: (python -I .*tools/check_metadata_only_deploy\.py.*)$", workflow)
        self.assertIsNotNone(command, "website-ci must run the guard with python -I")
        isolated = [sys.executable, *command.group(1).split()[1:]]
        bare = [sys.executable, "tools/check_metadata_only_deploy.py", "--site", "_site",
                "--metadata", "repo-metadata.json"]
        env = {name: value for name, value in os.environ.items() if not name.startswith("PYTHON")}
        env["SHADOW_MARKER"] = str(marker)

        def run(label: str, argv: list[str], expected: str = "changed: index.html") -> None:
            with self.subTest(label):
                result = subprocess.run([*argv, "--deployed-sha", self.live_sha], cwd=str(self.repo), env=env,
                                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                                        timeout=GUARD.TOOL_TIMEOUT)
                output = result.stdout + result.stderr
                self.assertFalse(marker.exists(), marker.read_text(encoding="utf-8") if marker.exists() else "")
                self.assertEqual(result.returncode, 1, output)
                self.assertIn(expected, output)
                self.assertNotIn("Only repo-metadata.json", output)
                self.assertNotIn("Traceback", output)

        # A11 as reproduced: without -I the guard itself drops tools/ from
        # sys.path before its first import (Python adds the script's folder
        # only after its own startup imports).
        run("without -I, tools/filecmp.py", bare)
        # Then every other standard module the guard imports, planted beside
        # it (left uncommitted, so the commits' own tools build as before).
        self.plant_shadow_modules()
        run("as website-ci runs it, all planted", isolated)
        run("without -I, all planted", bare)
        # Committed, as in A11, a standard-module name in tools/ is refused by
        # name before anything is built or compared.
        _git(self.repo, "add", "-f", "tools/filecmp.py")
        _git(self.repo, "commit", "-q", "-m", "a tools/filecmp.py")
        refused = "tools/filecmp.py: a module in tools/ named after the standard module filecmp"
        run("as website-ci runs it, committed", isolated, refused)
        run("without -I, committed", bare, refused)
        self.assertNoWorktreesLeft()

    # -- tracked files Python could run instead of the reviewed source ------

    def test_root_json_and_urllib_package_never_reach_the_stamp_driver(self) -> None:
        # The recheck's route (b): the stamp driver ran as python -B -E -s -c
        # with the worktree as its working folder, so sys.path[0] was that
        # folder and a root json.py or urllib/ package was imported by the
        # driver's own "import json" / "from pathlib import Path". Now the
        # driver runs isolated (the deploy job below stamps with it and must
        # not import them), and the guard refuses such a commit by name
        # before running any of its code.
        marker = self.temp / "root-imports.txt"
        (self.repo / "json.py").write_text(_marker_module(marker), encoding="utf-8", newline="\n")
        (self.repo / "urllib").mkdir()
        (self.repo / "urllib" / "__init__.py").write_text(_marker_module(marker), encoding="utf-8", newline="\n")
        self.commit("root json.py and urllib/ package")
        site, metadata = self.deploy_job()
        self.assertIn("v9.9.9", (site / "index.html").read_text(encoding="utf-8"))  # stamped all the same
        self.assertFalse(marker.exists(), marker.read_text(encoding="utf-8") if marker.exists() else "")
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata)
        message = str(caught.exception)
        self.assertIn("json.py: a module in the repository root named after the standard module json", message)
        self.assertIn("urllib/__init__.py: inside urllib/, a package in the repository root", message)
        self.assertIn("the guard runs none of its tools", message)
        self.assertFalse(marker.exists())
        self.assertFalse((self.temp / "work-1" / "deploy-site").exists())
        self.assertNoWorktreesLeft()

    def test_tracked_python_cache_is_refused_before_any_tool_runs(self) -> None:
        # The recheck's note: a committed tools/__pycache__ .pyc runs instead
        # of the reviewed tools/sync_repo_metadata.py, -B or not.
        marker = self.temp / "cache-ran.txt"
        _commit_cache(self.repo, f"open({str(marker)!r}, 'a', encoding='utf-8').write('cache ran\\n')\n"
                                 "def stamp_html_versions(payload):\n    pass\n")
        self.commit("a committed cache")
        # The hazard is real: the isolated driver itself runs the cache.
        self.tool("-c", GUARD.STAMP_DRIVER)
        self.assertEqual(marker.read_text(encoding="utf-8"), "cache ran\n")
        marker.unlink()
        site = self.temp / "site-cache"
        self.tool(GUARD.BUILD_TOOL, "--source", ".", "--out", str(site))  # imports no sync tool
        metadata = self.repo / "repo-metadata.json"
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata)
        cache = f"tools/__pycache__/sync_repo_metadata.{sys.implementation.cache_tag}.pyc"
        self.assertIn(f"{cache}: Python bytecode is never committed", str(caught.exception))
        self.assertFalse(marker.exists())
        self.assertNoWorktreesLeft()

        # The command line refuses the checkout itself first.
        shutil.move(str(site), str(self.repo / "_site"))
        previous = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(GUARD.main(["--deployed-sha", self.live_sha]), 1)
        self.assertIn("Release deploy refused, nothing was deployed: The checkout tracks Python files", output.getvalue())
        self.assertIn(cache, output.getvalue())
        self.assertNotIn("Approved live commit", output.getvalue())
        self.assertFalse(marker.exists())

    def test_cache_in_the_approved_commit_is_refused(self) -> None:
        marker = self.temp / "cache-ran.txt"
        source = (f"open({str(marker)!r}, 'a', encoding='utf-8').write('cache ran\\n')\n"
                  "def stamp_html_versions(payload):\n    pass\n")
        old = self.old_live_commit(lambda: _commit_cache(self.repo, source))
        site, metadata = self.deploy_job()  # main itself is clean
        with self.assertRaises(GUARD.GuardError) as caught:
            self.guard(site, metadata, live_sha=old)
        self.assertIn(f"Commit {old[:12]} tracks Python files", str(caught.exception))
        self.assertIn("Python bytecode is never committed", str(caught.exception))
        self.assertFalse(marker.exists())
        self.assertFalse((self.temp / "work-1" / "live-site").exists())
        self.assertNoWorktreesLeft()

    # -- a release deploy never becomes the approved baseline --------------

    def test_latent_tool_change_shipped_by_a_release_deploy_stays_held_to_the_approved_commit(self) -> None:
        # The review's A8: main's badge stamping adds a banner only once some
        # importer tag starts with "v9.". For today's metadata it builds the
        # same folder as the approved commit, so a release deploy passes and
        # uploads it. If that release deploy became the baseline, the next
        # release (Blender v9.0.0) would compare the commit with itself and
        # publish the never-approved banner.
        approved = self.live_sha
        _edit(self.repo / GUARD.STAMP_TOOL,
              '    """Write latest release tags into static HTML as fallback content."""\n',
              '    """Write latest release tags into static HTML as fallback content."""\n'
              '    if any(str(((r or {}).get("latest_release") or {}).get("tag", "")).startswith("v9.")\n'
              '           for r in payload.get("repos", {}).values()):\n'
              '        page = Path(pages_root) / "index.html"\n'
              '        page.write_text(page.read_text(encoding="utf-8").replace(\n'
              '            "</body>", "<p>latent banner</p></body>", 1), encoding="utf-8")\n')
        latent = self.commit("badge stamping with a latent banner")

        # (A8a) Today's release passes: the latent commit's output equals the
        # approved commit's, and the run history records it as an upload.
        self.assertEqual(self.release_deploy("v1.0.112", live_sha=approved), [])
        api = FakeActions(
            manual=[_run(10, approved, "2026-10-12T12:00:00Z")],
            dispatched=[_run(20, latent, "2026-10-18T17:00:00Z", title="product-release")],
            jobs={10: _jobs("success"), 20: _jobs("success")},
        )

        # (A8b/A8c) The next release, through the real command line and the
        # (faked) Actions API: the baseline is still the approved commit, so
        # the banner is named and nothing deploys.
        site, _ = self.deploy_job("v9.0.0")
        self.assertIn("<p>latent banner</p>", (site / "index.html").read_text(encoding="utf-8"))
        shutil.move(str(site), str(self.repo / "_site"))
        previous = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        output = io.StringIO()
        with patch.object(GUARD, "_api_get", lambda url, token: api(url)), \
                patch.dict(os.environ, {"GITHUB_RUN_ID": "21"}), contextlib.redirect_stdout(output):
            self.assertEqual(GUARD.main(["--repo", REPO]), 1)
        text = output.getvalue()
        self.assertIn(f"Approved live commit: {approved} (the last manual deploy, run 10)", text)
        self.assertIn("Release deploy refused, nothing was deployed", text)
        self.assertIn("changed: index.html", text)
        self.assertNotIn("is the approved live commit", text)
        self.assertNotIn(20, api.job_calls())
        self.assertNoWorktreesLeft()

    # -- (d) a live commit the guard cannot rebuild is refused safely ------

    def old_live_commit(self, change) -> str:
        """A live commit whose tools differ from today's, with main on top."""
        _git(self.repo, "checkout", "-q", "--orphan", "old")
        change()
        old = self.commit("an older site")
        _git(self.repo, "checkout", "-q", "-f", "main")
        return old

    def assertRefusedSafely(self, live_sha: str, expected: str) -> None:
        site, metadata = self.deploy_job()
        with self.assertRaises(GUARD.ToolsUnsupported) as caught:
            self.guard(site, metadata, live_sha=live_sha)
        self.assertIn(expected, str(caught.exception))
        self.assertNoWorktreesLeft()

    def test_live_commit_older_than_the_build_tool_is_refused(self) -> None:
        old = self.old_live_commit(lambda: shutil.rmtree(self.repo / "tools"))
        self.assertRefusedSafely(old, f"has no {GUARD.BUILD_TOOL} or {GUARD.STAMP_TOOL}")

    def test_live_commit_without_badge_stamping_is_refused(self) -> None:
        old = self.old_live_commit(lambda: _edit(
            self.repo / GUARD.STAMP_TOOL, "def stamp_html_versions(", "def stamp_html_versions_old("))
        self.assertRefusedSafely(old, "cannot stamp version badges")

    def test_live_commit_whose_build_tool_has_no_out_option_is_refused(self) -> None:
        def older_build_tool() -> None:
            (self.repo / GUARD.BUILD_TOOL).write_text(
                "import argparse\nparser = argparse.ArgumentParser()\n"
                "parser.add_argument('--source')\nparser.parse_args()\n",
                encoding="utf-8", newline="\n",
            )
        old = self.old_live_commit(older_build_tool)
        self.assertRefusedSafely(old, "does not accept --source and --out")

    def test_main_says_a_manual_deploy_is_needed_for_an_old_live_commit(self) -> None:
        old = self.old_live_commit(lambda: shutil.rmtree(self.repo / "tools"))
        self.deploy_job()
        shutil.move(str(self.temp / "site-1"), str(self.repo / "_site"))
        previous = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(GUARD.main(["--deployed-sha", old]), 1)
        self.assertIn("Release deploy refused, nothing was deployed", output.getvalue())
        self.assertIn("a manual deploy is needed", output.getvalue())
        self.assertIn("deploy_production=true", output.getvalue())

    def test_live_builder_that_exits_without_output_is_refused(self) -> None:
        def no_output() -> None:
            (self.repo / GUARD.BUILD_TOOL).write_text("raise SystemExit(0)\n", encoding="utf-8")
        old = self.old_live_commit(no_output)
        self.assertRefusedSafely(old, "did not write the folder given with --out")
        self.assertFalse((self.temp / "work-1" / "live-source").exists())

    def test_live_builder_timeout_refuses_and_removes_owned_worktree(self) -> None:
        def slow_builder() -> None:
            (self.repo / GUARD.BUILD_TOOL).write_text(
                "import time\ntime.sleep(10)\n", encoding="utf-8")
        old = self.old_live_commit(slow_builder)
        site, metadata = self.deploy_job()
        run_tool = GUARD._run_tool
        def short_live_deadline(worktree, args):
            # Normal HEAD stamp/build keeps its production budget. Only the
            # deliberately sleeping historical builder gets the short test deadline.
            if worktree.name == "live-source" and args[0] == GUARD.BUILD_TOOL:
                with patch.object(GUARD, "TOOL_TIMEOUT", 0.2):
                    return run_tool(worktree, args)
            return run_tool(worktree, args)
        with patch.object(GUARD, "_run_tool", side_effect=short_live_deadline):
            with self.assertRaises(GUARD.GuardError) as caught:
                self.guard(site, metadata, live_sha=old)
        self.assertIn("took longer than 0.2 s", str(caught.exception))
        self.assertFalse((self.temp / "work-1" / "live-source").exists())
        self.assertNoWorktreesLeft()

    def test_unknown_live_commit_is_refused(self) -> None:
        site, metadata = self.deploy_job()
        with self.assertRaises(GUARD.GuardError):
            self.guard(site, metadata, live_sha="0" * 40)

    # -- the command line ---------------------------------------------------

    def test_main_exit_codes(self) -> None:
        previous = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        self.commit("tests only")
        self.tool("-c", GUARD.STAMP_DRIVER)
        self.tool(GUARD.BUILD_TOOL)
        self.assertEqual(GUARD.main(["--deployed-sha", self.live_sha]), 0)

        _edit(self.repo / "index.html", "</body>", "<!-- merged later --></body>")
        self.commit("undeployed change")
        self.tool(GUARD.BUILD_TOOL)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(GUARD.main(["--deployed-sha", self.live_sha]), 1)
        self.assertIn("Release deploy refused, nothing was deployed", output.getvalue())
        self.assertIn("changed: index.html", output.getvalue())
        self.assertNoWorktreesLeft()


class ToolProcessTests(unittest.TestCase):
    def test_git_timeout_is_a_bounded_guard_refusal(self) -> None:
        timeout = subprocess.TimeoutExpired(["git", "fetch"], GUARD.GIT_TIMEOUT)
        with patch.object(GUARD.subprocess, "run", side_effect=timeout) as run:
            with self.assertRaises(GUARD.GuardError) as caught:
                GUARD._git(ROOT, "fetch", "--no-tags", "origin", "a" * 40)
        self.assertEqual(run.call_args.kwargs["timeout"], 60)
        self.assertIn("took longer than 60 s", str(caught.exception))

    # Variables a commit's tools must never see: tokens under any name, and
    # GitHub's step files, through which a process could set variables, PATH
    # entries or outputs for the steps after the guard.
    WITHHELD = {"GH_TOKEN": "x", "GITHUB_TOKEN": "x", "CLOUDFLARE_API_TOKEN": "x", "CLOUDFLARE_ACCOUNT_ID": "x",
                "AWS_SECRET_ACCESS_KEY": "x", "SOME_API_KEY": "x", "DB_PASSWORD": "x", "DEPLOY_HOOK_URL": "x",
                "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "x", "ACTIONS_RUNTIME_TOKEN": "x",
                "GITHUB_ENV": "x", "GITHUB_PATH": "x", "GITHUB_OUTPUT": "x", "GITHUB_STEP_SUMMARY": "x",
                "GITHUB_STATE": "x", "PYTHONPATH": "x", "PYTHONSTARTUP": "x", "NODE_OPTIONS": "x",
                "KEEP_ME": "1"}

    def test_tools_get_no_secrets_and_no_github_step_files(self) -> None:
        with patch.dict(os.environ, self.WITHHELD):
            env = GUARD._tool_env()
        self.assertFalse(set(self.WITHHELD) & set(env), set(self.WITHHELD) & set(env))
        self.assertEqual(env.get("PYTHONDONTWRITEBYTECODE"), "1")
        self.assertEqual(env.get("PATH") or env.get("Path"), os.environ.get("PATH"))
        self.assertTrue(set(env) <= set(os.environ) | {"PYTHONDONTWRITEBYTECODE"})

    def test_a_tool_process_sees_only_the_allowed_variables(self) -> None:
        # The same through a real tool run: what the commit's stamp function
        # finds in os.environ, and the interpreter flags it runs under.
        with tempfile.TemporaryDirectory() as temp:
            worktree = Path(temp)
            (worktree / "tools").mkdir()
            (worktree / "tools" / "sync_repo_metadata.py").write_text(
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "def stamp_html_versions(payload):\n"
                "    Path('seen.json').write_text(json.dumps({'env': sorted(os.environ),\n"
                "        'isolated': sys.flags.isolated, 'no_cache': sys.dont_write_bytecode,\n"
                "        'path': sys.path}), encoding='utf-8')\n",
                encoding="utf-8",
            )
            (worktree / "repo-metadata.json").write_text("{}", encoding="utf-8")
            with patch.dict(os.environ, self.WITHHELD):
                result = GUARD._run_tool(worktree, ["-c", GUARD.STAMP_DRIVER])
            self.assertEqual(result.returncode, 0, result.stderr)
            seen = json.loads((worktree / "seen.json").read_text(encoding="utf-8"))
        self.assertFalse(set(self.WITHHELD) & set(seen["env"]), seen["env"])
        self.assertEqual(seen["isolated"], 1)
        self.assertTrue(seen["no_cache"])
        # The worktree's tools/ comes after every other entry; its root is absent.
        tools = os.path.normcase(str(worktree / "tools"))
        self.assertEqual(os.path.normcase(seen["path"][-1]), tools)
        self.assertNotIn("", seen["path"])
        self.assertNotIn(os.path.normcase(str(worktree)), [os.path.normcase(entry) for entry in seen["path"]])

    def test_stamp_driver_never_imports_standard_module_names_from_the_worktree(self) -> None:
        # The recheck's route (b), at the process level. Planted: a root
        # json.py and urllib/ package (sys.path[0] when the driver ran as
        # -B -E -s -c) and a tools/csv.py, which the commit's sync tool
        # imports after the driver has put tools/ on sys.path.
        with tempfile.TemporaryDirectory() as temp:
            worktree = Path(temp) / "worktree"
            (worktree / "tools").mkdir(parents=True)
            marker = Path(temp) / "imports.txt"
            (worktree / "json.py").write_text(_marker_module(marker), encoding="utf-8")
            (worktree / "urllib").mkdir()
            (worktree / "urllib" / "__init__.py").write_text(_marker_module(marker), encoding="utf-8")
            (worktree / "tools" / "csv.py").write_text(_marker_module(marker), encoding="utf-8")
            (worktree / "tools" / "sync_repo_metadata.py").write_text(
                "import csv\n"
                "from pathlib import Path\n"
                "def stamp_html_versions(payload):\n"
                "    Path('stamped.txt').write_text(csv.__file__, encoding='utf-8')\n",
                encoding="utf-8",
            )
            (worktree / "repo-metadata.json").write_text("{}", encoding="utf-8")

            def imported() -> str:
                text = marker.read_text(encoding="utf-8") if marker.exists() else ""
                if marker.exists():
                    marker.unlink()
                return text

            # Controls: the old flags import the root json.py; tools/ put in
            # FRONT of the standard library hands the sync tool tools/csv.py.
            old = subprocess.run([sys.executable, "-B", "-E", "-s", "-X", "utf8", "-c", GUARD.STAMP_DRIVER],
                                 cwd=str(worktree), env=GUARD._tool_env(), capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=60)
            self.assertNotEqual(old.returncode, 0)
            self.assertIn("json", imported())
            in_front = GUARD.STAMP_DRIVER.replace("sys.path.append(", "sys.path.insert(0, ")
            self.assertNotEqual(GUARD._run_tool(worktree, ["-c", in_front]).returncode, 0)
            self.assertIn("csv", imported())

            result = GUARD._run_tool(worktree, ["-c", GUARD.STAMP_DRIVER])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(imported(), "")
            csv_file = Path((worktree / "stamped.txt").read_text(encoding="utf-8")).resolve()
            self.assertFalse(csv_file.is_relative_to(worktree.resolve()), csv_file)
            self.assertFalse((worktree / "tools" / "__pycache__").exists())

    def test_guard_refuses_to_run_with_a_repository_module_loaded(self) -> None:
        # Second line of defence: if a repository module is already loaded
        # (here tools/filecmp.py, imported before the guard starts), the guard
        # refuses before doing anything instead of comparing with it.
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "tools").mkdir()
            shutil.copyfile(ROOT / "tools" / "check_metadata_only_deploy.py",
                            repo / "tools" / "check_metadata_only_deploy.py")
            (repo / "tools" / "filecmp.py").write_text(
                "def cmp(f1, f2, shallow=True):\n    return True\n", encoding="utf-8")
            starter = ("import runpy, sys; sys.path.insert(0, 'tools'); import filecmp; "
                       "sys.argv = ['tools/check_metadata_only_deploy.py', '--deployed-sha', 'a' * 40]; "
                       "runpy.run_path('tools/check_metadata_only_deploy.py', run_name='__main__')")
            result = subprocess.run([sys.executable, "-B", "-c", starter], cwd=str(repo), capture_output=True,
                                    text=True, encoding="utf-8", errors="replace", timeout=60)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("the guard imported code from the repository it is checking", output)
        self.assertIn("filecmp (", output)
        self.assertNotIn("not a git checkout", output)  # refused before main() ran
        self.assertNotIn("Traceback", output)

    def test_repository_modules_are_found_by_location(self) -> None:
        import types
        from importlib.machinery import ModuleSpec
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp).resolve()
            outside = Path(sys.executable).resolve().parent

            def module(name: str, file: str | None = None, origin: str | None = None,
                       path: list | None = None) -> types.ModuleType:
                made = types.ModuleType(name)
                if file is not None:
                    made.__file__ = file
                spec = ModuleSpec(name, None, origin=origin)
                spec.has_location = origin not in (None, "built-in", "frozen")
                made.__spec__ = spec
                if path is not None:
                    made.__path__ = path
                return made

            modules = {
                "__main__": module("__main__", str(repo / "tools" / "check_metadata_only_deploy.py")),
                "json": module("json", str(repo / "tools" / "json" / "__init__.py")),
                "shutil": module("shutil", origin=str(repo / "tools" / "shutil.py")),
                "space": module("space", path=[str(repo / "tools" / "space")]),
                "filecmp": module("filecmp", str(outside / "Lib" / "filecmp.py")),
                "sys": module("sys", origin="built-in"),
                "os": module("os", str(outside / "Lib" / "os.py"), origin="frozen"),
                "missing": None,
            }
            found = GUARD._repository_modules(str(repo), modules)
        self.assertEqual([entry.split(" ", 1)[0] for entry in found], ["json", "shutil", "space"])

    def test_tools_import_only_their_own_worktree(self) -> None:
        # -I ignores PYTHONPATH, so today's tools folder cannot shadow the
        # live commit's; the only sync_repo_metadata on sys.path is the
        # worktree's own.
        with tempfile.TemporaryDirectory() as temp:
            worktree = Path(temp)
            (worktree / "tools").mkdir()
            (worktree / "tools" / "sync_repo_metadata.py").write_text(
                "from pathlib import Path\n"
                "def stamp_html_versions(payload):\n"
                "    Path('stamped.txt').write_text(__file__, encoding='utf-8')\n",
                encoding="utf-8",
            )
            (worktree / "repo-metadata.json").write_text("{}", encoding="utf-8")
            with patch.dict(os.environ, {"PYTHONPATH": str(ROOT / "tools")}):
                result = GUARD._run_tool(worktree, ["-c", GUARD.STAMP_DRIVER])
            self.assertEqual(result.returncode, 0, result.stderr)
            stamped_by = Path((worktree / "stamped.txt").read_text(encoding="utf-8")).resolve()
            self.assertEqual(stamped_by, (worktree / "tools" / "sync_repo_metadata.py").resolve())
            self.assertFalse((worktree / "tools" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
