"""The public link check finds dead links the way a stranger (no login) sees them."""

from __future__ import annotations

import contextlib
import http.server
import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_public_links", ROOT / "tools" / "check_public_links.py")
assert SPEC is not None and SPEC.loader is not None
LINKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINKS)

PORTABLE = "LibreCAD-PDF-Importer-Windows-Portable_v1.0.104.zip"
PLAIN = "LibreCAD-PDF-Importer_v1.0.104.zip"
METADATA = {
    "repos": {
        "BlueCollar-Systems/PDF-Importer-LibreCAD": {
            "repo_url": "https://example.invalid/librecad",
            "latest_release": {
                "tag": "v1.0.104",
                "url": "https://example.invalid/librecad/releases/tag/v1.0.104",
                "assets": [
                    {"name": PLAIN, "url": "https://example.invalid/dl/" + PLAIN},
                    {"name": PORTABLE, "url": "https://example.invalid/dl/" + PORTABLE},
                ],
            },
        },
        "BlueCollar-Systems/PDF-Importer-SketchUp": {
            "repo_url": "https://example.invalid/sketchup",
            "latest_release": {"tag": "v3.7.1", "url": "https://example.invalid/su/v3.7.1", "assets": []},
            "steel_release": {
                "tag": "steel-v1.0.2",
                "url": "https://example.invalid/su/steel-v1.0.2",
                "assets": [
                    {"name": "SHA256SUMS.txt", "url": "https://example.invalid/dl/SHA256SUMS.txt"},
                    {"name": "Structural-Steel-SU-Shapes-latest.zip",
                     "url": "https://example.invalid/dl/Structural-Steel-SU-Shapes-latest.zip"},
                ],
            },
        },
    }
}
INDEX = """<!DOCTYPE html><html><head>
<link rel="stylesheet" href="/styles.css"><link rel="canonical" href="https://bluecollar-systems.com/">
</head><body>
<a href="#main">skip</a> <a href="mailto:support@example.invalid">mail</a> <a href="tel:5550100">call</a>
<a href="/feedback">feedback</a> <a href="https://example.invalid/outside">outside</a>
<a href="https://example.invalid/librecad/releases/latest" data-repo-asset-link="BlueCollar-Systems/PDF-Importer-LibreCAD">Download</a>
<a href="https://example.invalid/librecad" data-repo-release-link="BlueCollar-Systems/PDF-Importer-LibreCAD">Notes</a>
<a href="https://example.invalid/su/releases" data-repo-asset-link="BlueCollar-Systems/PDF-Importer-SketchUp"
   data-release-channel="steel" data-asset-name="Structural-Steel-SU-Shapes-latest.zip">ZIP</a>
<script src="/nav.js"></script>
</body></html>"""


class Response(io.BytesIO):
    def __init__(self, status: int = 206):
        super().__init__(b"x")
        self.status = status

    def getcode(self):
        return self.status


def fake_opener(statuses: dict[str, int] | None = None, default: int = 206):
    statuses = statuses or {}
    calls: list = []

    def opener(request, timeout=None):
        calls.append(request)
        status = statuses.get(request.full_url, default)
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, None)
        return Response(status)

    opener.calls = calls
    return opener


class PublicLinkCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "index.html").write_text(INDEX, encoding="utf-8")
        (self.root / "feedback.html").write_text('<a href="/">home</a>', encoding="utf-8")
        (self.root / "styles.css").write_text("body{}", encoding="utf-8")
        (self.root / "nav.js").write_text("", encoding="utf-8")
        (self.root / "p").mkdir()
        (self.root / "p" / "index.html").write_text('<script src="/part-resolver.js"></script>', encoding="utf-8")
        (self.root / "part-resolver.js").write_text("", encoding="utf-8")
        (self.root / "_redirects").write_text("/p/* /p/ 200\n", encoding="utf-8")
        (self.root / "repo-metadata.json").write_text(json.dumps(METADATA), encoding="utf-8")
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.stdout))
        self.enterContext(contextlib.redirect_stderr(self.stderr))

    # -- single URL ---------------------------------------------------------

    def test_stubbed_404_fails_and_206_passes(self):
        ok, result = LINKS.check_url("https://example.invalid/a", opener=fake_opener(default=404), sleep=Mock())
        self.assertFalse(ok)
        self.assertEqual(result, "HTTP 404")
        ok, result = LINKS.check_url("https://example.invalid/a", opener=fake_opener(default=206), sleep=Mock())
        self.assertTrue(ok)
        self.assertEqual(result, "HTTP 206")

    def test_request_is_anonymous_and_ranged(self):
        opener = fake_opener()
        with patch.dict(os.environ, {"GH_TOKEN": "not-a-real-token", "GITHUB_TOKEN": "not-a-real-token"}):
            LINKS.check_url("https://example.invalid/a", opener=opener, sleep=Mock())
        request = opener.calls[0]
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.get_header("Range"), "bytes=0-0")

    def test_one_retry_after_a_network_error(self):
        opener = Mock(side_effect=[urllib.error.URLError("reset"), Response(206)])
        sleep = Mock()
        ok, _ = LINKS.check_url("https://example.invalid/a", opener=opener, sleep=sleep)
        self.assertTrue(ok)
        self.assertEqual(opener.call_count, 2)
        sleep.assert_called_once()
        opener = Mock(side_effect=urllib.error.URLError("down"))
        ok, result = LINKS.check_url("https://example.invalid/a", opener=opener, sleep=Mock())
        self.assertFalse(ok)
        self.assertIn("network error", result)
        self.assertEqual(opener.call_count, 2)

    def test_redirect_ending_in_200_passes(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/old":
                    self.send_response(302)
                    self.send_header("Location", "/sign-in")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                elif self.path == "/sign-in":
                    self.send_response(200)
                    self.send_header("Content-Length", "2")
                    self.end_headers()
                    self.wfile.write(b"ok")
                else:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

            def log_message(self, *_args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            self.assertEqual(LINKS.check_url(base + "/old", sleep=Mock()), (True, "HTTP 200"))
            self.assertEqual(LINKS.check_url(base + "/gone", sleep=Mock()), (False, "HTTP 404"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    # -- nav.js download picks ----------------------------------------------

    def test_asset_picker_prefers_librecad_portable_zip(self):
        assets = METADATA["repos"]["BlueCollar-Systems/PDF-Importer-LibreCAD"]["latest_release"]["assets"]
        self.assertEqual(LINKS.find_download_asset(assets)["name"], PORTABLE)
        self.assertEqual(LINKS.find_download_asset(list(reversed(assets)))["name"], PORTABLE)
        setup = {"name": "FreeCAD-PDF-Importer-Setup_v4.0.111.exe"}
        zip_ = {"name": "FreeCAD-PDF-Importer_v4.0.111.zip"}
        self.assertIs(LINKS.find_download_asset([zip_, setup]), setup)
        self.assertIsNone(LINKS.find_download_asset([zip_], "Missing.zip"))
        self.assertEqual(LINKS.find_download_asset([{"name": "notes.txt"}, {"name": "x.apk"}])["name"], "x.apk")

    def test_python_picker_mirrors_nav_js_rules(self):
        nav = (ROOT / "nav.js").read_text(encoding="utf-8")
        for pattern in LINKS._PRIMARY_ASSET_PATTERNS:
            self.assertIn(pattern.pattern, nav, "nav.js asset rules changed; update check_public_links.py")
        for pattern in (LINKS._SETUP_EXE, LINKS._LIBRECAD_PORTABLE, LINKS._LIBRECAD_PLAIN_ZIP):
            self.assertIn(pattern.pattern, nav, "nav.js asset rank changed; update check_public_links.py")
        self.assertIn("['.rbz', '.zip', '.aab', '.apk']", nav)

    def test_nav_js_links_follow_buttons_on_the_page(self):
        links = dict((url, what) for what, url in LINKS.nav_js_links(INDEX, METADATA))
        self.assertIn("https://example.invalid/dl/" + PORTABLE, links)
        self.assertNotIn("https://example.invalid/dl/" + PLAIN, links)
        self.assertIn("https://example.invalid/dl/Structural-Steel-SU-Shapes-latest.zip", links)
        self.assertNotIn("https://example.invalid/dl/SHA256SUMS.txt", links)
        self.assertIn("https://example.invalid/librecad/releases/tag/v1.0.104", links)

    # -- whole site ---------------------------------------------------------

    def test_clean_site_passes_and_skips_mailto_tel_and_fragments(self):
        opener = fake_opener()
        problems, checked = LINKS.run_checks(self.root, opener=opener, sleep=Mock())
        self.assertEqual(problems, [])
        fetched = {request.full_url for request in opener.calls}
        self.assertIn("https://example.invalid/outside", fetched)
        self.assertIn("https://example.invalid/dl/" + PORTABLE, fetched)
        self.assertFalse(any(u.startswith(("mailto:", "tel:")) or "#" in u for u in fetched))
        self.assertFalse(any("bluecollar-systems.com" in u for u in fetched), "on-site links are checked offline")
        self.assertGreater(checked, 5)

    def test_missing_relative_file_fails_offline(self):
        (self.root / "feedback.html").write_text('<img src="/images/missing.png"><a href="/">home</a>', encoding="utf-8")
        opener = Mock()
        problems, _ = LINKS.run_checks(self.root, offline=True, opener=opener)
        self.assertEqual(len(problems), 1)
        self.assertIn("feedback.html", problems[0])
        self.assertIn("/images/missing.png", problems[0])
        opener.assert_not_called()

    def test_dead_external_link_names_page_and_url(self):
        dead = "https://example.invalid/outside"
        problems, _ = LINKS.run_checks(self.root, opener=fake_opener({dead: 404}), sleep=Mock())
        self.assertEqual(problems, [f"BROKEN index.html: {dead} (HTTP 404)"])
        self.assertEqual(LINKS.main(["--root", str(self.root), "--offline"]), 0)

    def test_dead_download_button_is_reported(self):
        dead = "https://example.invalid/dl/" + PORTABLE
        problems, _ = LINKS.run_checks(self.root, opener=fake_opener({dead: 404}), sleep=Mock())
        self.assertEqual(len(problems), 1)
        self.assertIn("download button for BlueCollar-Systems/PDF-Importer-LibreCAD", problems[0])
        self.assertIn(dead, problems[0])

    def test_base_mode_requests_pages_and_on_site_links_from_live_site(self):
        opener = fake_opener({"https://live.example.invalid/feedback": 404})
        problems, _ = LINKS.run_checks(self.root, base="https://live.example.invalid/", opener=opener, sleep=Mock())
        fetched = {request.full_url for request in opener.calls}
        for url in ("https://live.example.invalid/", "https://live.example.invalid/styles.css",
                    "https://live.example.invalid/p/", "https://live.example.invalid/part-resolver.js"):
            self.assertIn(url, fetched)
        self.assertTrue(any("https://live.example.invalid/feedback (HTTP 404)" in p for p in problems))

    def test_known_exception_is_skipped_not_passed(self):
        dead = "https://example.invalid/outside"
        with patch.dict(LINKS.KNOWN_EXCEPTIONS, {dead: "2026-10-10: test entry"}):
            problems, _ = LINKS.run_checks(self.root, opener=fake_opener({dead: 404}), sleep=Mock())
        self.assertEqual(problems, [])
        self.assertIn(f"SKIPPED {dead}", self.stdout.getvalue())

    def test_unreadable_metadata_fails_clearly(self):
        (self.root / "repo-metadata.json").write_text("{", encoding="utf-8")
        self.assertEqual(LINKS.main(["--root", str(self.root), "--offline"]), 1)
        self.assertIn("repo-metadata.json could not be read", self.stderr.getvalue())

    def test_real_checkout_passes_offline(self):
        problems, _ = LINKS.run_checks(ROOT, offline=True)
        self.assertEqual(problems, [])

    def test_workflow_runs_the_check_before_and_after_deploy(self):
        workflow = (ROOT / ".github" / "workflows" / "website-ci.yml").read_text(encoding="utf-8")
        static_job = workflow[workflow.index("static-checks:"):workflow.index("deploy-pages:")]
        self.assertLess(static_job.index("- name: Build repository metadata snapshot"),
                        static_job.index("python tools/check_public_links.py"))
        self.assertIn("python tests/test_check_public_links.py -v", static_job)
        deploy_job = workflow[workflow.index("deploy-pages:"):]
        live_check = deploy_job.index("python tools/check_public_links.py --base https://bluecollar-systems.com")
        self.assertLess(deploy_job.index("- name: Verify public download metadata"), live_check)
        self.assertLess(live_check, deploy_job.index("- name: Commit stamped version badges back to repo"))


if __name__ == "__main__":
    unittest.main()
