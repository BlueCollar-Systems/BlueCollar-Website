"""The deploy folder holds only public website files and every on-site link resolves."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_site", ROOT / "tools" / "build_site.py")
assert SPEC is not None and SPEC.loader is not None
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)

PAGES = ("index.html", "feedback.html", "shapes.html", "report-doctor.html", "privacy.html", "404.html")
REQUIRED = PAGES + (
    "p/index.html",
    "p-records/demo-part.json",
    ".well-known/security.txt",
    "_headers",
    "_redirects",
    "styles.css",
    "nav.js",
    "support-links.js",
    "support-config.json",
    "part-resolver.js",
    "report-doctor.js",
    "favicon.ico",
    "favicon.svg",
    "og-image.png",
    "robots.txt",
    "app-ads.txt",
    "sitemap.xml",
    "repo-metadata.json",
)
NEVER_PUBLISHED = (
    "README.md",
    "CONTRIBUTING.md",
    "RELEASE_CHECKLIST.md",
    "LICENSE",
    "VERSION",
    ".cfignore",
    ".gitignore",
    ".gitattributes",
    ".pre-commit-config.yaml",
    "repo_context_builder_core.py",
    "0build_master_output_1BlueCollar-Website.py",
    "0build_master_output_1BlueCollar-Website.cmd",
    "docs/CLOUDFLARE_PAGES.md",
    "tools/sync_repo_metadata.py",
    "tests/test_build_site.py",
    ".github/workflows/website-ci.yml",
)


class BuildSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="bc-site-"))
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.stdout))
        self.enterContext(contextlib.redirect_stderr(self.stderr))

    def build_real_site(self) -> Path:
        out = self.temp / "_site"
        self.assertEqual(BUILD.main(["--source", str(ROOT), "--out", str(out)]), 0, self.stderr.getvalue())
        return out

    def test_every_public_page_and_asset_is_published(self):
        out = self.build_real_site()
        for rel in REQUIRED:
            with self.subTest(file=rel):
                self.assertTrue((out / rel).is_file(), f"{rel} missing from the deploy folder")
        for page in ROOT.glob("*.html"):
            self.assertTrue((out / page.name).is_file(), f"{page.name} missing from the deploy folder")
        self.assertEqual((out / "repo-metadata.json").read_bytes(), (ROOT / "repo-metadata.json").read_bytes())
        self.assertEqual((out / "support-config.json").read_bytes(), (ROOT / "support-config.json").read_bytes())

    def test_google_authorized_seller_is_published_as_plain_text(self):
        out = self.build_real_site()
        self.assertEqual(
            (out / "app-ads.txt").read_bytes(),
            b"google.com, pub-2053420996629428, DIRECT, f08c47fec0942fa0\n",
        )
        self.assertIn(
            "/app-ads.txt\n  Content-Type: text/plain; charset=utf-8\n"
            "  Cache-Control: public, max-age=300, must-revalidate\n",
            (out / "_headers").read_text(encoding="utf-8"),
        )

    def test_repository_only_files_are_not_published(self):
        out = self.build_real_site()
        for rel in NEVER_PUBLISHED:
            with self.subTest(file=rel):
                self.assertFalse((out / rel).exists(), f"{rel} would be public")
        self.assertEqual(BUILD.forbidden_files(out), [])
        suffixes = {p.suffix.lower() for p in out.rglob("*") if p.is_file()}
        self.assertFalse(suffixes & {".py", ".md", ".yml", ".yaml", ".cmd"}, suffixes)
        self.assertFalse(any(p.name in {"LICENSE", "VERSION"} for p in out.rglob("*")))

    def test_reference_check_passes_on_the_real_site(self):
        out = self.build_real_site()
        self.assertEqual(BUILD.check_references(out), [])
        self.assertIn("every on-site link resolves", self.stdout.getvalue())

    @unittest.skipUnless(shutil.which("node"), "Node is required to test the Windows bundle builder")
    def test_windows_bundle_ships_its_support_assets_and_all_public_references(self):
        # Exercise the real file-copy builder without shipping a runtime in a
        # unit-test temp folder. The actual distributable is built separately
        # with its real Windows Node executable and license.
        runtime = self.temp / "placeholder-runtime"
        runtime.mkdir()
        executable = runtime / "node.exe"
        executable.write_bytes(b"File-copy test placeholder; never execute.\n")
        (runtime / "LICENSE").write_text("File-copy test license placeholder.\n", encoding="utf-8")
        output = self.temp / "windows-bundle"
        builder = ROOT / "tools" / "windows-test-bundle" / "build.mjs"
        bootstrap = """
import { pathToFileURL } from 'node:url';
const [builder, runtime, destination] = process.argv.slice(1);
process.execPath = runtime;
process.argv = [runtime, builder, destination];
await import(pathToFileURL(builder).href);
"""
        result = subprocess.run(
            [shutil.which("node"), "--input-type=module", "-e", bootstrap,
             str(builder), str(executable), str(output)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        public = output / "public"
        self.assertEqual(BUILD.check_references(public), [])
        inventory = {entry["path"]: entry["sha256"] for entry in
                     json.loads((output / "PACKAGE_SHA256.json").read_text(encoding="utf-8"))}
        for name in ("support-links.js", "support-config.json"):
            with self.subTest(file=name):
                data = (public / name).read_bytes()
                self.assertEqual(data, (ROOT / name).read_bytes())
                self.assertEqual(inventory["public/" + name], hashlib.sha256(data).hexdigest())

    def test_pages_rules_match_cloudflare(self):
        out = self.build_real_site()
        expected = {
            "/": "index.html",
            "/shapes": "shapes.html",
            "/report-doctor": "report-doctor.html",
            "/report-doctor.html": "report-doctor.html",
            "/feedback": "feedback.html",
            "/privacy": "privacy.html",
            "/p/demo-part": "p/index.html",
            "/p/": "p/index.html",
            "/p-records/demo-part.json": "p-records/demo-part.json",
            "/repo-metadata.json": "repo-metadata.json",
            "/app-ads.txt": "app-ads.txt",
            "/.well-known/security.txt": ".well-known/security.txt",
            "/security.txt": ".well-known/security.txt",
            "/og-image.png": "og-image.png",
        }
        for path, served in expected.items():
            with self.subTest(path=path):
                self.assertEqual(BUILD.resolve_site_path(out, path), served)
        for path in ("/README.md", "/tools/sync_repo_metadata.py", "/.github/workflows/website-ci.yml",
                     "/docs/CLOUDFLARE_PAGES.md", "/missing", "/../README.md"):
            with self.subTest(path=path):
                self.assertIsNone(BUILD.resolve_site_path(out, path))

    def test_page_with_missing_image_fails_the_build(self):
        source = self.build_real_site()
        (source / "broken.html").write_text(
            '<!DOCTYPE html><title>x</title><img src="/images/missing.png" alt="">', encoding="utf-8"
        )
        result = BUILD.main(["--source", str(source), "--out", str(self.temp / "out2")])
        self.assertEqual(result, 1)
        self.assertIn("broken.html", self.stderr.getvalue())
        self.assertIn("/images/missing.png", self.stderr.getvalue())

    def test_relative_link_and_fetch_targets_are_checked(self):
        source = self.build_real_site()
        (source / "rel.html").write_text('<a href="nowhere.html">x</a>', encoding="utf-8")
        (source / "nav.js").write_text("fetch('/gone.json'); fetch('/no-folder/' + id);", encoding="utf-8")
        with self.assertRaises(BUILD.BuildError) as ctx:
            BUILD.build_site(source, self.temp / "out3")
        message = str(ctx.exception)
        self.assertIn("rel.html: nowhere.html", message)
        self.assertIn("fetch('/gone.json')", message)
        self.assertIn("/no-folder/", message)

    def test_repository_file_inside_a_public_folder_fails_the_build(self):
        source = self.build_real_site()
        (source / "p" / "notes.md").write_text("internal", encoding="utf-8")
        result = BUILD.main(["--source", str(source), "--out", str(self.temp / "out4")])
        self.assertEqual(result, 1)
        self.assertIn("p/notes.md", self.stderr.getvalue())

    def test_missing_listed_file_fails_instead_of_publishing_a_broken_site(self):
        source = self.build_real_site()
        (source / "og-image.png").unlink()
        result = BUILD.main(["--source", str(source), "--out", str(self.temp / "out5")])
        self.assertEqual(result, 1)
        self.assertIn("og-image.png", self.stderr.getvalue())

    def test_refuses_to_wipe_the_source_folder(self):
        # Uses a throwaway copy so a broken guard could never delete the repo.
        source = self.build_real_site()
        with self.assertRaises(BUILD.BuildError):
            BUILD.build_site(source, source)
        with self.assertRaises(BUILD.BuildError):
            BUILD.build_site(source, self.temp)
        (source / "inner").mkdir()
        (source / "inner" / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
        with self.assertRaises(BUILD.BuildError):
            BUILD.build_site(source, source / "inner")
        self.assertTrue((source / "index.html").is_file())

    def test_refuses_a_mistyped_out_folder_inside_the_source(self):
        # A throwaway source copy with tracked-looking folders next to the pages.
        source = self.build_real_site()
        tracked = {
            "docs": "CLOUDFLARE_PAGES.md",
            "tools": "sync_repo_metadata.py",
            ".github/workflows": "website-ci.yml",
            "notes": "plan.txt",
        }
        for folder, name in tracked.items():
            (source / folder).mkdir(parents=True)
            (source / folder / name).write_text("keep me", encoding="utf-8")
        for folder, name in tracked.items():
            top = folder.split("/")[0]
            with self.subTest(out=top):
                self.assertEqual(BUILD.main(["--source", str(source), "--out", str(source / top)]), 1)
                self.assertIn("did not make", self.stderr.getvalue())
                self.assertEqual((source / folder / name).read_text(encoding="utf-8"), "keep me")

    def test_refuses_a_non_empty_folder_that_is_not_a_build(self):
        source = self.build_real_site()
        other = self.temp / "my-files"
        other.mkdir()
        (other / "index.html").write_text("mine", encoding="utf-8")
        (other / "photo.png").write_bytes(b"png")
        with self.assertRaises(BUILD.BuildError):
            BUILD.build_site(source, other)
        self.assertTrue((other / "photo.png").is_file())
        a_file = self.temp / "a-file.txt"
        a_file.write_text("x", encoding="utf-8")
        with self.assertRaises(BUILD.BuildError):
            BUILD.build_site(source, a_file)
        self.assertTrue(a_file.is_file())

    def test_builds_into_new_empty_default_or_earlier_build_folders(self):
        source = self.build_real_site()
        empty = self.temp / "empty"
        empty.mkdir()
        BUILD.build_site(source, empty)
        self.assertTrue((empty / "index.html").is_file())
        BUILD.build_site(source, empty)  # now an earlier build: rebuilt
        BUILD.build_site(source, self.temp / "brand-new" / "site")
        default = source / "_site"
        default.mkdir()
        (default / "leftover.md").write_text("old", encoding="utf-8")
        BUILD.build_site(source, default)  # the git-ignored default is always rebuilt
        self.assertFalse((default / "leftover.md").exists())
        self.assertTrue((default / "index.html").is_file())

    def test_new_root_stylesheet_ships_without_a_list_edit(self):
        source = self.build_real_site()
        (source / "part-page.css").write_text("main{margin:0}", encoding="utf-8")
        (source / "p" / "index.html").write_text(
            '<link rel="stylesheet" href="/part-page.css"><script src="/part-resolver.js"></script>', encoding="utf-8"
        )
        out = self.temp / "out6"
        BUILD.build_site(source, out)
        self.assertTrue((out / "part-page.css").is_file())

    def test_rebuild_removes_stale_files(self):
        out = self.build_real_site()
        (out / "stale.txt").write_text("old", encoding="utf-8")
        self.build_real_site()
        self.assertFalse((out / "stale.txt").exists())

    def test_workflow_deploys_only_the_built_folder(self):
        workflow = (ROOT / ".github" / "workflows" / "website-ci.yml").read_text(encoding="utf-8")
        self.assertFalse("pages deploy . " in workflow, "deploy must not upload the repository root")
        # Wrangler runs from an empty folder outside the checkout (see
        # tests/test_manual_publication_workflow.py), given _site by path.
        self.assertIn('site="$(pwd -P)/_site"', workflow, "deploy must upload the built _site folder")
        self.assertTrue('pages deploy "$site" ' in workflow, "deploy must upload the built _site folder")
        deploy_job = workflow[workflow.index("deploy-pages:"):]
        validation = deploy_job.index("- name: Validate final immutable release metadata")
        build = deploy_job.index("python -I -B tools/build_site.py")
        deployment = deploy_job.index("npx --yes wrangler@")
        self.assertLess(validation, build)
        self.assertLess(build, deployment)
        static_job = workflow[workflow.index("static-checks:"):workflow.index("deploy-pages:")]
        self.assertIn("python -I -B tools/build_site.py", static_job)
        self.assertIn("python -I -B tests/test_build_site.py -v", static_job)
        self.assertIn("_site/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
        self.assertFalse((ROOT / ".cfignore").exists(), ".cfignore is not read by Cloudflare Pages")


if __name__ == "__main__":
    unittest.main()
