"""Regression tests for tools/check_metadata_only_deploy.py.

The end-to-end cases build real public folders from a throwaway git
repository that holds a copy of this site's public files, so they exercise
the same worktree checkout, badge stamping and tools/build_site.py allowlist
the release deploy uses. Nothing is fetched from the network.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_metadata_only_deploy", ROOT / "tools" / "check_metadata_only_deploy.py")
assert SPEC is not None and SPEC.loader is not None
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
BUILD = GUARD.build_site
SYNC = GUARD.sync

API = "https://api.github.com/repos/BlueCollar-Systems/BlueCollar-Website/actions"
BLENDER = "BlueCollar-Systems/PDF-Importer-Blender"


def _run(run_id: int, sha: str, started: str, *, branch: str = "main") -> dict:
    return {"id": run_id, "head_sha": sha, "head_branch": branch, "run_started_at": started}


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
    def __init__(self, manual: list[dict], dispatched: list[dict], jobs: dict[int, dict]) -> None:
        self.runs = {"workflow_dispatch": manual, "repository_dispatch": dispatched}
        self.jobs = jobs
        self.calls: list[str] = []

    def __call__(self, url: str):
        self.calls.append(url)
        for event, runs in self.runs.items():
            if url == f"{API}/workflows/website-ci.yml/runs?event={event}&status=completed&per_page=50":
                return {"workflow_runs": runs}
        for run_id, jobs in self.jobs.items():
            if url == f"{API}/runs/{run_id}/jobs?filter=all&per_page=100":
                return jobs
        raise AssertionError(f"unexpected API call {url}")


class FindDeployedCommitTests(unittest.TestCase):
    def find(self, api: FakeActions, current: str | None = None):
        return GUARD.find_deployed_commit("BlueCollar-Systems/BlueCollar-Website", api, current_run_id=current)

    def test_newest_run_whose_upload_succeeded_wins(self) -> None:
        api = FakeActions(
            manual=[
                _run(30, "c" * 40, "2026-10-18T18:00:00Z"),  # validation only
                _run(10, "a" * 40, "2026-10-12T12:00:00Z"),  # older deploy
            ],
            dispatched=[_run(20, "b" * 40, "2026-10-18T17:00:00Z")],
            jobs={30: _jobs(None), 20: _jobs("success"), 10: _jobs("success")},
        )
        self.assertEqual(self.find(api), ("b" * 40, 20))
        self.assertNotIn(f"{API}/runs/10/jobs?filter=all&per_page=100", api.calls)

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
            dispatched=[_run(60, "9" * 40, "2026-10-18T20:00:00Z")],
            jobs={50: _jobs("failure"), 45: _jobs("success"), 10: _jobs("success"), 60: _jobs("success")},
        )
        self.assertEqual(self.find(api, current="60"), ("a" * 40, 10))

    def test_no_deploy_found_refuses(self) -> None:
        api = FakeActions(manual=[_run(30, "c" * 40, "2026-10-18T18:00:00Z")], dispatched=[], jobs={30: _jobs("skipped")})
        with self.assertRaises(GUARD.GuardError):
            self.find(api)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Guard Test", "-c", "user.email=guard@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _copy_public_files(destination: Path) -> None:
    """The site's public files, plus a README that is not published."""
    for pattern in BUILD.ALLOWED_GLOBS:
        for path in ROOT.glob(pattern):
            shutil.copyfile(path, destination / path.name)
    for name in BUILD.ALLOWED_FILES:
        shutil.copyfile(ROOT / name, destination / name)
    for name in BUILD.ALLOWED_DIRS:
        shutil.copytree(ROOT / name, destination / name, ignore=shutil.ignore_patterns("__pycache__"))
    (destination / "README.md").write_text("repository notes\n", encoding="utf-8", newline="\n")
    (destination / ".gitignore").write_text("_site/\n", encoding="utf-8", newline="\n")


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

    def commit(self, message: str) -> str:
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "--allow-empty", "-m", message)
        return _git(self.repo, "rev-parse", "HEAD")

    def release_deploy(self, tag: str = "v9.9.9") -> list[str]:
        """What the deploy job does: sync, stamp, build, then the guard."""
        payload = _fresh_metadata(self.repo, tag)
        metadata = self.repo / "repo-metadata.json"
        metadata.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        SYNC.stamp_html_versions(payload, self.repo)
        site = self.temp / "site"
        BUILD.build_site(self.repo, site)
        head = _git(self.repo, "rev-parse", "HEAD")
        work = self.temp / "work"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir()
        return GUARD.check(self.repo, site, metadata, self.live_sha, head, work)

    def test_new_release_metadata_alone_passes(self) -> None:
        self.commit("tests only")  # a commit that changes nothing public
        self.assertEqual(self.release_deploy(), [])
        index = (self.temp / "site" / "index.html").read_text(encoding="utf-8")
        self.assertIn("v9.9.9", index)  # the badge really was stamped
        self.assertNotIn("live-source", _git(self.repo, "worktree", "list"))

    def test_badge_stamp_commit_after_the_last_deploy_passes(self) -> None:
        payload = _fresh_metadata(self.repo, "v9.9.8")
        (self.repo / "repo-metadata.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        SYNC.stamp_html_versions(payload, self.repo)
        self.commit("chore: stamp release badges from metadata sync [skip release]")
        self.assertEqual(self.release_deploy("v9.9.9"), [])

    def test_repository_only_changes_pass(self) -> None:
        (self.repo / "README.md").write_text("new notes\n", encoding="utf-8", newline="\n")
        (self.repo / "tools").mkdir()
        (self.repo / "tools" / "helper.py").write_text("print('x')\n", encoding="utf-8", newline="\n")
        self.commit("docs and tools")
        self.assertEqual(self.release_deploy(), [])

    def test_undeployed_page_copy_change_is_refused(self) -> None:
        index = self.repo / "index.html"
        index.write_text(index.read_text(encoding="utf-8").replace("</body>", "<p>new copy</p></body>", 1),
                         encoding="utf-8", newline="\n")
        self.commit("copy change merged but not deployed")
        self.assertEqual(self.release_deploy(), ["changed: index.html"])

    def test_new_and_removed_public_files_are_refused(self) -> None:
        (self.repo / "extra.css").write_text("body{}\n", encoding="utf-8", newline="\n")
        removed = next(p for p in sorted((self.repo / "p-records").rglob("*")) if p.is_file())
        removed_name = removed.relative_to(self.repo).as_posix()
        removed.unlink()
        self.commit("add a stylesheet, drop a record")
        self.assertEqual(
            self.release_deploy(),
            ["new public file: extra.css", f"removed public file: {removed_name}"],
        )

    def test_same_commit_needs_no_rebuild(self) -> None:
        # No worktree and no build: the folder arguments are not even read.
        missing = self.temp / "no-such-folder"
        self.assertEqual(GUARD.check(self.repo, missing, missing, self.live_sha, self.live_sha, missing), [])

    def test_unknown_live_commit_is_refused(self) -> None:
        with self.assertRaises(GUARD.GuardError):
            GUARD.build_reference_site(self.repo, "0" * 40, self.repo / "repo-metadata.json", self.temp)

    def test_main_exit_codes(self) -> None:
        previous = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        self.commit("tests only")
        SYNC.stamp_html_versions(json.loads((self.repo / "repo-metadata.json").read_text(encoding="utf-8")), self.repo)
        BUILD.build_site(self.repo, self.repo / "_site")
        self.assertEqual(GUARD.main(["--deployed-sha", self.live_sha]), 0)

        index = self.repo / "index.html"
        index.write_text(index.read_text(encoding="utf-8") + "<!-- merged later -->\n", encoding="utf-8", newline="\n")
        self.commit("undeployed change")
        BUILD.build_site(self.repo, self.repo / "_site")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(GUARD.main(["--deployed-sha", self.live_sha]), 1)
        self.assertIn("Release deploy refused, nothing was deployed", output.getvalue())
        self.assertIn("changed: index.html", output.getvalue())


if __name__ == "__main__":
    unittest.main()
