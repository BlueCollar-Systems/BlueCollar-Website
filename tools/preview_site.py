"""Preview public website files on localhost with the Cloudflare page routes."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SUFFIXES = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".txt",
    ".svg",
    ".ico",
    ".png",
}


def preview_route(request_path: str) -> str | None:
    """Map a public URL to a file; development files and traversal stay private."""
    encoded_path = urlsplit(request_path).path
    path = unquote(encoded_path)
    if any(part in {".", ".."} for part in path.split("/")) or "\\" in path:
        return None
    if path in {"", "/"}:
        return "index.html"
    if encoded_path.startswith("/p/") or path == "/p":
        return "p/index.html"
    if path in {"/security.txt", "/.well-known/security.txt"}:
        return ".well-known/security.txt"
    relative = path.lstrip("/")
    if "/" not in relative:
        candidate = SITE_ROOT / relative
        if candidate.suffix == "":
            candidate = candidate.with_suffix(".html")
        if candidate.is_file() and candidate.suffix in PUBLIC_SUFFIXES:
            return candidate.name
    if path.startswith("/p-records/") and "/" not in relative[len("p-records/") :]:
        candidate = SITE_ROOT / relative
        if candidate.suffix == ".json" and candidate.is_file():
            return relative
    return None


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_ROOT), **kwargs)

    def do_GET(self):
        self._serve(super().do_GET)

    def do_HEAD(self):
        self._serve(super().do_HEAD)

    def _serve(self, serve):
        target = preview_route(self.path)
        if target is None:
            self.send_error(404, "Public preview file not found")
            return
        original = self.path
        self.path = "/" + target
        try:
            serve()
        finally:
            self.path = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8082)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler) as server:
        print(f"Website preview: http://127.0.0.1:{server.server_port}/", flush=True)
        print(
            "Press Ctrl+C to stop. This preview does not deploy or publish.", flush=True
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
