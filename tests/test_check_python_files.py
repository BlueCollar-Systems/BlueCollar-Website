"""Regression tests for tools/check_python_files.py (website-ci static-checks).

A tracked Python cache can run in place of the reviewed .py source, and a
module or package named after a standard module at the repository root, in
tools/ or in tests/ is imported in place of the standard library by any
Python started without -I. The check refuses both; the release deploy guard
(tools/check_metadata_only_deploy.py) keeps its own copy of the same rule,
and these tests keep the two the same.
"""

from __future__ import annotations

import importlib.util
import os
import py_compile
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_python_files.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A temporary folder on a drive that records no file owner (FAT, exFAT) makes
# git refuse the throwaway repositories as "dubious ownership". Trust them for
# this test process only (environment config, nothing is written anywhere).
_count = int(os.environ.get("GIT_CONFIG_COUNT", "0") or 0)
os.environ[f"GIT_CONFIG_KEY_{_count}"] = "safe.directory"
os.environ[f"GIT_CONFIG_VALUE_{_count}"] = "*"
os.environ["GIT_CONFIG_COUNT"] = str(_count + 1)

CHECK = _load("check_python_files")
GUARD = _load("check_metadata_only_deploy")

# The marker module: records that it was imported (and with which secret in
# sight), then fails.
MARKER_BODY = (
    "import os as _os\n"
    "with open(_os.environ['SHADOW_MARKER'], 'a', encoding='utf-8') as _f:\n"
    "    _f.write(__name__ + '\\n')\n"
    "raise ImportError('shadow module ' + __name__ + ' was imported')\n"
)

REFUSED = {
    "json.py": "module in the repository root named after the standard module json",
    "site.py": "standard module site",
    "sitecustomize.py": "standard module sitecustomize",
    "urllib/__init__.py": "inside urllib/, a package in the repository root named after the standard module urllib",
    "email/mime/text.py": "inside email/, a package",
    "http.cpython-312-x86_64-linux-gnu.so": "standard module http",
    "tools/json.py": "a module in tools/ named after the standard module json",
    "tools/filecmp.pyw": "standard module filecmp",
    "tools/urllib/request.py": "inside tools/urllib/, a package in tools/",
    "tests/unittest.py": "a module in tests/ named after the standard module unittest",
    "tools/__pycache__/sync_repo_metadata.cpython-312.pyc": "Python bytecode is never committed",
    "tools/__pycache__/notes.txt": "Python bytecode is never committed",
    "docs/helper.pyc": "Python bytecode is never committed",
    "old.PYO": "Python bytecode is never committed",
}
ALLOWED = [
    "index.html", "repo_context_builder_core.py", "0build_master_output_1BlueCollar-Website.py",
    "tools/build_site.py", "tools/sync_repo_metadata.py", "tools/windows-test-bundle/build.mjs",
    "tests/test_build_site.py", "tests/fixtures/report_doctor/parts_bootstrap_importer.json",
    "email/welcome.html",          # a folder of non-Python files is no package
    "docs/json.py",                # docs/ is never on the import path
    "p-records/demo-part.json", "json.md", "JSON.py",  # import names are case-sensitive
    "tools/json.txt", "tests/fixtures/json.py",
]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Check Test", "-c", "user.email=check@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "safe.directory=*", *args],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _remove_tree(path: Path) -> None:
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


class RuleTests(unittest.TestCase):
    def test_each_hazard_is_named_once_and_nothing_else_is(self) -> None:
        found = CHECK.problems([*REFUSED, *ALLOWED])
        self.assertEqual(len(found), len(REFUSED), "\n".join(found))
        for path, reason in REFUSED.items():
            with self.subTest(path=path):
                lines = [line for line in found if line.startswith(path + ": ")]
                self.assertEqual(len(lines), 1, found)
                self.assertIn(reason, lines[0])
        for path in ALLOWED:
            self.assertFalse([line for line in found if line.startswith(path + ": ")], path)

    def test_the_guard_applies_the_same_rule(self) -> None:
        # The guard imports nothing from the repository it judges, so it
        # keeps its own copy of the rule. The copies must agree.
        listed = [*REFUSED, *ALLOWED, *CHECK.tracked_files(ROOT)]
        self.assertEqual(GUARD.python_file_problems(listed), CHECK.problems(listed))
        for name in ("IMPORT_PATH_FOLDERS", "BYTECODE_SUFFIXES", "MODULE_SUFFIXES", "STARTUP_HOOKS"):
            self.assertEqual(getattr(GUARD, name), getattr(CHECK, name), name)
        self.assertEqual(GUARD._shadowed_names(), CHECK.shadowed_names())

    def test_this_repository_passes(self) -> None:
        result = subprocess.run([sys.executable, "-I", "-B", str(TOOL)], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No tracked Python caches or standard-library module names", result.stdout)


class CommandLineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="python-files-test-"))
        self.addCleanup(_remove_tree, self.temp)
        self.repo = self.temp / "repo"
        (self.repo / "tools").mkdir(parents=True)
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "core.autocrlf", "false")
        shutil.copyfile(TOOL, self.repo / "tools" / "check_python_files.py")
        (self.repo / "index.html").write_text("<!DOCTYPE html>\n", encoding="utf-8", newline="\n")
        (self.repo / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8", newline="\n")
        self.marker = self.temp / "imported.txt"

    def run_check(self) -> subprocess.CompletedProcess:
        """As website-ci runs it: from the checkout, its own tools/ copy, -I -B."""
        env = {name: value for name, value in os.environ.items() if not name.startswith("PYTHON")}
        env["SHADOW_MARKER"] = str(self.marker)
        return subprocess.run([sys.executable, "-I", "-B", "tools/check_python_files.py"], cwd=str(self.repo),
                              env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=120)

    def test_clean_checkout_passes(self) -> None:
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "clean")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_root_json_urllib_and_tracked_cache_are_refused_without_being_imported(self) -> None:
        # The review's cases: a root json.py, a root urllib/ package, a
        # tools/ module named after a standard one, and a committed
        # tools/__pycache__ .pyc (force-added past .gitignore). Each is named;
        # none of them is imported by the check itself.
        for name in ("json.py", "tools/json.py", "tools/subprocess.py", "tools/argparse.py"):
            (self.repo / name).write_text(MARKER_BODY, encoding="utf-8", newline="\n")
        (self.repo / "urllib").mkdir()
        (self.repo / "urllib" / "__init__.py").write_text(MARKER_BODY, encoding="utf-8", newline="\n")
        source = self.temp / "sync_repo_metadata.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        cache = self.repo / "tools" / "__pycache__" / "sync_repo_metadata.cpython-312.pyc"
        cache.parent.mkdir()
        py_compile.compile(str(source), cfile=str(cache), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        _git(self.repo, "add", "-A")
        _git(self.repo, "add", "-f", str(cache.relative_to(self.repo)))
        _git(self.repo, "commit", "-q", "-m", "hazards")
        result = self.run_check()
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        for path in ("json.py", "tools/json.py", "tools/subprocess.py", "tools/argparse.py", "urllib/__init__.py",
                     "tools/__pycache__/sync_repo_metadata.cpython-312.pyc"):
            self.assertIn(f"  {path}: ", output)
        self.assertFalse(self.marker.exists(), self.marker.read_text(encoding="utf-8") if self.marker.exists() else "")
        self.assertNotIn("Traceback", output)

    def test_untracked_caches_do_not_count(self) -> None:
        # Only what is committed reaches CI; a developer's own caches do not.
        (self.repo / "tools" / "__pycache__").mkdir()
        (self.repo / "tools" / "__pycache__" / "x.cpython-312.pyc").write_bytes(b"\0")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "clean")
        self.assertEqual(self.run_check().returncode, 0)

    def test_not_a_checkout_is_exit_2(self) -> None:
        outside = self.temp / "not-a-repo"
        outside.mkdir()
        result = subprocess.run([sys.executable, "-I", "-B", str(TOOL), "--root", str(outside)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                                env={**os.environ, "GIT_CEILING_DIRECTORIES": str(self.temp)})
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Could not list the tracked files", result.stdout)


if __name__ == "__main__":
    unittest.main()
