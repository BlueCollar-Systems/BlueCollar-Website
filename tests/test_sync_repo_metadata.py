from __future__ import annotations

import contextlib
import copy
import datetime as real_dt
import importlib.util
import io
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sync_repo_metadata", ROOT / "tools" / "sync_repo_metadata.py"
)
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)

VALIDATE_SPEC = importlib.util.spec_from_file_location(
    "validate_static_metadata", ROOT / "tools" / "validate_static_metadata.py"
)
assert VALIDATE_SPEC is not None and VALIDATE_SPEC.loader is not None
VALIDATE = importlib.util.module_from_spec(VALIDATE_SPEC)
VALIDATE_SPEC.loader.exec_module(VALIDATE)


class ReleaseSummaryTests(unittest.TestCase):
    def test_release_summary_preserves_exact_target_commit(self) -> None:
        commit = "48ca80ed2c47c91a66d6060fbf783d71653d7a3f"
        summary = SYNC._release_summary(
            {
                "tag_name": "v4.0.85",
                "target_commitish": commit,
                "assets": [],
            }
        )

        self.assertEqual(summary.get("target_commitish"), commit)

    def test_primary_assets_precede_but_preserve_supporting_attestation(self) -> None:
        summary = SYNC._release_summary(
            {
                "tag_name": "v4.0.85",
                "assets": [
                    {
                        "name": "FreeCAD-PDF-Importer-Setup_v4.0.85.attestation.json",
                        "browser_download_url": "https://example.invalid/attestation.json",
                        "size": 810,
                        "content_type": "application/json",
                        "digest": "sha256:" + "c" * 64,
                    },
                    {
                        "name": "FreeCAD-PDF-Importer_v4.0.85.zip",
                        "browser_download_url": "https://example.invalid/freecad.zip",
                        "size": 61_115_147,
                        "content_type": "application/zip",
                        "digest": "sha256:" + "a" * 64,
                    },
                    {
                        "name": "FreeCAD-PDF-Importer-Setup_v4.0.85.exe",
                        "browser_download_url": "https://example.invalid/freecad.exe",
                        "size": 17_756_091,
                        "content_type": "application/x-msdownload",
                        "digest": "sha256:" + "b" * 64,
                    },
                ],
            }
        )

        self.assertEqual(
            [asset["name"] for asset in summary["assets"]],
            [
                "FreeCAD-PDF-Importer-Setup_v4.0.85.exe",
                "FreeCAD-PDF-Importer_v4.0.85.zip",
                "FreeCAD-PDF-Importer-Setup_v4.0.85.attestation.json",
            ],
        )

    def test_primary_asset_preserves_github_digest(self) -> None:
        digest = "sha256:" + "a" * 64
        summary = SYNC._release_summary(
            {
                "tag_name": "v1.2.3",
                "name": "v1.2.3",
                "html_url": "https://example.invalid/release",
                "published_at": "2026-08-01T00:00:00Z",
                "immutable": True,
                "assets": [
                    {
                        "name": "LibreCAD-PDF-Importer-Windows-Portable_v1.2.3.zip",
                        "browser_download_url": "https://example.invalid/portable.zip",
                        "size": 123,
                        "content_type": "application/zip",
                        "digest": digest,
                    }
                ],
            }
        )

        self.assertEqual(summary["assets"][0]["digest"], digest)
        self.assertIs(summary["immutable"], True)

    def test_absent_digest_is_explicit_not_invented(self) -> None:
        summary = SYNC._release_summary(
            {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "FreeCAD-PDF-Importer_v1.2.3.zip",
                        "browser_download_url": "https://example.invalid/freecad.zip",
                        "size": 456,
                        "content_type": "application/zip",
                    }
                ],
            }
        )

        self.assertIsNone(summary["assets"][0]["digest"])


class ReleaseDigestValidationTests(unittest.TestCase):
    def _repos(self, digest: object, *, immutable: object = True) -> dict:
        return {
            "BlueCollar-Systems/PDF-Importer-LibreCAD": {
                "latest_release": {
                    "immutable": immutable,
                    "assets": [
                        {
                            "name": "LibreCAD-PDF-Importer-Windows-Portable_v1.2.3.zip",
                            "digest": digest,
                        }
                    ],
                }
            }
        }

    def test_accepts_canonical_sha256_digest(self) -> None:
        failures: list[str] = []
        checked = VALIDATE._check_release_asset_digests(
            self._repos("sha256:" + "b" * 64), failures
        )

        self.assertEqual(checked, 1)
        self.assertEqual(failures, [])

    def test_rejects_missing_or_malformed_digest(self) -> None:
        for digest in (None, "", "sha256:1234", "SHA256:" + "b" * 64):
            with self.subTest(digest=digest):
                failures: list[str] = []
                checked = VALIDATE._check_release_asset_digests(
                    self._repos(digest), failures
                )
                self.assertEqual(checked, 1)
                self.assertEqual(len(failures), 1)

    def test_requires_every_importer_release_to_be_immutable(self) -> None:
        repos = {
            repo: {
                "latest_release": {
                    "immutable": True,
                    "target_commitish": "1" * 40,
                    "assets": [],
                }
            }
            for repo in VALIDATE.REQUIRED_IMPORTER_REPOS
        }
        failures: list[str] = []
        checked = VALIDATE._check_importer_release_immutability(repos, failures)

        self.assertEqual(checked, 4)
        self.assertEqual(failures, [])

        repos["BlueCollar-Systems/PDF-Importer-LibreCAD"]["latest_release"][
            "immutable"
        ] = False
        repos["BlueCollar-Systems/PDF-Importer-SketchUp"]["latest_release"][
            "target_commitish"
        ] = "main"
        del repos["BlueCollar-Systems/PDF-Importer-Blender"]
        failures = []
        checked = VALIDATE._check_importer_release_immutability(repos, failures)

        self.assertEqual(checked, 3)
        self.assertEqual(len(failures), 3)
        self.assertTrue(any("LibreCAD" in failure for failure in failures))
        self.assertTrue(any("Blender" in failure for failure in failures))
        self.assertTrue(any("SketchUp" in failure for failure in failures))



def _release(tag: str, asset_name: str, *, digest: str = "sha256:" + "a" * 64, size: int = 100) -> dict:
    return {
        "tag_name": tag,
        "name": tag,
        "html_url": f"https://example.invalid/releases/tag/{tag}",
        "published_at": "2026-10-01T00:00:00Z",
        "target_commitish": "1" * 40,
        "immutable": True,
        "draft": False,
        "prerelease": False,
        "assets": [{
            "name": asset_name,
            "browser_download_url": f"https://example.invalid/releases/download/{tag}/{asset_name}",
            "size": size,
            "content_type": "application/zip",
            "digest": digest,
        }],
    }


class FakeGitHub:
    """Fixed GitHub API answers for every repo sync_repo_metadata reads."""

    def __init__(self) -> None:
        self.private: dict[str, bool] = {}
        self.pushed_at = {repo: "2026-10-06T00:00:00Z" for repo in SYNC.REPOS}
        self.releases: dict[str, list[dict]] = {
            "BlueCollar-Systems/PDF-Importer-SketchUp": [
                _release("v3.7.1", "SketchUp-PDF-Importer_v3.7.1.rbz"),
                _release("steel-v1.0.2", "Structural-Steel-SU-Shapes-latest.zip"),
            ],
            "BlueCollar-Systems/PDF-Importer-FreeCAD": [
                # Released importer, but no steel-v release yet: the steel
                # badge falls back to the push date, so pushed_at is visible.
                _release("v4.0.1", "FreeCAD-PDF-Importer_v4.0.1.zip"),
            ],
            # No release at all: the badge shows the push date.
            "BlueCollar-Systems/PDF-Importer-Blender": [],
            "BlueCollar-Systems/PDF-Importer-LibreCAD": [
                _release("v1.0.1", "LibreCAD-PDF-Importer-Windows-Portable_v1.0.1.zip"),
            ],
        }

    def __call__(self, url: str, token: str | None = None):
        prefix = "https://api.github.com/repos/"
        assert url.startswith(prefix), url
        rest = url[len(prefix):]
        for repo in SYNC.REPOS:
            if rest == repo:
                return {
                    "default_branch": "main",
                    "pushed_at": self.pushed_at[repo],
                    "html_url": f"https://github.com/{repo}",
                    "private": self.private.get(repo, False),
                }
            if rest == repo + "/releases?per_page=100":
                return copy.deepcopy(self.releases[repo])
            if rest == repo + "/releases/latest":
                versioned = [r for r in self.releases[repo] if r["tag_name"].startswith("v")]
                return copy.deepcopy(versioned[0]) if versioned else {}
        raise AssertionError(f"unexpected API call {url}")


class _Clock:
    """A clock that moves forward one hour per call, like separate cron runs."""

    UTC = real_dt.UTC

    def __init__(self) -> None:
        self.calls = 0
        clock = self

        class _DateTime:
            @staticmethod
            def now(tz=None):
                clock.calls += 1
                return real_dt.datetime(2026, 10, 10, clock.calls % 24, 0, 0, tzinfo=tz)

        self.datetime = _DateTime


class IdempotenceTests(unittest.TestCase):
    """A sync whose only change is a timestamp must not rewrite the files."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        (self.cwd / "index.html").write_text(
            '<!DOCTYPE html><span data-repo-version="BlueCollar-Systems/PDF-Importer-LibreCAD">v0.0.0</span>\n',
            encoding="utf-8",
        )
        previous_cwd = os.getcwd()
        os.chdir(self.cwd)
        self.addCleanup(os.chdir, previous_cwd)
        self.github = FakeGitHub()
        clock = _Clock()
        self.enterContext(patch.object(SYNC, "_json_get", self.github))
        self.enterContext(patch.object(SYNC, "dt", types.SimpleNamespace(datetime=clock.datetime, UTC=clock.UTC)))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.events = iter(["schedule", "push", "repository_dispatch", "workflow_dispatch", "schedule", "push"])

    def run_sync(self) -> bytes:
        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": next(self.events)}):
            self.assertEqual(SYNC.main(), 0)
        return (self.cwd / "repo-metadata.json").read_bytes()

    def test_second_run_with_same_releases_keeps_identical_bytes(self) -> None:
        first = self.run_sync()
        page = self.cwd / "index.html"
        html_first = page.read_bytes()
        os.utime(page, ns=(1_000_000_000, 1_000_000_000))
        second = self.run_sync()
        self.assertEqual(first, second)
        self.assertEqual(html_first, page.read_bytes())
        self.assertEqual(page.stat().st_mtime_ns, 1_000_000_000, "unchanged page was rewritten")
        self.assertIn(b"v1.0.1", html_first)
        self.assertNotIn(b"\r\n", html_first)

    def test_push_date_on_a_released_repo_is_not_a_change(self) -> None:
        first = self.run_sync()
        self.github.pushed_at["BlueCollar-Systems/PDF-Importer-LibreCAD"] = "2026-10-09T12:00:00Z"
        self.github.pushed_at["BlueCollar-Systems/PDF-Importer-SketchUp"] = "2026-10-09T12:00:00Z"
        self.assertEqual(first, self.run_sync())

    def test_new_release_tag_rewrites_the_file(self) -> None:
        first = self.run_sync()
        self.github.releases["BlueCollar-Systems/PDF-Importer-LibreCAD"].insert(
            0, _release("v1.0.2", "LibreCAD-PDF-Importer-Windows-Portable_v1.0.2.zip")
        )
        second = self.run_sync()
        self.assertNotEqual(first, second)
        self.assertIn(b"v1.0.2", second)
        self.assertIn(b"v1.0.2", (self.cwd / "index.html").read_bytes())

    def test_asset_digest_or_size_change_rewrites_the_file(self) -> None:
        first = self.run_sync()
        asset = self.github.releases["BlueCollar-Systems/PDF-Importer-LibreCAD"][0]["assets"][0]
        asset["digest"] = "sha256:" + "b" * 64
        second = self.run_sync()
        self.assertNotEqual(first, second)
        self.assertIn(b"sha256:" + b"b" * 64, second)
        asset["size"] = 101
        self.assertNotEqual(second, self.run_sync())

    def test_steel_release_change_rewrites_the_file(self) -> None:
        first = self.run_sync()
        self.github.releases["BlueCollar-Systems/PDF-Importer-SketchUp"].insert(
            0, _release("steel-v1.0.3", "Structural-Steel-SU-Shapes-latest.zip")
        )
        self.assertNotEqual(first, self.run_sync())

    def test_push_date_on_a_repo_without_a_release_rewrites_the_file(self) -> None:
        first = self.run_sync()
        self.github.pushed_at["BlueCollar-Systems/PDF-Importer-Blender"] = "2026-10-09T12:00:00Z"
        second = self.run_sync()
        self.assertNotEqual(first, second)
        self.assertIn(b"2026-10-09T12:00:00Z", second)

    def test_push_date_shown_by_a_steel_badge_without_steel_release_rewrites(self) -> None:
        first = self.run_sync()
        self.github.pushed_at["BlueCollar-Systems/PDF-Importer-FreeCAD"] = "2026-10-09T12:00:00Z"
        self.assertNotEqual(first, self.run_sync())

    def test_unreadable_previous_file_is_replaced(self) -> None:
        (self.cwd / "repo-metadata.json").write_text("{not json", encoding="utf-8")
        written = self.run_sync()
        self.assertIn(b'"repos"', written)

    def test_private_repo_is_refused(self) -> None:
        self.github.private["BlueCollar-Systems/PDF-Importer-Blender"] = True
        with self.assertRaises(SystemExit) as ctx:
            self.run_sync()
        self.assertIn("BlueCollar-Systems/PDF-Importer-Blender", str(ctx.exception))
        self.assertFalse((self.cwd / "repo-metadata.json").exists())


if __name__ == "__main__":
    unittest.main()
