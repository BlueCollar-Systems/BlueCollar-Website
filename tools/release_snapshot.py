"""Pin website release bytes to one commit; verify a draft before publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args]).decode("utf-8").strip()


def prepare(version, repository, directory):
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Invalid release version")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository), "Invalid repository")
    commit = git("rev-parse", "HEAD")
    require(re.fullmatch(r"[0-9a-f]{40}", commit), "Expected full source commit")
    require(git("show", commit + ":VERSION") == version, "VERSION differs from pinned source")
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / f"BlueCollar-Website_v{version}.zip"
    sidecar = directory / f"BlueCollar-Website_v{version}.provenance.json"
    require(not archive.exists() and not sidecar.exists(), "Release output already exists")
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=zip", "--output", str(archive), commit], check=True)
    proof = {"schema": "bcs.website-release-snapshot/1", "repository": repository,
             "tag": "v" + version, "source_commit": commit,
             "source_tree": git("rev-parse", commit + "^{tree}"),
             "archive": {"name": archive.name, "bytes": archive.stat().st_size, "sha256": digest(archive)}}
    with sidecar.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(proof, indent=2) + "\n")
    return sidecar


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError("Unexpected GitHub JSON API redirect")


class GitHub:
    def __init__(self, repository):
        self.repository = repository
        self.token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        require(self.token, "GitHub token required for explicitly approved publication")
        self.opener = build_opener(NoRedirect())

    def api(self, suffix, method="GET", body=None, absent_ok=False):
        url = "https://api.github.com/repos/" + self.repository + "/" + suffix
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(url, data=data, method=method, headers={
            "Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "BlueCollar-Website-Snapshot",
            "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404 and absent_ok:
                return None
            raise ValueError(f"GitHub API {method} failed (HTTP {error.code})") from None

    def find_release(self, tag):
        # Numeric-id lookup/list includes authenticated drafts; /tags alone does not.
        found = []
        for page in range(1, 101):
            batch = self.api(f"releases?per_page=100&page={page}")
            require(isinstance(batch, list), "Invalid release listing")
            found += [item for item in batch if item.get("tag_name") == tag]
            if len(batch) < 100:
                require(len(found) <= 1, "Duplicate release tags")
                return found[0] if found else None
        raise ValueError("Release listing exceeded bounded pagination")

    def tag_commit(self, tag):
        ref = self.api("git/ref/tags/" + tag, absent_ok=True)
        if ref is None:
            return None
        obj, seen = ref["object"], set()
        for _ in range(8):
            require(obj["sha"] not in seen, "Cyclic annotated tag")
            seen.add(obj["sha"])
            if obj["type"] == "commit":
                return obj["sha"]
            require(obj["type"] == "tag", "Tag does not resolve to a commit")
            obj = self.api("git/tags/" + obj["sha"])["object"]
        raise ValueError("Annotated tag nesting exceeded bound")

    def create_draft(self, proof, files):
        command = ["gh", "release", "create", proof["tag"], "--repo", self.repository,
                   "--target", proof["source_commit"], "--draft", "--latest=false",
                   "--title", proof["tag"] + " — BlueCollar Systems Website Snapshot",
                   "--notes", "Exact source snapshot: " + proof["source_commit"] +
                   ". Archive SHA256 and source identity are in the provenance sidecar.",
                   *[str(path) for path in files]]
        result = subprocess.run(command, capture_output=True)
        require(result.returncode == 0, "Draft create/upload failed; inspect without clobbering")

    def download(self, asset_id, destination):
        require(type(asset_id) is int and asset_id > 0, "Invalid release asset id")
        with destination.open("xb") as stream:
            result = subprocess.run(["gh", "api", f"repos/{self.repository}/releases/assets/{asset_id}",
                                     "--method", "GET", "-H", "Accept: application/octet-stream"],
                                    stdout=stream, stderr=subprocess.PIPE)
        require(result.returncode == 0, "Uploaded asset download failed")


def verify_release(client, release, proof, files, draft):
    require(release["tag_name"] == proof["tag"] and release["target_commitish"] == proof["source_commit"], "Release source differs from archive source")
    require(release["draft"] is draft and release["prerelease"] is False, "Unexpected release state")
    actual_commit = client.tag_commit(proof["tag"])
    # GitHub may defer creating a new draft's tag until publication.
    require(actual_commit == proof["source_commit"] or (draft and actual_commit is None), "Tag source mismatch")
    assets = release["assets"]
    require(len(assets) == len(files) and {item["name"] for item in assets} == {path.name for path in files}, "Incomplete/extra release assets; never repair by clobber")
    require(len({item["id"] for item in assets}) == len(assets), "Duplicate release asset ids")
    with tempfile.TemporaryDirectory(prefix="bcs-website-release-check-") as directory:
        for path in files:
            item = next(item for item in assets if item["name"] == path.name)
            require(item["state"] == "uploaded" and item["size"] == path.stat().st_size and
                    item.get("digest") == "sha256:" + digest(path), "Uploaded asset size/digest mismatch")
            downloaded = Path(directory) / path.name
            client.download(item["id"], downloaded)
            require(downloaded.stat().st_size == path.stat().st_size and digest(downloaded) == digest(path), "Downloaded bytes differ from local release bytes")


def verify_local_source(proof, archive):
    require(git("rev-parse", proof["source_commit"]) == proof["source_commit"] and
            git("rev-parse", proof["source_commit"] + "^{tree}") == proof["source_tree"] and
            git("show", proof["source_commit"] + ":VERSION") == proof["tag"][1:], "Local source provenance mismatch")
    with tempfile.TemporaryDirectory(prefix="bcs-website-source-check-") as directory:
        rebuilt = Path(directory) / archive.name
        subprocess.run(["git", "-C", str(ROOT), "archive", "--format=zip", "--output", str(rebuilt), proof["source_commit"]], check=True)
        require(digest(rebuilt) == digest(archive), "Archive differs from exact pinned Git source")


def publish(sidecar, client=None):
    proof = json.loads(sidecar.read_text(encoding="utf-8"))
    require(proof["schema"] == "bcs.website-release-snapshot/1", "Invalid provenance schema")
    require(re.fullmatch(r"[0-9a-f]{40}", proof["source_commit"]), "Full source SHA required")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", proof["repository"]), "Invalid repository")
    require(re.fullmatch(r"v\d+\.\d+\.\d+", proof["tag"]), "Invalid release tag")
    name = "BlueCollar-Website_" + proof["tag"]
    require(sidecar.name == name + ".provenance.json" and proof["archive"]["name"] == name + ".zip", "Unexpected release filenames")
    archive = sidecar.with_name(proof["archive"]["name"])
    require(archive.stat().st_size == proof["archive"]["bytes"] and digest(archive) == proof["archive"]["sha256"], "Local archive drift after preparation")
    verify_local_source(proof, archive)
    files = [archive, sidecar]
    client = client or GitHub(proof["repository"])
    # The pinned commit must exist in the target remote repository.
    require(client.api("commits/" + proof["source_commit"])["sha"] == proof["source_commit"], "Pinned source absent remotely")
    tag_commit = client.tag_commit(proof["tag"])
    require(tag_commit in (None, proof["source_commit"]), "Existing tag belongs to different source")
    existing = client.find_release(proof["tag"])
    if existing is not None:
        require(existing["draft"] is False, "Existing draft requires explicit inspection; no automatic mutation")
        verify_release(client, existing, proof, files, draft=False)
        return {"status": "VERIFIED_EXISTING_RELEASE", "source_commit": proof["source_commit"]}
    client.create_draft(proof, files)
    minted = client.find_release(proof["tag"])
    require(minted is not None and type(minted["id"]) is int and minted["id"] > 0, "Minted draft missing")
    release_id = minted["id"]
    # Read exact numeric draft id; never confuse a published /tags response.
    minted = client.api("releases/" + str(release_id))
    verify_release(client, minted, proof, files, draft=True)
    client.api("releases/" + str(release_id), method="PATCH", body={"draft": False, "make_latest": "true"})
    published = client.api("releases/" + str(release_id))
    verify_release(client, published, proof, files, draft=False)
    return {"status": "VERIFIED_NEW_RELEASE", "source_commit": proof["source_commit"], "release_id": release_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    build = modes.add_parser("prepare")
    build.add_argument("--version", required=True); build.add_argument("--repository", required=True)
    build.add_argument("--output-dir", required=True, type=Path)
    mint = modes.add_parser("publish")
    mint.add_argument("--provenance", required=True, type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.version, args.repository, args.output_dir))
    else:
        print(json.dumps(publish(args.provenance)))


if __name__ == "__main__":
    main()
