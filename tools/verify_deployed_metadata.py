#!/usr/bin/env python3
"""Require the public download metadata to match the snapshot just deployed.

After the metadata matches, also require that repository-only files (the
README and the CI workflow) are NOT served on the public site. Only the
_site folder built by tools/build_site.py may be published.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Callable


DEFAULT_URL = "https://bluecollar-systems.com/repo-metadata.json"

# Repository-only files that must answer 404 on the live site. If either is
# served, the deploy uploaded the repository root instead of _site/.
PRIVATE_PATHS: tuple[str, ...] = (
    "/README.md",
    "/.github/workflows/website-ci.yml",
)


class MetadataVerificationError(RuntimeError):
    """The intended metadata never became available at the public URL."""


def verify_deployed_metadata(
    expected: bytes,
    url: str = DEFAULT_URL,
    *,
    attempts: int = 12,
    delay: float = 10,
    timeout: float = 15,
    opener: Callable | None = None,
    sleep: Callable = time.sleep,
) -> str:
    """Compare exact bytes, including all tags, source revisions and asset digests.

    Redirects follow urllib's normal handling, so canonical domain redirects
    remain supported. Each request bypasses caches and receives a unique query.
    HTTP errors, incomplete responses and mismatches all consume the same
    bounded propagation retry budget; none count as a successful deployment.
    """
    if attempts < 1 or delay < 0 or timeout <= 0:
        raise ValueError("attempts must be positive, delay nonnegative and timeout positive")
    payload = json.loads(expected)
    if not isinstance(payload, dict) or not isinstance(payload.get("repos"), dict) or not payload["repos"]:
        raise ValueError("Expected snapshot must be JSON with a nonempty repos object")

    expected_digest = hashlib.sha256(expected).hexdigest()
    open_url = opener or urllib.request.urlopen
    parsed = urllib.parse.urlsplit(url)
    last_error = "No response received"
    for attempt in range(1, attempts + 1):
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        query.append(("publication_check", f"{expected_digest[:12]}-{uuid.uuid4().hex}"))
        request_url = urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query), fragment=""))
        request = urllib.request.Request(
            request_url,
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache, no-store",
                "Pragma": "no-cache",
                "User-Agent": "Mozilla/5.0 (BlueCollar Website deployment verification)",
            },
        )
        try:
            with open_url(request, timeout=timeout) as response:
                if response.getcode() != 200:
                    raise MetadataVerificationError(f"HTTP {response.getcode()}, expected 200")
                # One extra byte detects extra content without downloading an
                # unbounded error page or accidentally accepting a prefix.
                actual = response.read(len(expected) + 1)
            if actual != expected:
                raise MetadataVerificationError(
                    "Public snapshot differs from deployed snapshot "
                    f"(expected sha256:{expected_digest}; received prefix sha256:{hashlib.sha256(actual).hexdigest()})"
                )
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}, expected 200"
        except (OSError, http.client.HTTPException, MetadataVerificationError) as exc:
            last_error = str(exc)
        else:
            print(f"Verified public download metadata: sha256:{expected_digest}")
            return expected_digest

        print(f"Metadata verification attempt {attempt}/{attempts}: {last_error}", file=sys.stderr)
        if attempt < attempts:
            sleep(delay)

    raise MetadataVerificationError(
        f"Public download metadata did not match after {attempts} attempts: {last_error}"
    )


def verify_private_paths_hidden(
    url: str = DEFAULT_URL,
    paths: tuple[str, ...] = PRIVATE_PATHS,
    *,
    attempts: int = 12,
    delay: float = 10,
    timeout: float = 15,
    opener: Callable | None = None,
    sleep: Callable = time.sleep,
) -> None:
    """Require every repository-only path to answer HTTP 404 on the site.

    A 200 (or any answer other than 404) uses the same bounded retry budget
    as the metadata check, so a slow edge cache can catch up, then fails.
    """
    if attempts < 1 or delay < 0 or timeout <= 0:
        raise ValueError("attempts must be positive, delay nonnegative and timeout positive")
    open_url = opener or urllib.request.urlopen
    for path in paths:
        target = urllib.parse.urljoin(url, path)
        last_error = "No response received"
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(
                target + "?publication_check=" + uuid.uuid4().hex,
                headers={
                    "Cache-Control": "no-cache, no-store",
                    "Pragma": "no-cache",
                    "User-Agent": "Mozilla/5.0 (BlueCollar Website deployment verification)",
                },
            )
            try:
                with open_url(request, timeout=timeout) as response:
                    status = response.getcode()
            except urllib.error.HTTPError as exc:
                status = exc.code
            except (OSError, http.client.HTTPException) as exc:
                status = None
                last_error = str(exc)
            if status == 404:
                print(f"Verified {path} is not published (HTTP 404)")
                break
            if status is not None:
                last_error = f"HTTP {status}, expected 404"
            print(f"Private file check {path} attempt {attempt}/{attempts}: {last_error}", file=sys.stderr)
            if attempt < attempts:
                sleep(delay)
        else:
            raise MetadataVerificationError(
                f"Repository file {path} is still public on the website ({last_error}). "
                "Deploy only the _site folder built by tools/build_site.py."
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, default=Path("repo-metadata.json"))
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay", type=float, default=10)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args(argv)
    try:
        verify_deployed_metadata(
            args.expected.read_bytes(), args.url,
            attempts=args.attempts, delay=args.delay, timeout=args.timeout,
        )
        verify_private_paths_hidden(
            args.url, attempts=args.attempts, delay=args.delay, timeout=args.timeout,
        )
    except (OSError, ValueError, MetadataVerificationError) as exc:
        print(f"Deployment verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
