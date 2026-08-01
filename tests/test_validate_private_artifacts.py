from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tools" / "validate_private_artifacts.py"


class PrivateArtifactGuardTests(unittest.TestCase):
    def _run_guard(self, files: dict[str, bytes]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(
                ["git", "init", "--quiet", str(repo)],
                check=True,
                capture_output=True,
            )
            for name, content in files.items():
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            subprocess.run(
                ["git", "-C", str(repo), "add", "--all"],
                check=True,
                capture_output=True,
            )
            return subprocess.run(
                [sys.executable, str(GUARD), "--root", str(repo)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_accepts_normal_website_files(self) -> None:
        result = self._run_guard(
            {
                "index.html": b"<!doctype html><title>Safe</title>",
                "favicon.png": b"\x89PNG\r\n\x1a\n",
            }
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_cad_or_pdf_filename_extensions(self) -> None:
        for filename in ("artifact.pdf", "drawing.dxf", "model.skp", "part.FCStd"):
            with self.subTest(filename=filename):
                result = self._run_guard({filename: b"placeholder"})
                self.assertEqual(result.returncode, 1)
                self.assertIn("forbidden artifact extension", result.stdout)

    def test_rejects_extensionless_pdf_by_content_signature(self) -> None:
        result = self._run_guard(
            {"artifact": b"\xef\xbb\xbf \r\n%PDF-1.7\r\n%binary payload"}
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("PDF content signature", result.stdout)

    def test_rejects_extensionless_cad_by_content_signature(self) -> None:
        signatures = {
            "ascii-dxf": b"0\r\nSECTION\r\n2\r\nHEADER\r\n9\r\n$ACADVER\r\n1\r\nAC1032\r\n",
            "binary-dxf": b"AutoCAD Binary DXF\r\n\x1a\x00",
            "dwg": b"AC1032\x00binary",
            "sketchup": b"SketchUp Model\x00binary",
            "blender": b"BLENDER-v300",
        }
        for filename, content in signatures.items():
            with self.subTest(filename=filename):
                result = self._run_guard({filename: content})
                self.assertEqual(result.returncode, 1)
                self.assertIn("content signature", result.stdout)

    def test_rejects_extensionless_freecad_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "artifact"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("Document.xml", "<Document SchemaVersion=\"4\"/>")
                bundle.writestr("GuiDocument.xml", "<GuiDocument/>")
            result = self._run_guard({"artifact": archive.read_bytes()})

        self.assertEqual(result.returncode, 1)
        self.assertIn("FreeCAD content signature", result.stdout)

    def test_rejects_pdf_or_cad_nested_in_generic_zip(self) -> None:
        fixtures = {
            "named": ("evidence/drawing.dxf", b"placeholder"),
            "extensionless": ("evidence/artifact", b"%PDF-1.7\nprivate"),
        }
        for case, (member, content) in fixtures.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "bundle.zip"
                with zipfile.ZipFile(archive, "w") as bundle:
                    bundle.writestr(member, content)
                result = self._run_guard({"bundle.zip": archive.read_bytes()})

            self.assertEqual(result.returncode, 1)
            self.assertIn("archive contains", result.stdout)


if __name__ == "__main__":
    unittest.main()
