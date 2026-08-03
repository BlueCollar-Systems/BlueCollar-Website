from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
