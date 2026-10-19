#!/usr/bin/env python3
"""Refuse tracked Python caches and modules named after standard modules.

website-ci runs this repository's Python tools inside the deploy job, some of
them while a token is in their environment. Two kinds of tracked file could
make such a run execute something other than the reviewed .py source without
anyone meaning it to, so neither may be committed:

1. Python bytecode: anything in a __pycache__/ folder, and any *.pyc or *.pyo
   file. Python reads tools/__pycache__/<name>.cpython-*.pyc instead of
   tools/<name>.py whenever the cache says the source need not be checked (an
   "unchecked-hash" .pyc), and -B only stops Python writing caches, not
   reading them.
2. A module or package named after a standard-library module
   (sys.stdlib_module_names, plus the sitecustomize and usercustomize startup
   hooks) in a folder Python puts first on its import path when it runs this
   repository's code without -I: the repository root ("python -" and
   "python -c" run there), tools/ ("python tools/<x>.py") and tests/
   ("python tests/<x>.py"). A json.py, a json.*.so or a urllib/ package there
   is imported in place of the real one. A folder counts as a package when it
   holds any Python file; a folder of other files (email/welcome.html) is fine.

website-ci starts every Python with -I, which already keeps these folders off
the import path. This check makes such a file fail the pull request instead of
waiting for a run without -I. tools/check_metadata_only_deploy.py applies the
same rule to every commit it rebuilds (it imports nothing from the repository,
so it keeps its own copy; tests/test_check_python_files.py keeps the two the
same).

Usage, from anywhere:
    python -I -B tools/check_python_files.py [--root <checkout>]

Exit codes: 0 none found, 1 found (each file is named), 2 the tracked files
could not be listed.
"""

import argparse
import subprocess
import sys
from pathlib import Path, PurePosixPath

# Folders Python puts on sys.path when this repository's code runs without -I.
IMPORT_PATH_FOLDERS = ("", "tools", "tests")
BYTECODE_SUFFIXES = (".pyc", ".pyo")
# Files Python imports a module from: source, bytecode and extension modules.
MODULE_SUFFIXES = (".py", ".pyw", ".pyc", ".pyo", ".pyd", ".so")
STARTUP_HOOKS = ("sitecustomize", "usercustomize")


def shadowed_names() -> frozenset:
    """Module names a repository file must never take."""
    names = getattr(sys, "stdlib_module_names", None)
    if not names:
        raise SystemExit("check_python_files.py needs Python 3.10 or newer (sys.stdlib_module_names).")
    return frozenset(names) | frozenset(STARTUP_HOOKS)


def _is_module_file(name: str) -> bool:
    return name.lower().endswith(MODULE_SUFFIXES)


def problems(paths, names=None) -> list:
    """One line per tracked path (POSIX, relative to the root) that is refused."""
    names = shadowed_names() if names is None else names
    found = []
    for path in sorted(set(paths)):
        parts = PurePosixPath(path).parts
        if not parts:
            continue
        if "__pycache__" in parts or path.lower().endswith(BYTECODE_SUFFIXES):
            found.append(f"{path}: Python bytecode is never committed; Python can run it instead of the .py source")
            continue
        for folder in IMPORT_PATH_FOLDERS:
            if folder and parts[0] != folder:
                continue
            inside = parts[1:] if folder else parts
            if not inside:
                continue
            where = f"{folder}/" if folder else "the repository root"
            if len(inside) == 1:
                module = inside[0].split(".", 1)[0]
                if _is_module_file(inside[0]) and module in names:
                    found.append(f"{path}: a module in {where} named after the standard module {module}")
                    break
            elif inside[0] in names and _is_module_file(inside[-1]):
                found.append(f"{path}: inside {'/'.join(parts[:len(parts) - len(inside) + 1])}/, a package in "
                             f"{where} named after the standard module {inside[0]}")
                break
    return found


def tracked_files(root: Path) -> list:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached"],
        check=False, capture_output=True, timeout=60,
    )
    if result.returncode != 0:
        raise OSError(result.stderr.decode("utf-8", "replace").strip() or f"git ls-files exit {result.returncode}")
    return [name for name in result.stdout.decode("utf-8", "surrogateescape").split("\0") if name]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="the checkout to check (default: this script's repository)")
    args = parser.parse_args(argv)
    try:
        listed = tracked_files(args.root)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"::error::Could not list the tracked files of {args.root}: {exc}")
        return 2
    found = problems(listed)
    if found:
        print("::error::Tracked Python files that could run in place of reviewed code or the standard "
              "library. Delete them (git rm --cached for caches; rename the modules):")
        for line in found:
            print(f"  {line}")
        return 1
    print(f"No tracked Python caches or standard-library module names ({len(listed)} tracked files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
