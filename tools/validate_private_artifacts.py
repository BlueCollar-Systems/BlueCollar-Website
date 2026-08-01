#!/usr/bin/env python3
"""Fail when tracked website files contain PDF or CAD artifacts."""

from __future__ import annotations

import argparse
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath


FORBIDDEN_SUFFIXES = frozenset(
    {".pdf", ".dxf", ".dwg", ".skp", ".fcstd", ".fcstd1", ".blend", ".blend1"}
)
_DWG_SIGNATURE = re.compile(br"^AC10\d{2}")


def _tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [
        root / value.decode("utf-8", errors="surrogateescape")
        for value in result.stdout.split(b"\0")
        if value
    ]


def _raw_content_signature(head: bytes) -> str | None:
    normalized = head.replace(b"\r\n", b"\n")
    pdf_head = head.removeprefix(b"\xef\xbb\xbf").lstrip()
    if pdf_head.startswith(b"%PDF-"):
        return "PDF content signature"
    if head.startswith(b"AutoCAD Binary DXF"):
        return "binary DXF content signature"
    if b"\nSECTION\n" in normalized and b"\n$ACADVER\n" in normalized:
        return "ASCII DXF content signature"
    if _DWG_SIGNATURE.match(head):
        return "DWG content signature"
    if head.startswith(b"SketchUp Model"):
        return "SketchUp content signature"
    if head.startswith(b"BLENDER"):
        return "Blender content signature"
    return None


def _content_signature(path: Path) -> str | None:
    with path.open("rb") as stream:
        head = stream.read(65_536)

    signature = _raw_content_signature(head)
    if signature:
        return signature
    if head.startswith(b"PK") and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            if any(member.filename == "Document.xml" for member in members):
                return "FreeCAD content signature"
            for member in members:
                suffix = PurePosixPath(member.filename).suffix.lower()
                if suffix in FORBIDDEN_SUFFIXES:
                    return "archive contains forbidden PDF/CAD artifact extension"
                with archive.open(member) as stream:
                    nested_head = stream.read(65_536)
                nested_signature = _raw_content_signature(nested_head)
                if nested_signature:
                    return f"archive contains {nested_signature}"
    return None


def find_forbidden_artifacts(root: Path) -> list[tuple[Path, str]]:
    failures: list[tuple[Path, str]] = []
    for path in _tracked_paths(root):
        relative = path.relative_to(root)
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append((relative, "forbidden artifact extension"))
            continue
        if not path.is_file() or path.is_symlink():
            continue
        try:
            signature = _content_signature(path)
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            failures.append((relative, f"could not safely inspect file: {exc}"))
            continue
        if signature:
            failures.append((relative, signature))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    failures = find_forbidden_artifacts(root)
    if failures:
        print("Private PDF/CAD artifact guard failed:")
        for path, reason in failures:
            print(f"  {path}: {reason}")
        return 1
    print("Private PDF/CAD artifact guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
