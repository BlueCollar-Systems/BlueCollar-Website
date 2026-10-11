#!/usr/bin/env python3
"""Copy only the public website files into _site/ for Cloudflare Pages.

Cloudflare Pages publishes every file in the folder it is given, and it does
not read .cfignore. Deploying the repository root therefore put build
scripts, CI workflows, tests and internal notes on bluecollar-systems.com.
This script builds a clean _site/ folder from an explicit allowlist, refuses
to finish if a repository-only file slipped in, and checks that every link,
image, script and fetch() target on the site resolves inside _site/ using the
same rules Cloudflare Pages uses (/feedback -> feedback.html, /p/<id> ->
p/index.html through _redirects, trailing / -> index.html).

ADDING A PUBLIC FILE: anything new the site must serve has to be added to
ALLOWED_FILES or ALLOWED_DIRS below, or it will 404 in production. That
includes a future app-ads.txt (root file) or .well-known/assetlinks.json
(already covered by the .well-known/ directory entry, but keep it in mind).

Standard library only. Usage:
    python tools/build_site.py [--source .] [--out _site]
"""

from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

SITE_ORIGIN = "https://bluecollar-systems.com"
OWN_HOSTS = frozenset({"bluecollar-systems.com", "www.bluecollar-systems.com"})

# Every *.html page and *.css stylesheet in the repository root is public
# (a page-specific stylesheet such as part-page.css ships without a list edit).
ALLOWED_GLOBS: tuple[str, ...] = ("*.html", "*.css")

# Individual public files in the repository root. Keep this list explicit:
# a file that is not listed here is not published.
ALLOWED_FILES: tuple[str, ...] = (
    "styles.css",
    "nav.js",
    "part-resolver.js",
    "report-doctor.js",
    "favicon.ico",
    "favicon.svg",
    "og-image.png",
    "robots.txt",
    "sitemap.xml",
    "repo-metadata.json",
    "_headers",
    "_redirects",
    # Add future root files here, for example "app-ads.txt".
)

# Public directories, copied whole. A future .well-known/assetlinks.json is
# published through the .well-known entry.
ALLOWED_DIRS: tuple[str, ...] = (
    ".well-known",
    "p",
    "p-records",
)

# Operating-system and cache junk that is never copied out of ALLOWED_DIRS.
_IGNORED_JUNK = shutil.ignore_patterns(
    ".DS_Store", "Thumbs.db", "Desktop.ini", "__pycache__", "*.pyc", "*~", "*.swp"
)

# Repository-only files that must never reach the public site.
FORBIDDEN_SUFFIXES = frozenset(
    {".py", ".pyc", ".md", ".yml", ".yaml", ".cmd", ".bat", ".ps1", ".sh", ".toml", ".lock"}
)
FORBIDDEN_NAMES = frozenset(
    {"LICENSE", "VERSION", ".gitignore", ".gitattributes", ".cfignore", ".pre-commit-config.yaml"}
)

_SKIPPED_SCHEMES = ("mailto:", "tel:", "data:", "javascript:")
_FETCH_LITERAL = re.compile(r"""fetch\(\s*(['"])(/[^'"]*)\1\s*(\+)?""")
_CSS_URL = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""")
_OWN_URL_IN_TEXT = re.compile(r"https://(?:www\.)?bluecollar-systems\.com(?:/[^\s<>\"']*)?")
_TEXT_FILES_WITH_URLS = ("robots.txt", "sitemap.xml", ".well-known/security.txt")


class BuildError(RuntimeError):
    """The public site folder could not be built safely."""


# ---------------------------------------------------------------------------
# Cloudflare Pages path rules (shared with tools/check_public_links.py)
# ---------------------------------------------------------------------------

def load_redirects(site_root: Path) -> list[tuple[str, str, int]]:
    """Parse _redirects into (source, destination, status) rules.

    Supports the forms this site uses: exact sources and a trailing ``*``
    splat, with ``:splat`` substitution in the destination.
    """
    path = Path(site_root) / "_redirects"
    rules: list[tuple[str, str, int]] = []
    if not path.is_file():
        return rules
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        status = 302
        if len(parts) >= 3 and parts[2].rstrip("!").isdigit():
            status = int(parts[2].rstrip("!"))
        rules.append((parts[0], parts[1], status))
    return rules


def _match_redirect(url_path: str, rules: list[tuple[str, str, int]]) -> tuple[str, int] | None:
    for source, destination, status in rules:
        if source.endswith("*"):
            prefix = source[:-1]
            if url_path.startswith(prefix):
                splat = url_path[len(prefix):]
                return destination.replace(":splat", splat), status
        elif url_path == source:
            return destination, status
    return None


def _normalise_url_path(url_path: str) -> str | None:
    path = unquote(urlsplit(url_path).path or "/")
    if not path.startswith("/"):
        return None
    trailing = path.endswith("/")
    normalised = posixpath.normpath(path)
    if normalised.startswith("//"):
        normalised = "/" + normalised.lstrip("/")
    if trailing and normalised != "/":
        normalised += "/"
    if ".." in normalised.split("/"):
        return None
    return normalised


def _static_lookup(site_root: Path, url_path: str) -> str | None:
    """Return the file Pages serves for a path, as a POSIX path, or None."""
    rel = url_path.lstrip("/")
    root = Path(site_root)

    def is_file(candidate: str) -> bool:
        return bool(candidate) and (root / candidate).is_file()

    if url_path.endswith("/"):
        if is_file(rel + "index.html"):
            return rel + "index.html"
        # Pages redirects /x/ to /x when only x.html exists.
        if rel and is_file(rel.rstrip("/") + ".html"):
            return rel.rstrip("/") + ".html"
        return None
    if is_file(rel):
        return rel
    if is_file(rel + ".html"):
        return rel + ".html"
    # Pages redirects /x to /x/ when x/index.html exists.
    if is_file(rel + "/index.html"):
        return rel + "/index.html"
    return None


def resolve_site_path(
    site_root: Path,
    url_path: str,
    redirects: list[tuple[str, str, int]] | None = None,
    _depth: int = 0,
) -> str | None:
    """Resolve a site path the way Cloudflare Pages serves it.

    Returns the POSIX path of the file that would be served (relative to
    site_root), the absolute URL of an off-site redirect, or None when the
    request would 404. _redirects rules run before static lookup, as they do
    on Pages.
    """
    if redirects is None:
        redirects = load_redirects(site_root)
    path = _normalise_url_path(url_path)
    if path is None or _depth > 5:
        return None
    match = _match_redirect(path, redirects)
    if match is not None:
        destination, status = match
        if destination.startswith(("http://", "https://")):
            parsed = urlsplit(destination)
            if parsed.hostname not in OWN_HOSTS:
                return destination
            destination = parsed.path or "/"
        if status == 200:
            # A rewrite serves the destination's asset without another
            # round of redirect rules.
            dest = _normalise_url_path(destination)
            return _static_lookup(site_root, dest) if dest else None
        return resolve_site_path(site_root, destination, redirects, _depth + 1)
    return _static_lookup(site_root, path)


def page_route(rel_path: str) -> str:
    """The URL path a page is served at (index.html -> /, x.html -> /x)."""
    rel = rel_path.replace("\\", "/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    if rel.endswith(".html"):
        return "/" + rel[: -len(".html")]
    return "/" + rel


# ---------------------------------------------------------------------------
# Reference collection
# ---------------------------------------------------------------------------

class _ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for name in ("href", "src"):
            value = values.get(name)
            if value is not None:
                self.references.append(value.strip())
        srcset = values.get("srcset")
        if srcset:
            for candidate in srcset.split(","):
                url = candidate.strip().split(" ")[0]
                if url:
                    self.references.append(url)
        # Link previews (og:image, twitter:image) point at our own domain.
        if tag == "meta":
            content = (values.get("content") or "").strip()
            if _OWN_URL_IN_TEXT.fullmatch(content):
                self.references.append(content)



def html_references(html: str) -> list[str]:
    """Every href, src, srcset entry and own-domain meta URL in a page."""
    parser = _ReferenceParser()
    parser.feed(html)
    parser.close()
    return parser.references


def classify_reference(page_url_path: str, reference: str) -> tuple[str, str] | None:
    """Turn a raw reference into ("site", path) or ("external", url).

    Returns None for references that are not fetched from a server
    (#fragments, mailto:, tel:, data:, javascript:, empty values).
    """
    ref = reference.strip()
    if not ref or ref.startswith("#") or ref.lower().startswith(_SKIPPED_SCHEMES):
        return None
    absolute = urljoin(SITE_ORIGIN + page_url_path, ref)
    parsed = urlsplit(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    if parsed.hostname in OWN_HOSTS:
        return ("site", parsed.path or "/")
    return ("external", absolute)


def _site_files(site_root: Path, suffix: str) -> list[Path]:
    return sorted(p for p in Path(site_root).rglob(f"*{suffix}") if p.is_file())


def collect_site_references(site_root: Path) -> list[tuple[str, str]]:
    """(source file, raw reference) pairs for HTML, CSS, JS fetch and text files."""
    root = Path(site_root)
    found: list[tuple[str, str]] = []
    for page in _site_files(root, ".html"):
        rel = page.relative_to(root).as_posix()
        for ref in html_references(page.read_text(encoding="utf-8")):
            found.append((rel, ref))
    for sheet in _site_files(root, ".css"):
        rel = sheet.relative_to(root).as_posix()
        for match in _CSS_URL.finditer(sheet.read_text(encoding="utf-8")):
            found.append((rel, match.group(2).strip()))
    for name in _TEXT_FILES_WITH_URLS:
        path = root / name
        if path.is_file():
            for match in _OWN_URL_IN_TEXT.finditer(path.read_text(encoding="utf-8")):
                found.append((name, match.group(0)))
    return found


def check_references(site_root: Path) -> list[str]:
    """Return a problem line for each on-site reference that would 404."""
    root = Path(site_root)
    redirects = load_redirects(root)
    problems: list[str] = []
    for source, ref in collect_site_references(root):
        base = page_route(source) if source.endswith(".html") else "/"
        kind = classify_reference(base, ref)
        if kind is None or kind[0] != "site":
            continue
        if resolve_site_path(root, kind[1], redirects) is None:
            problems.append(f"{source}: {ref} -> {kind[1]} is not in the published site")
    for script in _site_files(root, ".js"):
        rel = script.relative_to(root).as_posix()
        for match in _FETCH_LITERAL.finditer(script.read_text(encoding="utf-8")):
            target, is_prefix = match.group(2), bool(match.group(3))
            if is_prefix:
                # fetch('/p-records/' + id + '.json'): the folder must ship.
                folder = target if target.endswith("/") else posixpath.dirname(target) + "/"
                if not (root / folder.lstrip("/")).is_dir():
                    problems.append(f"{rel}: fetch('{target}' + ...) needs folder {folder} in the published site")
            elif resolve_site_path(root, target, redirects) is None:
                problems.append(f"{rel}: fetch('{target}') is not in the published site")
    return problems


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def forbidden_files(site_root: Path) -> list[str]:
    root = Path(site_root)
    bad = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and (path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name in FORBIDDEN_NAMES):
            bad.append(path.relative_to(root).as_posix())
    return bad


# Files every finished build leaves in its folder. An existing folder must
# hold all of them (and no repository-only files) before it may be wiped.
_BUILD_SIGNATURE: tuple[str, ...] = ("index.html", "_headers", "_redirects", "repo-metadata.json", "nav.js")
DEFAULT_OUT = "_site"


def _looks_like_earlier_build(out: Path) -> bool:
    return all((out / name).is_file() for name in _BUILD_SIGNATURE) and not forbidden_files(out)


def _check_output_location(source: Path, out: Path) -> None:
    """Refuse an output folder whose wipe could destroy anything but a build.

    The folder is deleted and rebuilt, so it must be missing, empty, the
    git-ignored default <source>/_site, or the result of an earlier build
    (its usual files present and no repository-only file such as .py, .md
    or .yml). A mistyped --out such as docs, tools or .github is refused.
    """
    if out == source or source.is_relative_to(out):
        raise BuildError(f"Refusing to build into {out}: it would delete the source folder.")
    if out.exists() and not out.is_dir():
        raise BuildError(f"Refusing to build into {out}: it is not a plain folder.")
    if (out / ".git").exists():
        raise BuildError(f"Refusing to build into {out}: it contains a .git folder.")
    if not out.exists() or not any(out.iterdir()):
        return
    if out == source / DEFAULT_OUT:
        return
    if not _looks_like_earlier_build(out):
        raise BuildError(
            f"Refusing to build into {out}: it already holds files that build_site.py did not make, "
            f"and building there would delete them. Use --out {DEFAULT_OUT} (the default), "
            "a new or empty folder, or delete the folder yourself first."
        )


def build_site(source: Path, out: Path) -> list[str]:
    """Build the public folder. Returns the published files (POSIX paths)."""
    source = Path(source).resolve()
    out = Path(out).resolve()
    _check_output_location(source, out)

    missing = [name for name in ALLOWED_FILES if not (source / name).is_file()]
    missing += [name + "/" for name in ALLOWED_DIRS if not (source / name).is_dir()]
    if missing:
        raise BuildError(
            "Listed public files are missing from the repository: " + ", ".join(missing)
            + ". Restore them or update the list in tools/build_site.py."
        )

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for pattern in ALLOWED_GLOBS:
        for path in sorted(source.glob(pattern)):
            if path.is_file():
                shutil.copy2(path, out / path.name)
    for name in ALLOWED_FILES:
        shutil.copy2(source / name, out / name)
    for name in ALLOWED_DIRS:
        shutil.copytree(source / name, out / name, ignore=_IGNORED_JUNK)

    leaked = forbidden_files(out)
    if leaked:
        raise BuildError(
            "Repository-only files would be published: " + ", ".join(leaked)
            + ". Move them out of the public folders."
        )

    problems = check_references(out)
    if problems:
        raise BuildError(
            "Links point at files that would not be published:\n  " + "\n  ".join(problems)
        )

    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=Path("."), help="repository root (default: .)")
    parser.add_argument(
        "--out", type=Path, default=Path(DEFAULT_OUT),
        help="output folder, deleted and rebuilt; must be new, empty, _site or an earlier build "
             "(default: _site)",
    )
    args = parser.parse_args(argv)
    try:
        files = build_site(args.source, args.out)
    except BuildError as exc:
        print(f"Site build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built {args.out} with {len(files)} public files; every on-site link resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
