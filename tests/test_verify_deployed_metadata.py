from __future__ import annotations

import contextlib
import copy
import hashlib
import http.client
import http.server
import importlib.util
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_deployed_metadata", ROOT / "tools" / "verify_deployed_metadata.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)

SNAPSHOT = {
    "generated_at": "2026-09-16T20:00:00Z",
    "repos": {
        "BlueCollar-Systems/PDF-Importer-Blender": {
            "latest_release": {
                "tag": "v1.0.97", "target_commitish": "a" * 40,
                "immutable": True,
                "assets": [{
                    "name": "Blender-PDF-Importer_v1.0.97.zip",
                    "url": "https://example.invalid/releases/v1.0.97/importer.zip",
                    "digest": "sha256:" + "b" * 64,
                }],
            }
        }
    },
}
EXPECTED = json.dumps(SNAPSHOT).encode()


class Response(io.BytesIO):
    def __init__(self, body: bytes, status: int = 200):
        super().__init__(body)
        self.status = status

    def getcode(self):
        return self.status


class DeployedMetadataTests(unittest.TestCase):
    def setUp(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.stdout))
        self.enterContext(contextlib.redirect_stderr(self.stderr))

    def test_matching_snapshot_passes_with_uncached_request(self):
        opener = Mock(return_value=Response(EXPECTED))
        digest = VERIFY.verify_deployed_metadata(EXPECTED, opener=opener)
        self.assertEqual(digest, hashlib.sha256(EXPECTED).hexdigest())
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Cache-control"), "no-cache, no-store")
        self.assertEqual(request.get_header("Pragma"), "no-cache")
        self.assertIn("Mozilla/5.0", request.get_header("User-agent"))
        self.assertIn("publication_check=", request.full_url)
        self.assertIn("Verified public download metadata", self.stdout.getvalue())

    def test_stale_or_changed_release_identity_never_passes(self):
        mutations = {
            "version": lambda x: x.update(tag="v1.0.96"),
            "source": lambda x: x.update(target_commitish="c" * 40),
            "digest": lambda x: x["assets"][0].update(digest="sha256:" + "d" * 64),
            "download_url": lambda x: x["assets"][0].update(url="https://example.invalid/old.zip"),
            "immutability": lambda x: x.update(immutable=False),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(SNAPSHOT)
                mutate(changed["repos"]["BlueCollar-Systems/PDF-Importer-Blender"]["latest_release"])
                opener = Mock(return_value=Response(json.dumps(changed).encode()))
                with self.assertRaises(VERIFY.MetadataVerificationError):
                    VERIFY.verify_deployed_metadata(EXPECTED, opener=opener, attempts=1)
        self.assertNotIn("Verified", self.stdout.getvalue())

    def test_prior_snapshot_timestamp_alone_is_still_stale(self):
        changed = copy.deepcopy(SNAPSHOT)
        changed["generated_at"] = "2026-09-15T20:00:00Z"
        with self.assertRaises(VERIFY.MetadataVerificationError):
            VERIFY.verify_deployed_metadata(
                EXPECTED, opener=Mock(return_value=Response(json.dumps(changed).encode())), attempts=1,
            )

    def test_retries_propagation_with_unique_queries_then_passes(self):
        opener = Mock(side_effect=[Response(b"stale"), Response(EXPECTED)])
        sleep = Mock()
        VERIFY.verify_deployed_metadata(
            EXPECTED, "https://example.invalid/repo-metadata.json?existing=1",
            opener=opener, sleep=sleep, attempts=3, delay=2,
        )
        self.assertEqual(opener.call_count, 2)
        sleep.assert_called_once_with(2)
        urls = [call.args[0].full_url for call in opener.call_args_list]
        self.assertNotEqual(urls[0], urls[1])
        self.assertTrue(all(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["existing"] == ["1"] for url in urls))

    def test_http_failure_can_recover_within_retry_budget(self):
        error = urllib.error.HTTPError(VERIFY.DEFAULT_URL, 503, "Unavailable", {}, None)
        opener = Mock(side_effect=[error, Response(EXPECTED)])
        VERIFY.verify_deployed_metadata(EXPECTED, opener=opener, sleep=Mock(), attempts=2)
        self.assertEqual(opener.call_count, 2)

    def test_network_protocol_and_http_errors_exhaust_budget_without_success(self):
        errors = [
            urllib.error.URLError("unreachable"),
            TimeoutError("timed out"),
            http.client.IncompleteRead(b"partial"),
            urllib.error.HTTPError(VERIFY.DEFAULT_URL, 403, "Forbidden", {}, None),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                opener = Mock(side_effect=error)
                sleep = Mock()
                with self.assertRaises(VERIFY.MetadataVerificationError):
                    VERIFY.verify_deployed_metadata(EXPECTED, opener=opener, sleep=sleep, attempts=2)
                self.assertEqual(opener.call_count, 2)
                sleep.assert_called_once_with(10)
        self.assertNotIn("Verified", self.stdout.getvalue())

    def test_bad_status_or_error_body_cannot_look_like_success(self):
        for body, status in [(EXPECTED, 201), (b"<html>Access denied</html>", 200), (b"{}", 200), (EXPECTED + b"extra", 200)]:
            with self.subTest(status=status, body=body[:15]):
                with self.assertRaises(VERIFY.MetadataVerificationError):
                    VERIFY.verify_deployed_metadata(EXPECTED, opener=Mock(return_value=Response(body, status)), attempts=1)
        self.assertNotIn("Verified", self.stdout.getvalue())

    def test_invalid_expected_file_or_retry_options_fail_before_request(self):
        opener = Mock()
        for expected in (b"not json", b"[]", b"{}", b'{"repos":{}}'):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                VERIFY.verify_deployed_metadata(expected, opener=opener)
        for options in ({"attempts": 0}, {"delay": -1}, {"timeout": 0}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                VERIFY.verify_deployed_metadata(EXPECTED, opener=opener, **options)
        opener.assert_not_called()

    def test_cli_returns_nonzero_on_failed_public_check(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "repo-metadata.json"
            expected.write_bytes(EXPECTED)
            with patch.object(VERIFY.urllib.request, "urlopen", side_effect=urllib.error.URLError("unreachable")):
                result = VERIFY.main(["--expected", str(expected), "--attempts", "1"])
        self.assertEqual(result, 1)
        self.assertIn("Deployment verification failed", self.stderr.getvalue())
        self.assertNotIn("Verified", self.stdout.getvalue())

    def test_cli_follows_canonical_redirect_and_checks_real_http_body(self):
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                if self.path.startswith("/metadata?"):
                    self.send_response(302)
                    self.send_header("Location", "/published/repo-metadata.json")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(EXPECTED)))
                    self.end_headers()
                    self.wfile.write(EXPECTED)

            def log_message(self, *_args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                expected = Path(directory) / "repo-metadata.json"
                expected.write_bytes(EXPECTED)
                result = VERIFY.main([
                    "--expected", str(expected), "--attempts", "1",
                    "--url", f"http://127.0.0.1:{server.server_port}/metadata",
                ])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(result, 0)
        self.assertEqual(len(requests), 2)
        self.assertIn("publication_check=", requests[0])
        self.assertEqual(requests[1], "/published/repo-metadata.json")

    def test_workflow_only_commits_badges_after_live_verification(self):
        workflow = (ROOT / ".github" / "workflows" / "website-ci.yml").read_text()
        validation = workflow.index("- name: Validate final immutable release metadata")
        deployment = workflow.index("npx --yes wrangler@")
        verification = workflow.index("- name: Verify public download metadata")
        commit = workflow.index("- name: Commit stamped version badges back to repo")
        self.assertLess(validation, deployment)
        self.assertLess(deployment, verification)
        self.assertLess(verification, commit)
        self.assertNotIn("continue-on-error", workflow[verification:commit])
        self.assertNotIn("if: always()", workflow[verification:commit])


if __name__ == "__main__":
    unittest.main()
