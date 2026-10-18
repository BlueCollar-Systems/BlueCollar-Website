"""Regression tests for tools/check_release_drift.py (no network)."""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_release_drift", ROOT / "tools" / "check_release_drift.py")
assert SPEC is not None and SPEC.loader is not None
DRIFT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIFT)
SYNC = DRIFT.sync

SKETCHUP = "BlueCollar-Systems/PDF-Importer-SketchUp"
FREECAD = "BlueCollar-Systems/PDF-Importer-FreeCAD"
BLENDER = "BlueCollar-Systems/PDF-Importer-Blender"
LIBRECAD = "BlueCollar-Systems/PDF-Importer-LibreCAD"
NOW = dt.datetime(2026, 10, 18, 12, 0, tzinfo=dt.UTC)


def _iso(moment: dt.datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _gh_release(repo: str, tag: str, published: dt.datetime, *, draft: bool = False,
                prerelease: bool = False, digest: str = "a") -> dict:
    """A release as the GitHub /releases API lists it."""
    name = f"{repo.rsplit('-', 1)[-1]}-PDF-Importer_{tag}.zip"
    return {
        "tag_name": tag,
        "name": tag,
        "html_url": f"https://github.com/{repo}/releases/tag/{tag}",
        "published_at": _iso(published),
        "target_commitish": "1" * 40,
        "immutable": True,
        "draft": draft,
        "prerelease": prerelease,
        "assets": [{
            "name": name,
            "browser_download_url": f"https://github.com/{repo}/releases/download/{tag}/{name}",
            "size": 100,
            "content_type": "application/zip",
            "digest": "sha256:" + digest * 64,
        }],
    }


class World:
    """GitHub releases plus the live metadata a deploy made from them."""

    def __init__(self) -> None:
        week_ago = NOW - dt.timedelta(days=7)
        self.releases: dict[str, list[dict]] = {
            SKETCHUP: [
                _gh_release(SKETCHUP, "v3.7.166", week_ago),
                _gh_release(SKETCHUP, "steel-v1.0.2", week_ago - dt.timedelta(days=20)),
            ],
            FREECAD: [
                _gh_release(FREECAD, "v4.0.115", week_ago),
                _gh_release(FREECAD, "steel-v1.0.1", week_ago - dt.timedelta(days=20)),
            ],
            BLENDER: [_gh_release(BLENDER, "v1.0.111", week_ago)],
            LIBRECAD: [_gh_release(LIBRECAD, "v1.0.108", week_ago)],
        }
        self.live = self.deploy(week_ago + dt.timedelta(minutes=10))

    def deploy(self, when: dt.datetime) -> dict:
        """The metadata tools/sync_repo_metadata.py would publish now."""
        repos = {}
        for repo in SYNC.REPOS:
            importer = SYNC.final_tagged_releases(self.releases[repo], "v")
            steel = SYNC.final_tagged_releases(self.releases[repo], "steel-v")
            repos[repo] = {
                "error": None,
                "latest_release": SYNC._release_summary(importer[0]) if importer else None,
                "steel_release": (
                    SYNC._release_summary(steel[0])
                    if steel and repo in SYNC.STEEL_RELEASE_REPOS else None
                ),
            }
        return {"generated_at": when.isoformat(), "repos": repos}

    def publish(self, repo: str, tag: str, hours_ago: float, **kwargs) -> None:
        self.releases[repo].insert(0, _gh_release(repo, tag, NOW - dt.timedelta(hours=hours_ago), **kwargs))

    def evaluate(self, grace: float = 24):
        return DRIFT.evaluate(self.live, copy.deepcopy(self.releases), NOW, grace)


def _result(results, repo: str, channel: str = "importer"):
    matches = [r for r in results if r.repo == repo and r.channel == channel]
    assert len(matches) == 1, (repo, channel, results)
    return matches[0]


class CompareTests(unittest.TestCase):
    def test_site_in_sync_is_green(self) -> None:
        code, report, results = World().evaluate()
        self.assertEqual(code, DRIFT.EXIT_IN_SYNC)
        self.assertTrue(all(r.in_sync for r in results))
        self.assertIn(DRIFT.ISSUE_MARKER, report)
        self.assertIn("offers the latest GitHub release of every importer", report)
        self.assertNotIn("How to fix", report)

    def test_checks_every_importer_and_only_the_shape_pack_repos(self) -> None:
        _, _, results = World().evaluate()
        self.assertEqual(
            [(r.repo, r.channel) for r in results],
            [
                (SKETCHUP, "importer"), (SKETCHUP, "shape pack"),
                (FREECAD, "importer"), (FREECAD, "shape pack"),
                (BLENDER, "importer"), (LIBRECAD, "importer"),
            ],
        )

    def test_release_behind_for_less_than_a_day_only_warns(self) -> None:
        world = World()
        world.publish(BLENDER, "v1.0.112", hours_ago=2)
        code, report, results = world.evaluate()
        blender = _result(results, BLENDER)
        self.assertEqual(code, DRIFT.EXIT_IN_SYNC)
        self.assertFalse(blender.in_sync)
        self.assertFalse(blender.is_stale(NOW, 24))
        self.assertAlmostEqual(blender.age_hours(NOW), 2)
        self.assertIn("within grace", report)
        self.assertIn("less than 24 hours", report)

    def test_release_behind_for_more_than_a_day_is_red(self) -> None:
        world = World()
        world.publish(FREECAD, "v4.0.116", hours_ago=30)
        code, report, results = world.evaluate()
        freecad = _result(results, FREECAD)
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertEqual((freecad.live_tag, freecad.github_tag), ("v4.0.115", "v4.0.116"))
        self.assertEqual(freecad.behind_since, NOW - dt.timedelta(hours=30))
        self.assertIn("| PDF-Importer-FreeCAD | importer | v4.0.115 | v4.0.116 | 30 h | STALE", report)
        self.assertIn("deploy_production", report)
        self.assertTrue(_result(results, FREECAD, "shape pack").in_sync)

    def test_age_counts_from_the_first_release_the_site_missed(self) -> None:
        # The newest release is an hour old, but the site has lacked the one
        # before it for three days: that is stale, not "1 hour behind".
        world = World()
        world.publish(BLENDER, "v1.0.112", hours_ago=72)
        world.publish(BLENDER, "v1.0.113", hours_ago=1)
        code, report, results = world.evaluate()
        blender = _result(results, BLENDER)
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertEqual(blender.github_tag, "v1.0.113")
        self.assertEqual(blender.behind_since, NOW - dt.timedelta(hours=72))
        self.assertIn("2 newer releases on GitHub", report)
        self.assertIn("3.0 days", report)

    def test_drafts_and_prereleases_are_not_drift(self) -> None:
        world = World()
        world.publish(LIBRECAD, "v1.0.109", hours_ago=48, draft=True)
        world.publish(LIBRECAD, "v1.0.110", hours_ago=48, prerelease=True)
        code, _, results = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_IN_SYNC)
        self.assertTrue(_result(results, LIBRECAD).in_sync)

    def test_shape_pack_release_drift_is_reported(self) -> None:
        world = World()
        world.publish(SKETCHUP, "steel-v1.0.3", hours_ago=26)
        code, report, results = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_STALE)
        steel = _result(results, SKETCHUP, "shape pack")
        self.assertEqual((steel.live_tag, steel.github_tag), ("steel-v1.0.2", "steel-v1.0.3"))
        # A steel release is newest in the listing, but the importer channel
        # still compares v* releases only.
        self.assertTrue(_result(results, SKETCHUP).in_sync)
        self.assertIn("| PDF-Importer-SketchUp | shape pack | steel-v1.0.2 | steel-v1.0.3 |", report)

    def test_shape_pack_drift_asks_for_the_manual_deploy(self) -> None:
        # A steel pack release is published with GITHUB_TOKEN, so no dispatch
        # deploys the site; the report must not promise a release deploy.
        world = World()
        world.publish(FREECAD, "steel-v1.0.2", hours_ago=3)
        _, report, _ = world.evaluate()
        self.assertIn("A shape pack (`steel-v*`) release needs the manual deploy", report)
        self.assertIn("`GITHUB_TOKEN`", report)
        self.assertIn("`deploy_production` set to true", report)
        importer_only = World()
        importer_only.publish(BLENDER, "v1.0.112", hours_ago=3)
        self.assertNotIn("needs the manual deploy", importer_only.evaluate()[1])

    def test_stale_marker_is_only_in_a_report_that_found_stale_downloads(self) -> None:
        world = World()
        self.assertNotIn(DRIFT.STALE_MARKER, world.evaluate()[1])
        world.publish(BLENDER, "v1.0.112", hours_ago=3)
        self.assertNotIn(DRIFT.STALE_MARKER, world.evaluate()[1])  # within grace
        world.publish(BLENDER, "v1.0.113", hours_ago=30)
        code, report, _ = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertEqual(report.splitlines()[:2], [DRIFT.ISSUE_MARKER, DRIFT.STALE_MARKER])

    def test_deleted_live_release_fails_at_once(self) -> None:
        world = World()
        world.publish(SKETCHUP, "v3.7.167", hours_ago=1)
        world.live = world.deploy(NOW - dt.timedelta(minutes=30))
        del world.releases[SKETCHUP][0]  # v3.7.167 withdrawn after the deploy
        code, report, results = world.evaluate()
        sketchup = _result(results, SKETCHUP)
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertIsNone(sketchup.age_hours(NOW))
        self.assertIn("no longer a published GitHub release", report)
        self.assertIn("no grace (fix now)", report)

    def test_live_release_older_than_a_full_listing_fails_at_once(self) -> None:
        world = World()
        for number in range(100):
            world.publish(FREECAD, f"v4.1.{number}", hours_ago=200 - number)
        code, _, results = world.evaluate()
        freecad = _result(results, FREECAD)
        self.assertEqual(code, DRIFT.EXIT_STALE)
        world.releases[FREECAD] = world.releases[FREECAD][:100]  # what one API page holds
        results = world.evaluate()[2]
        self.assertIn("not among the 100 newest GitHub releases", _result(results, FREECAD).note)
        self.assertIsNone(_result(results, FREECAD).age_hours(NOW))
        self.assertEqual(freecad.behind_since, NOW - dt.timedelta(hours=200))

    def test_release_turned_back_into_prerelease_fails_at_once(self) -> None:
        world = World()
        world.publish(BLENDER, "v1.0.112", hours_ago=1)
        world.live = world.deploy(NOW - dt.timedelta(minutes=30))
        world.releases[BLENDER][0]["prerelease"] = True
        code, _, results = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertEqual(_result(results, BLENDER).github_tag, "v1.0.111")

    def test_changed_download_file_under_the_same_tag_is_drift(self) -> None:
        world = World()
        world.releases[LIBRECAD][0]["assets"][0]["digest"] = "sha256:" + "b" * 64
        code, report, results = world.evaluate()
        librecad = _result(results, LIBRECAD)
        self.assertEqual(code, DRIFT.EXIT_STALE)  # published a week ago
        self.assertIn("download files differ", librecad.note)

    def test_asset_order_alone_is_not_drift(self) -> None:
        world = World()
        extra = dict(world.releases[FREECAD][0]["assets"][0], name="FreeCAD-PDF-Importer_v4.0.115.attestation.json",
                     browser_download_url="https://example.invalid/attestation.json")
        world.releases[FREECAD][0]["assets"].append(extra)
        world.live = world.deploy(NOW - dt.timedelta(days=1))
        world.releases[FREECAD][0]["assets"].reverse()
        code, _, results = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_IN_SYNC)
        self.assertTrue(_result(results, FREECAD).in_sync)

    def test_repo_missing_from_live_metadata_is_stale(self) -> None:
        world = World()
        del world.live["repos"][LIBRECAD]
        code, report, _ = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertIn("missing from the live metadata", report)

    def test_first_release_of_a_channel_gets_the_grace_period(self) -> None:
        world = World()
        world.releases[BLENDER] = []
        world.live = world.deploy(NOW - dt.timedelta(hours=5))
        world.publish(BLENDER, "v1.0.1", hours_ago=3)
        code, _, results = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_IN_SYNC)
        self.assertAlmostEqual(_result(results, BLENDER).age_hours(NOW), 3)
        world.publish(BLENDER, "v1.0.2", hours_ago=1)
        self.assertEqual(world.evaluate(grace=2)[0], DRIFT.EXIT_STALE)

    def test_channel_without_any_github_release_is_not_drift(self) -> None:
        world = World()
        world.releases[BLENDER] = []
        code, _, results = world.evaluate()
        self.assertEqual(code, DRIFT.EXIT_IN_SYNC)
        self.assertIn("no published GitHub release", _result(results, BLENDER).note)

    def test_snapshot_of_2026_10_12_against_the_releases_of_2026_10_14_is_red(self) -> None:
        # The real gap this check exists for: the site kept v1.0.109 /
        # v4.0.114 / v1.0.107 / v3.7.164 for days after newer releases.
        world = World()
        published = {
            BLENDER: [("v1.0.111", "2026-10-14T01:48:43Z"), ("v1.0.110", "2026-10-13T22:37:16Z"),
                      ("v1.0.109", "2026-10-12T03:40:03Z")],
            FREECAD: [("v4.0.115", "2026-10-14T01:49:11Z"), ("v4.0.114", "2026-10-12T11:41:57Z")],
            LIBRECAD: [("v1.0.108", "2026-10-14T02:39:12Z"), ("v1.0.107", "2026-10-12T03:37:53Z")],
            SKETCHUP: [("v3.7.166", "2026-10-13T22:37:37Z"), ("v3.7.165", "2026-10-12T22:22:31Z"),
                       ("v3.7.164", "2026-10-11T18:06:48Z")],
        }
        for repo, tags in published.items():
            steel = [r for r in world.releases[repo] if r["tag_name"].startswith("steel-v")]
            world.releases[repo] = [
                _gh_release(repo, tag, dt.datetime.fromisoformat(when.replace("Z", "+00:00")))
                for tag, when in tags
            ] + steel
        current = world.releases
        world.releases = {repo: [r for r in rels if r["tag_name"] not in
                                 {"v1.0.111", "v1.0.110", "v4.0.115", "v1.0.108", "v3.7.166", "v3.7.165"}]
                          for repo, rels in current.items()}
        world.live = world.deploy(dt.datetime(2026, 10, 12, 12, 2, 8, tzinfo=dt.UTC))
        world.releases = current
        code, report, results = DRIFT.evaluate(world.live, current, dt.datetime(2026, 10, 17, 12, 0, tzinfo=dt.UTC), 24)
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertEqual(
            {r.repo: (r.live_tag, r.github_tag) for r in results if r.channel == "importer"},
            {BLENDER: ("v1.0.109", "v1.0.111"), FREECAD: ("v4.0.114", "v4.0.115"),
             LIBRECAD: ("v1.0.107", "v1.0.108"), SKETCHUP: ("v3.7.164", "v3.7.166")},
        )
        self.assertEqual(_result(results, SKETCHUP).behind_since.isoformat(), "2026-10-12T22:22:31+00:00")
        self.assertEqual(report.count("STALE"), 4)


OTHER = "BlueCollar-Systems/Other-Tool"


class SharedSelectionRuleTests(unittest.TestCase):
    """The drift check and the deploy's sync pick a release by one rule."""

    def test_drift_reads_the_channel_rule_from_the_sync_tool(self) -> None:
        self.assertEqual(DRIFT.channels(SKETCHUP), [
            ("latest_release", SYNC.IMPORTER_TAG_PREFIX, "importer"),
            ("steel_release", SYNC.STEEL_TAG_PREFIX, "shape pack"),
        ])
        self.assertEqual(DRIFT.channels(BLENDER), [("latest_release", "v", "importer")])
        self.assertIsNone(SYNC.importer_tag_prefix(OTHER))
        with patch.object(SYNC, "importer_tag_prefix", lambda repo: "x-"):
            self.assertEqual(DRIFT.channels(BLENDER)[0][1], "x-")

    def world_with_other_repo(self) -> tuple[World, dict]:
        world = World()
        world.releases[OTHER] = [
            _gh_release(OTHER, "2.1.0", NOW - dt.timedelta(days=5)),
            _gh_release(OTHER, "v1.0.0", NOW - dt.timedelta(days=60)),
        ]
        return world, {OTHER: world.releases[OTHER][0]}

    def fake_github(self, world: World, latest: dict):
        def fake_get(url, token=None):
            repo = url.split("/repos/", 1)[1]
            if url == SYNC.releases_url(repo.split("/releases", 1)[0]):
                return world.releases[repo.split("/releases", 1)[0]]
            if url.endswith("/releases/latest"):
                repo = repo[: -len("/releases/latest")]
                if latest.get(repo) is None:
                    raise urllib.error.HTTPError(url, 404, "not found", {}, None)
                return latest[repo]
            return {"default_branch": "main", "pushed_at": _iso(NOW), "html_url": f"https://github.com/{repo}",
                    "private": False}
        return fake_get

    def test_repo_outside_the_importers_follows_releases_latest_in_both_tools(self) -> None:
        # The sync publishes GitHub's /releases/latest for a repo outside
        # PDF_IMPORTER_RELEASE_REPOS, whatever its tag looks like. The drift
        # check used to apply the importers' "v" rule to every repo and would
        # call this live 2.1.0 "no longer a published GitHub release".
        world, latest = self.world_with_other_repo()
        fake_get = self.fake_github(world, latest)
        with patch.object(SYNC, "REPOS", (*SYNC.REPOS, OTHER)), patch.object(SYNC, "_json_get", fake_get):
            live = SYNC.build_metadata(None)
            self.assertEqual(live["repos"][OTHER]["latest_release"]["tag"], "2.1.0")
            fetched_latest = DRIFT.fetch_latest_releases(None)
            self.assertEqual(set(fetched_latest), {OTHER})
            code, _, results = DRIFT.evaluate(live, world.releases, NOW, 24, latest_by_repo=fetched_latest)
            self.assertEqual(code, DRIFT.EXIT_IN_SYNC, results)
            self.assertTrue(_result(results, OTHER).in_sync)

            # A newer release 30 hours old: stale, and dated from it.
            world.releases[OTHER].insert(0, _gh_release(OTHER, "2.2.0", NOW - dt.timedelta(hours=30)))
            latest[OTHER] = world.releases[OTHER][0]
            code, _, results = DRIFT.evaluate(live, world.releases, NOW, 24,
                                              latest_by_repo=DRIFT.fetch_latest_releases(None))
        other = _result(results, OTHER)
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertEqual((other.live_tag, other.github_tag), ("2.1.0", "2.2.0"))
        self.assertEqual(other.behind_since, NOW - dt.timedelta(hours=30))

    def test_repo_without_a_latest_release_is_not_drift(self) -> None:
        world, _ = self.world_with_other_repo()
        with patch.object(SYNC, "REPOS", (*SYNC.REPOS, OTHER)), \
                patch.object(SYNC, "_json_get", self.fake_github(world, {OTHER: None})):
            latest = DRIFT.fetch_latest_releases(None)
            self.assertEqual(latest, {OTHER: None})
            live = world.live
            live["repos"][OTHER] = {"latest_release": None}
            _, _, results = DRIFT.evaluate(live, world.releases, NOW, 24, latest_by_repo=latest)
        self.assertTrue(_result(results, OTHER).in_sync)

    def test_importer_repos_never_ask_for_releases_latest(self) -> None:
        def fake_get(url, token=None):
            raise AssertionError(f"unexpected call {url}")

        with patch.object(SYNC, "_json_get", fake_get):
            self.assertEqual(DRIFT.fetch_latest_releases(None), {})


class _Response:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body, self.status = body, status

    def getcode(self) -> int:
        return self.status

    def read(self, size: int = -1) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


class FetchTests(unittest.TestCase):
    def test_live_metadata_bypasses_caches_with_a_unique_query(self) -> None:
        seen = []

        def opener(request, timeout):
            seen.append(request)
            return _Response(json.dumps(World().live).encode())

        payload = DRIFT.fetch_live_metadata("https://example.invalid/repo-metadata.json?a=1", opener=opener)
        self.assertIn(BLENDER, payload["repos"])
        self.assertIn("a=1", seen[0].full_url)
        self.assertIn("drift_check=", seen[0].full_url)
        self.assertEqual(seen[0].get_header("Cache-control"), "no-cache, no-store")

    def test_live_metadata_retries_then_gives_up_clearly(self) -> None:
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(request.full_url, 503, "busy", {}, None)
            return _Response(b"<html>not json</html>")

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(DRIFT.CheckError):
                DRIFT.fetch_live_metadata(opener=opener, attempts=3, sleep=lambda _: None)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(set(calls)), 3)

    def test_github_listing_uses_the_sync_tool_url_and_token(self) -> None:
        world = World()
        calls = []

        def fake_get(url, token=None):
            calls.append((url, token))
            repo = url.split("/repos/", 1)[1].split("/releases", 1)[0]
            return world.releases[repo]

        with patch.object(SYNC, "_json_get", fake_get):
            releases = DRIFT.fetch_releases("t0ken")
        self.assertEqual(set(releases), set(SYNC.REPOS))
        self.assertEqual(calls[0], (SYNC.releases_url(SYNC.REPOS[0]), "t0ken"))

    def test_github_error_is_a_check_error(self) -> None:
        def fake_get(url, token=None):
            raise urllib.error.HTTPError(url, 403, "rate limited", {}, None)

        with patch.object(SYNC, "_json_get", fake_get):
            with self.assertRaises(DRIFT.CheckError):
                DRIFT.fetch_releases(None)


class MainTests(unittest.TestCase):
    def run_main(self, world: World | None, *extra: str) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "drift.md"
            stdout = io.StringIO()
            if world is None:
                fetch = patch.object(DRIFT, "fetch_live_metadata", side_effect=DRIFT.CheckError("site down"))
            else:
                fetch = patch.object(DRIFT, "fetch_live_metadata", return_value=world.live)
            releases = copy.deepcopy(world.releases) if world else {}
            with fetch, patch.object(DRIFT, "fetch_releases", return_value=releases), \
                    contextlib.redirect_stdout(stdout):
                code = DRIFT.main(["--report", str(report), "--now", _iso(NOW), *extra])
            return code, report.read_text(encoding="utf-8"), stdout.getvalue()

    def test_exit_codes_and_annotations(self) -> None:
        world = World()
        self.assertEqual(self.run_main(world)[0], 0)

        world.publish(BLENDER, "v1.0.112", hours_ago=3)
        code, report, out = self.run_main(world)
        self.assertEqual(code, 0)
        self.assertIn("::warning::PDF-Importer-Blender importer downloads are behind", out)

        code, report, out = self.run_main(world, "--grace-hours", "2")
        self.assertEqual(code, 1)
        self.assertIn("::error::PDF-Importer-Blender importer downloads are stale", out)
        self.assertTrue(report.startswith(DRIFT.ISSUE_MARKER))

    def test_unreachable_site_is_status_2_with_a_report(self) -> None:
        code, report, out = self.run_main(None)
        self.assertEqual(code, DRIFT.EXIT_UNCHECKED)
        self.assertIn("could not run", report)
        self.assertIn("site down", out)
        self.assertNotIn(DRIFT.STALE_MARKER, report)

    def test_unexpected_error_is_status_2_never_stale(self) -> None:
        # An uncaught exception used to exit 1, which the workflow reads as
        # stale downloads. Now it is "could not check", with the error shown.
        world = World()
        world.publish(BLENDER, "v1.0.112", hours_ago=30)  # really stale, too
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "drift.md"
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(DRIFT, "fetch_live_metadata", return_value=world.live), \
                    patch.object(DRIFT, "fetch_releases", return_value=copy.deepcopy(world.releases)), \
                    patch.object(DRIFT, "evaluate", side_effect=KeyError("tag")), \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = DRIFT.main(["--report", str(report), "--now", _iso(NOW)])
            text = report.read_text(encoding="utf-8")
        self.assertEqual(code, DRIFT.EXIT_UNCHECKED)
        self.assertIn("unexpected error in check_release_drift.py: KeyError", stdout.getvalue())
        self.assertIn("Traceback", stderr.getvalue())
        self.assertTrue(text.startswith(DRIFT.ISSUE_MARKER))
        self.assertIn("This is not a drift finding", text)
        self.assertNotIn(DRIFT.STALE_MARKER, text)

    def test_shape_pack_annotation_names_the_manual_deploy(self) -> None:
        world = World()
        world.publish(SKETCHUP, "steel-v1.0.3", hours_ago=30)
        code, report, out = self.run_main(world)
        self.assertEqual(code, DRIFT.EXIT_STALE)
        self.assertIn("::error::PDF-Importer-SketchUp shape pack downloads are stale", out)
        self.assertIn("shape pack releases need the manual deploy (deploy_production=true)", out)
        self.assertIn(DRIFT.STALE_MARKER, report)


if __name__ == "__main__":
    unittest.main()
