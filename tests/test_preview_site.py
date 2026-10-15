import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "preview_site", Path(__file__).resolve().parents[1] / "tools" / "preview_site.py"
)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewRouteTests(unittest.TestCase):
    def test_home_and_extensionless_pages_use_public_html(self):
        self.assertEqual(preview.preview_route("/"), "index.html")
        for name in ["shapes", "report-doctor", "feedback", "privacy"]:
            self.assertEqual(
                preview.preview_route("/" + name + "?test=1"), name + ".html"
            )

    def test_part_urls_preserve_resolver_route(self):
        for url in ["/p/training-part", "/p/training%2Fpart%231", "/p/"]:
            self.assertEqual(preview.preview_route(url), "p/index.html")

    def test_public_static_assets_resolve(self):
        for name in [
            "styles.css",
            "nav.js",
            "support-links.js",
            "support-config.json",
            "report-doctor.js",
            "repo-metadata.json",
            "app-ads.txt",
            "favicon.svg",
        ]:
            self.assertEqual(preview.preview_route("/" + name), name)
        self.assertEqual(
            preview.preview_route("/security.txt"), ".well-known/security.txt"
        )

    def test_development_files_and_traversal_are_not_served(self):
        for url in [
            "/.git/config",
            "/tools/preview_site.py",
            "/dev_logs/",
            "/p-records/../../README.md",
            "/%2E%2E/index.html",
            "/p/%2E%2E/index.html",
            "/p\\..\\index.html",
        ]:
            self.assertIsNone(preview.preview_route(url), url)


if __name__ == "__main__":
    unittest.main()
