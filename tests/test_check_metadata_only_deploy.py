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
import re
import shutil
import subprocess
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

    def test_newest_run_whose_upload_succeeded_wins(self) -> None:
        api = FakeActions(
            manual=[
                _run(30, "c" * 40, "2026-10-18T18:00:00Z"),  # validation only
                _run(10, "a" * 40, "2026-10-12T12:00:00Z"),  # older deploy
            ],
            dispatched=[_run(20, "b" * 40, "2026-10-18T17:00:00Z", title="product-release")],
            jobs={30: _jobs(None), 20: _jobs("success"), 10: _jobs("success")},
        )
        self.assertEqual(self.find(api), ("b" * 40, 20))
        self.assertNotIn(10, api.job_calls())

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
                _run(50, "e" * 40, "2026-10-18T19:00:00Z"),
                _run(45, "f" * 40, "2026-10-18T18:30:00Z", branch="claude/x"),
                _run(10, "a" * 40, "2026-10-12T12:00:00Z"),
            ],
            dispatched=[_run(60, "9" * 40, "2026-10-18T20:00:00Z", title="product-release")],
            jobs={50: _jobs("failure"), 45: _jobs("success"), 10: _jobs("success"), 60: _jobs("success")},
        )
        self.assertEqual(self.find(api, current="60"), ("a" * 40, 10))
        self.assertNotIn(45, api.job_calls())
        self.assertNotIn(60, api.job_calls())

    def test_validation_only_dispatch_runs_cost_no_job_lookup(self) -> None:
        # GitHub titles a repository_dispatch run with its event type; only a
        # product-release dispatch (or an unknown title) can have deployed.
        api = FakeActions(
            manual=[_run(10, "a" * 40, "2026-10-12T12:00:00Z")],
            dispatched=[
                _run(70, "7" * 40, "2026-10-18T20:00:00Z", title="product-update"),
                _run(69, "6" * 40, "2026-10-18T19:00:00Z", title="steel-shapes-release"),
                _run(68, "5" * 40, "2026-10-18T18:00:00Z", title="steel-shapes-update"),
                _run(67, "4" * 40, "2026-10-18T17:00:00Z", title="something-new"),
                _run(66, "3" * 40, "2026-10-18T16:00:00Z"),
            ],
            jobs={67: _jobs(None), 66: _jobs(None), 10: _jobs("success")},
        )
        self.assertEqual(self.find(api), ("a" * 40, 10))
        self.assertEqual(api.job_calls(), [67, 66, 10])

    def test_pages_back_through_months_of_dispatch_traffic(self) -> None:
        # About three product-update dispatches a day filled the old 60-run
        # window in under three weeks. Ninety days of them still find the
        # deploy, with one job lookup.
        dispatched = [
            _run(10_000 - n, "7" * 40, _stamp(18 - n // 300, 1439 - n % 300), title="product-update")
            for n in range(270)
        ]
        api = FakeActions(
            manual=[_run(10, "a" * 40, "2026-07-01T12:00:00Z")],
            dispatched=dispatched,
            jobs={10: _jobs("success")},
        )
        self.assertEqual(self.find(api), ("a" * 40, 10))
        self.assertEqual(api.job_calls(), [10])
        pages = [url for url in api.calls if "event=repository_dispatch" in url]
        self.assertEqual(len(pages), 3)

    def test_no_deploy_found_says_exactly_why(self) -> None:
        api = FakeActions(
            manual=[_run(30, "c" * 40, "2026-10-18T18:00:00Z")],
            dispatched=[_run(31, "d" * 40, "2026-10-18T17:00:00Z", title="product-update")],
            jobs={30: _jobs("skipped")},
        )
        with self.assertRaises(GUARD.GuardError) as caught:
            self.find(api)
        message = str(caught.exception)
        self.assertIn("The live commit is unknown", message)
        self.assertIn("all 1 completed workflow_dispatch runs and all 1 completed repository_dispatch runs", message)
        self.assertIn("1 of them could have deployed", message)
        self.assertIn(f"none has a successful '{GUARD.DEPLOY_STEP}' step", message)

    def test_history_beyond_the_api_limit_is_named_in_the_refusal(self) -> None:
        full = GUARD.RUNS_PER_PAGE * GUARD.MAX_RUN_PAGES
        dispatched = [_run(50_000 - n, "7" * 40, _stamp(18, 0), title="product-update") for n in range(full + 5)]
        api = FakeActions(manual=[], dispatched=dispatched, jobs={})
        with self.assertRaises(GUARD.GuardError) as caught:
            self.find(api)
        message = str(caught.exception)
        self.assertIn(f"the newest {full} of {full + 5} repository_dispatch runs (the Actions API lists no more)", message)
        self.assertIn("older than the run history the Actions API lists", message)
        self.assertEqual(len([url for url in api.calls if "event=repository_dispatch" in url]), GUARD.MAX_RUN_PAGES)

    def test_job_lookups_are_bounded_and_the_bound_is_named(self) -> None:
        manual = [_run(1000 + n, "c" * 40, _stamp(18, 1000 - n)) for n in range(GUARD.MAX_JOB_LOOKUPS + 3)]
        api = FakeActions(manual=manual, dispatched=[], jobs={run["id"]: _jobs("skipped") for run in manual})
        with self.assertRaises(GUARD.GuardError) as caught:
            self.find(api)
        self.assertEqual(len(api.job_calls()), GUARD.MAX_JOB_LOOKUPS)
        self.assertIn(f"reads at most {GUARD.MAX_JOB_LOOKUPS} runs' jobs", str(caught.exception))

    def test_website_ci_keeps_the_dispatch_type_as_run_title(self) -> None:
        # The title filter relies on GitHub's default run name; a run-name
        # would only cost job lookups, but keep the assumption visible.
        text = (ROOT / ".github" / "workflows" / "website-ci.yml").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?m)^run-name:")


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


def _edit(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) >= count, (path, old)
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


class GuardEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="guard-test-"))
        self.addCleanup(shutil.rmtree, self.temp, True)
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
    def test_tools_run_without_secrets(self) -> None:
        secrets = {"GH_TOKEN": "x", "GITHUB_TOKEN": "x", "CLOUDFLARE_API_TOKEN": "x",
                   "AWS_SECRET_ACCESS_KEY": "x", "SOME_API_KEY": "x", "DB_PASSWORD": "x"}
        with patch.dict(os.environ, {**secrets, "KEEP_ME": "1"}):
            env = GUARD._tool_env()
        self.assertFalse(set(secrets) & set(env))
        self.assertEqual(env.get("KEEP_ME"), "1")

    def test_tools_import_only_their_own_worktree(self) -> None:
        # -E ignores PYTHONPATH, so today's tools folder cannot shadow the
        # live commit's; the worktree's own tools folder comes first.
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
