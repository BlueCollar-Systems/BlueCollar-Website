# BlueCollar-Systems Website

[![CI](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions/workflows/website-ci.yml/badge.svg)](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Static marketing site for **BlueCollar-Systems** — precision software for fabricators, welders, and detailers.

## Products

| Product | Description | Link |
|---------|-------------|------|
| **Steel Logic** | Job Clock for fitter and welder time, plus AISC v16.0 shapes, calculators, converters, and inventory. The Android beta is free with ads. A free version and a paid Pro version are the plan; iOS is in development. | [Check Android test access (Google sign-in)](https://play.google.com/apps/testing/com.bluecollarsystems.steellogic) |
| **BlueCollar Tag Logic** | Hang tags with a QR code that opens the piece in Steel Logic. New tags start with an editable BCS1: prefix; older CS1: tags still scan. Latest published build v10.43; not a download from this website yet. | [bluecollar-systems.com/#tag-qc](https://bluecollar-systems.com/#tag-qc) |
| **Free Shape Packs** | Public-domain SketchUp + DXF/DWG shape packs | [Shapes Hub](https://bluecollar-systems.com/shapes) |
| **SketchUp PDF Importer** | Vector-accurate PDF geometry import for SketchUp | [GitHub](https://github.com/BlueCollar-Systems/PDF-Importer-SketchUp) |
| **FreeCAD PDF Importer** | PDF vector import workbench for FreeCAD | [GitHub](https://github.com/BlueCollar-Systems/PDF-Importer-FreeCAD) |
| **Blender PDF Importer** | PDF vector import add-on for Blender | [GitHub](https://github.com/BlueCollar-Systems/PDF-Importer-Blender) |
| **LibreCAD PDF Converter** | PDF-to-DXF converter for LibreCAD workflows | [GitHub](https://github.com/BlueCollar-Systems/PDF-Importer-LibreCAD) |

## Tech Stack

- Vanilla HTML5
- Custom utility-class CSS (Tailwind-style naming, zero build dependencies)
- No JavaScript framework

## Development

Open `index.html` in a browser. No build step required.

To see exactly what gets published, run `python tools/build_site.py`. It copies only the public site files into `_site/` (ignored by git) and fails if a repository-only file would be published or an on-site link points at a missing file.

For a working local preview with the same page and part-tag routes as the hosted
site, run `python tools/preview_site.py` and open
`http://127.0.0.1:8082/`. Stop it with Ctrl+C. The preview uses only public site
files; it does not publish anything. This also lets Report Doctor copy buttons
use a secure localhost clipboard instead of a `file:` page.

To check every link and download button the way a visitor sees them (no login, no token), run `python tools/check_public_links.py`. A dead link (404 or 410) or a download that needs a login fails the check. A site that stays busy or unreachable (5xx, 429, network errors) after about a minute of retries is reported as a warning naming the page and URL, so brief GitHub throttling cannot block a deploy. `--offline` checks on-site links with no network; `--base https://bluecollar-systems.com` checks the live pages after a deploy.

## Optional support links

Set `ko_fi_url` and/or `github_sponsors_url` in [`support-config.json`](support-config.json)
to the owner's confirmed public profile URLs. Both can be enabled together.
Use `https://ko-fi.com/<profile>` and `https://github.com/sponsors/<account>`;
leave a field empty to hide that channel. The homepage hides the entire support
section until at least one valid URL is configured, and also hides it if the
configuration cannot be loaded. There are no placeholder donation buttons.

These are public URLs, never API tokens or account credentials. Confirm each
profile belongs to the intended recipient and accepts contributions before
deployment. The default configuration is blank pending the owner's URLs.
Use the localhost preview above to test the configuration; browsers can block
JSON fetches when opening `index.html` directly with `file:`.

Run `node tests/support_links_test.js` to check both channels and rejected URLs.

## Deployment

Deployed to **Cloudflare Pages** (project `bluecollar-website`) via GitHub Actions workflow [`.github/workflows/website-ci.yml`](.github/workflows/website-ci.yml).

- Pushes to `main` run `website-ci`.
- `static-checks` must pass before `deploy-pages` runs. There are two ways to deploy production, both from `main` only:
  - **Manual:** a `website-ci` run on `main` with `deploy_production=true`. Its default is validation only. This is the only way to publish page, style, script or other site changes.
  - **Importer release:** an importer's `product-release` dispatch deploys by itself, so the version badges and Download buttons follow each release with no separate GO (owner decision O13). It is deploy-only: no website snapshot release. It may change nothing but the download metadata; see [Release deploys change only download metadata](#release-deploys-change-only-download-metadata).
- `deploy-pages` syncs and validates release metadata, builds `_site/` with `tools/build_site.py` (public files only), publishes that folder with Wrangler, then verifies that the public domain serves the exact new metadata bytes and that repository files such as `/README.md` answer 404, then requests every live page and on-site link, before committing stamped badges back to `main`. Both ways in use these same steps and secrets.
- A manual `auto-release` run with `publish_release=true` bumps `VERSION` and publishes a GitHub Release snapshot zip. Its default builds an inspection artifact without publishing. Dispatches never start it.
- Pushes, pull requests, the six-hour schedule and the `product-update`, `steel-shapes-release` and `steel-shapes-update` dispatches run validation only. They do not deploy or publish releases.
- A shape pack (`steel-v*`) release never deploys the site by itself; run the manual deploy after each one. See [Shape pack releases need a manual deploy](#shape-pack-releases-need-a-manual-deploy).
- The daily [`release-drift`](.github/workflows/release-drift.yml) workflow turns red when the live downloads have lagged GitHub releases for more than 24 hours; see [Release drift check](#release-drift-check).

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for app launch/update steps (Google Play + iOS).

## What is live vs on main

Merging to `main` alone does not deploy. A manual production run publishes
approved site changes; an importer `product-release` dispatch can publish only
metadata and stamped badges after the guard above proves that no other public
changes would ship. `main` can therefore be ahead of what visitors see. To check:

1. **Footer version.** Compare the footer version on
   https://bluecollar-systems.com/ (for example `v1.0.109`) with
   [`VERSION`](VERSION) on `main`. A lower live number means the site is
   behind. The number changes only when a manual `auto-release` run bumps it,
   so a match alone does not prove the pages are the same.
2. **Release metadata.** From an up-to-date checkout of `main`, run
   `python tools/verify_deployed_metadata.py --expected repo-metadata.json --attempts 1`.
   It passes only if the live `/repo-metadata.json` has exactly the bytes of
   the file on `main` (same release tags, download links and `generated_at`)
   and repository files such as `/README.md` answer 404. It only reads the site.
3. **Page changes since the last deploy.** Find the commit the last
   production run published, then list what `main` has added since:

   ```bash
   gh run list -R BlueCollar-Systems/BlueCollar-Website --workflow website-ci.yml --limit 100 --json databaseId,headSha,createdAt,event
   gh run view <RUN_ID> -R BlueCollar-Systems/BlueCollar-Website   # deploy-pages must show success, not skipped
   git log --oneline <headSha>..origin/main
   ```

   Select the newest run whose **Deploy to Cloudflare Pages** step succeeded,
   whether it was manual or a `product-release` dispatch. Validation-only runs
   do not count; extend the history if none appears in these 100 runs. The
   bot's `chore: stamp release badges` commit belongs to that same deploy.
   `tools/build_site.py` publishes only its allowlist. README, docs and tests
   are not public files, but build or badge-stamping tool changes can alter
   the public output, and workflow changes affect subsequent runs. The log
   identifies commits to review; it does not by itself prove which public
   bytes differ.

A product release reaches the live site only after a successful production
run. An importer release normally triggers that run automatically; the guard
can hold it when undeployed site changes need an approved manual deployment.
Shape-pack releases follow the manual-deploy route described below.

## Android test-access status

The Google Group is an access/coordination route, not an app download. The
existing Google Play testing URL requires sign-in; eligibility depends on the
account and test track. The site therefore says **Check Test Access** rather
than promising enrollment or a download. Contact support if access is unavailable.
A public Google Play release has not been announced. This copy does not publish
or configure an app, and does not offer a public APK from this website.

## Release metadata and download links

Product versions and ZIP download URLs are **not** hardcoded in HTML for versioned `/releases/download/v…` paths. Instead:

| Layer | Role |
|-------|------|
| [`repo-metadata.json`](repo-metadata.json) | Build-time snapshot of each GitHub repo's importer release plus any `steel-v*` release channel (generated in CI). It records each release's exact target commit and immutable GitHub asset digests. Primary installers/downloads stay first for the download UI, while published verification sidecars such as attestations remain available. |
| [`tools/sync_repo_metadata.py`](tools/sync_repo_metadata.py) | Fetches GitHub API data and optionally stamps `data-repo-version` fallbacks in `*.html`. When nothing a visitor can see has changed (only the run time, or a push date no badge shows), it leaves `repo-metadata.json` and the pages byte-for-byte unchanged, so the 6-hour schedule adds no badge-stamp commit. It refuses to run if a tracked repo is private, because its download links would be dead for visitors. |
| [`nav.js`](nav.js) | Client-side enhancement: loads `/repo-metadata.json` (`Cache-Control: no-store`) and updates `data-repo-version`, `data-repo-release-link`, and `data-repo-asset-link` elements. Supports `data-release-channel="steel"` for shape-pack downloads hosted by importer repos. |
| Static HTML fallbacks | `releases/latest` links and version badges work if JavaScript or metadata fetch fails. |

Tracked repos: `PDF-Importer-SketchUp`, `PDF-Importer-FreeCAD`, `PDF-Importer-Blender`, and `PDF-Importer-LibreCAD`. Private Steel Logic and BlueCollar Tag Logic release assets are not exposed in this public snapshot. The former standalone SketchUp and DXF/DWG shape repos are now represented by `steel-v*` releases in the SketchUp and FreeCAD importer repos.

### End-to-end automation (product release → live site)

1. Importer repo `auto-release` (or manual `release: published`) creates/updates a GitHub Release.
2. Same pipeline dispatches `repository_dispatch` to `BlueCollar-Systems/BlueCollar-Website` with event type `product-release` (or `product-update`).
3. A `product-release` dispatch runs every static check, then `deploy-pages` on `main`: it re-runs `sync_repo_metadata.py` (all four importers, not only the one that dispatched), validates the metadata, builds `_site/`, confirms the deploy changes only download metadata, and deploys to Cloudflare Pages. A `product-update` dispatch only validates.
4. `tools/verify_deployed_metadata.py` requests the public metadata with cache bypass headers and a unique query, allowing up to 12 attempts with 10 seconds between attempts and a 15-second request timeout. It requires exact bytes, so stale tags, download URLs, source revisions, asset digests, or an older snapshot fail the job. Only a verified deployment commits the stamped badges back to `main`.
5. The daily drift check reports any release the site still lacks after 24 hours.

Shape pack (`steel-v*`) releases do not take this path; see
[Shape pack releases need a manual deploy](#shape-pack-releases-need-a-manual-deploy).

Release and manual deploys share one concurrency group, so two deploys never
overlap. A release deploy waits for a running deploy instead of cancelling it,
and when several importers release at once, the newest waiting run replaces
the older waiting ones; it reads every repo's latest release anyway. A manual
`deploy_production=true` run still cancels a deploy in progress, as before.

A local metadata-sync PR is optional: every production run fetches fresh
metadata itself. The separate website auto-release publishes a GitHub site
snapshot and does not deploy Pages; dispatches never start it.

### Release deploys change only download metadata

A `product-release` dispatch is a GO for new downloads, not for other website
changes that were merged to `main` but never deployed. Before upload, the
release deploy runs [`tools/check_metadata_only_deploy.py`](tools/check_metadata_only_deploy.py):

1. It finds the approved commit: the head commit of the newest **manual**
   `website-ci` run on `main` (`deploy_production=true`) whose **Deploy to
   Cloudflare Pages** step succeeded. It reads the Actions API with the run's
   own read-only token, back through the newest 1,000 manual runs (the most
   the API lists). Dispatch runs are never read, so no amount of dispatch
   traffic can push the last manual deploy out of reach. A release deploy
   never becomes the approved commit: it only proved that its commit builds
   the same folder as the approved one for that day's metadata. If that
   commit's tools behave differently for some later metadata (for example a
   banner that appears once a tag starts with `v9.`), that difference was
   never approved. So every release deploy is compared with the last manual
   deploy, and what it uploads is what that approved commit builds with the
   new metadata.
2. It builds two public folders the same clean way, each in its own new
   temporary worktree and its own new output folder: one from the commit about
   to be deployed, one from the approved commit. Both get the same freshly synced
   `repo-metadata.json`, and each commit's **own** tools do the work, run with
   that worktree as the working folder and only its own `tools/` importable:
   its `tools/sync_repo_metadata.py` (`stamp_html_versions`) stamps the version
   badges, and its `tools/build_site.py --source . --out <folder>` builds the
   folder.
3. It requires the `_site/` about to be uploaded to be byte-for-byte the clean
   build of its own commit (so no uncommitted or leftover file rides along),
   and that build to be byte-for-byte the approved commit's build. All three
   folders may hold only plain files and folders: Wrangler follows links when
   it uploads, so a link, a Windows junction or any other kind of entry is
   refused instead of compared.

`_site/` is the whole upload. The deploy step starts Wrangler in a new empty
folder outside the checkout and hands it the absolute path of `_site/`.
Started in the checkout, Wrangler 4.83.0 would also build and upload Pages
Functions from `functions/`, read a `wrangler.toml`, `wrangler.json` or
`wrangler.jsonc` found in that folder or any parent folder, and load `.env`
and `.env.local`; the guard compares none of those. The step refuses to upload
if its folder is inside the checkout or has a Wrangler config file above it,
or if `_site/` holds anything but plain files and folders. Every Wrangler
option is passed as one `--name=value` argument, because Wrangler reads a
separate value that starts with `-` as an option of its own (a commit message
such as `--cwd=<checkout>` would have sent it back into the checkout). The
commit message is only the deployment's label: the subject on one line,
without leading dashes, at most 200 characters.
This holds for manual deploys too: this site has no Pages Functions, and
adding one needs a deliberate change to the deploy step.

The guard runs from `tools/` of the very checkout it judges, so website-ci
starts it with `python -I`, which keeps `tools/` off Python's import path: a
`tools/json.py` or `tools/filecmp.py` on `main` cannot stand in for the
standard library inside the guard. Started without `-I`, the guard drops every
import-path entry inside the repository before its first import, and refuses
to run if any module it loaded comes from the repository.

So only `repo-metadata.json` and the badges stamped from it can differ from
production. `repo-metadata.json` itself is written by `main`'s
`sync_repo_metadata.py`, so a change to what the sync records ships with the
next release deploy. Files outside `_site/` never reach Cloudflare, so the
README, tests and most of `tools/` can change freely. A change to how the
public folder is made counts like a page change: if `main`'s
`tools/build_site.py` publishes a different set of
files, or `main`'s badge stamping writes different HTML, the two builds differ
and the release deploy refuses. If `main` holds any public change that is not
live yet (a page, a style, a script, a new or removed file, or such a tool
change), the release deploy stops before upload, names the files and deploys
nothing. Run `website-ci` manually on `main` with `deploy_production=true` once
those changes are approved; it publishes them and the new downloads together.

The guard also refuses, deploying nothing, whenever it cannot prove the
result: no successful manual deploy is found in the manual run history (the
message says how many runs it read and why it stopped), or the approved commit
cannot be fetched or cannot be rebuilt with its own tools. An approved commit
older than `tools/build_site.py`, or one whose tools lack
`stamp_html_versions()` or the `--source` and `--out` options, is refused with the note that a manual deploy is needed. Manual deploys skip
this step. The guard compares built files only.

**Trust boundary.** Some of `main` runs as committed inside the deploy job,
before the upload, deployed or not: `website-ci.yml` itself, the metadata sync
(`tools/sync_repo_metadata.py`, which writes `repo-metadata.json`), the
metadata check (`tools/validate_static_metadata.py`), the site build
(`tools/build_site.py`, which writes `_site/`), this guard, and any module in
`tools/` that the sync, the check or the build imports. The guard compares
what they build. It cannot see anything else they do while they run, such as
a file they write for a later step or a process they leave running, so a
change to any of them is a change to the deploy machinery and needs the same
review as a change to the workflow.

To see what a release deploy would decide, commit your changes, then run
`python tools/sync_repo_metadata.py`, `python tools/build_site.py` and
`python -I tools/check_metadata_only_deploy.py` (add `--deployed-sha <commit>` to
skip the Actions API lookup). It only reads; it never deploys. An uncommitted
change to a public file makes `_site/` differ from the clean build of `HEAD`,
and the guard refuses.

### Shape pack releases need a manual deploy

A shape pack (`steel-v*`) release never deploys the site by itself. The
`steel-shapes-release.yml` workflow in the SketchUp and FreeCAD repos publishes
the release with `GITHUB_TOKEN`, and GitHub starts no other workflow from an
event made with that token, so `notify-website-deploy` does not run and no
`product-release` dispatch reaches the website. (A `steel-shapes-release`
dispatch only validates.) After every shape pack release, run `website-ci`
manually on `main` with `deploy_production=true`. The next importer release
deploy also picks the pack up, because every deploy reads all channels. If
neither happens, the daily drift check turns red after 24 hours, and its issue
says the shape pack needs the manual deploy.

### Release drift check

[`.github/workflows/release-drift.yml`](.github/workflows/release-drift.yml)
runs once a day (13:41 UTC), and on demand from the Actions tab. It runs
[`tools/check_release_drift.py`](tools/check_release_drift.py), which reads the
live `https://bluecollar-systems.com/repo-metadata.json` (cache bypassed) and
compares each importer with the release a deploy would publish now: the newest
published, final `v*` release, and the newest `steel-v*` shape-pack release in
the SketchUp and FreeCAD repos. The check reads that rule from
`sync_repo_metadata.py` (`importer_tag_prefix()`; a tracked repo outside the
PDF importers would follow GitHub's `/releases/latest` in both). A normal
deploy clears available-release drift. If the last final release was withdrawn,
the sync retains its previous snapshot: that needs an approved replacement or
explicit retirement, rather than a metadata refresh alone. Drafts and
prereleases never count as replacements.

- **Behind for less than 24 hours:** a warning only; the job stays green. The
  release deploy normally closes this within minutes. A shape pack waits for
  the manual deploy (see above), and the report says so.
- **Behind for more than 24 hours:** the job turns red and opens one issue,
  *Live site downloads are behind GitHub releases*, or updates it if it is
  already open. The age counts from the publish time of the first release the
  site is missing, so a fresh release on top of an old gap does not reset it.
- **A live release that GitHub no longer lists** (deleted, back to draft or
  prerelease) turns red at once, because its Download link may be dead. This
  includes withdrawal of the channel's last final release; a truly empty
  channel with no advertised release remains in sync.
- **In sync again:** the next run comments with the result and closes the issue.
- **The check could not run** (site or GitHub API unreachable, or an error in
  the tool itself): red with status 2, and the issue is not opened, edited or
  closed. Only a finished check that found stale downloads (exit 1, with the
  stale marker in its report) can open the issue, so a crash never reads as
  drift.

For available-release drift, the fix is the manual `website-ci` run with
`deploy_production=true` once that deployment is approved. If no final
replacement exists, approve a replacement release or a website change that
retires the affected download; syncing alone retains the withdrawn snapshot.
The report identifies the applicable recovery and never automatically unlinks
or republishes anything. The workflow never builds, deploys or pushes. Pull
requests that change the check run it read-only and never touch the issue.

To check by hand: `python tools/check_release_drift.py` (exit 0 in sync or
within the grace period, 1 stale, 2 could not check; `--grace-hours` and
`--report drift.md` are optional).

To check a prepared snapshot manually, run `python tools/verify_deployed_metadata.py --expected repo-metadata.json`. This reads the public metadata; it does not deploy or change any content.

Importer workflows: `.github/workflows/auto-release.yml` and `.github/workflows/notify-website-deploy.yml` in each product repo.

### GitHub Actions secrets (BlueCollar-Website repo)

Configure under **Settings → Secrets and variables → Actions**:

| Secret | Required | Purpose |
|--------|----------|---------|
| `CLOUDFLARE_ACCOUNT_ID` | Yes (deploy) | Cloudflare account for Pages API / Wrangler. |
| `CLOUDFLARE_PAGES_API_TOKEN` | Yes (deploy) | Preferred. Needs **Account → Cloudflare Pages: Edit** and **Account Settings: Read**. Alternatives: `CLOUDFLARE_API_TOKEN`, `CF_API_TOKEN`. |
| `REPO_METADATA_TOKEN` | Recommended | PAT or fine-grained token that can read **public** org repos (and any private product repos). Used only in CI to call `api.github.com` for `sync_repo_metadata.py`. Scope: `public_repo` (classic) or repository read on each product repo. If missing, workflow falls back to `GITHUB_TOKEN` (same-repo only; org repos may 404). |

Do **not** put GitHub or Cloudflare tokens in HTML, `nav.js`, or committed config.

### GitHub Actions secrets (each product repo: PDF-Importer-*, etc.)

| Secret | Required | Purpose |
|--------|----------|---------|
| `WEBSITE_DISPATCH_TOKEN` | Recommended | PAT or fine-grained token allowed to trigger `repository_dispatch` on `BlueCollar-Systems/BlueCollar-Website`. Classic PAT: `repo` scope (or fine-grained: **Actions: Read and write** on `BlueCollar-Website`). Aliases accepted in workflows: `BLUECOLLAR_WEBSITE_DISPATCH_TOKEN`, `REPO_DISPATCH_TOKEN`. |

If `WEBSITE_DISPATCH_TOKEN` is unset, releases still publish on GitHub, but no `product-release` dispatch arrives, so the site does not update by itself; the daily drift check turns red after 24 hours. Every website change other than download metadata always requires the manual deployment described above.

**Dispatch payload** (informational; website workflow re-syncs all repos, it does not merge this JSON into the site):

```json
{
  "source_repo": "BlueCollar-Systems/PDF-Importer-SketchUp",
  "source_event": "auto-release",
  "source_ref": "refs/heads/main",
  "source_sha": "<commit>",
  "release_tag": "v3.7.2",
  "release_name": "v3.7.2",
  "release_url": "https://github.com/BlueCollar-Systems/PDF-Importer-SketchUp/releases/tag/v3.7.2"
}
```

Event types listened by `website-ci`: `product-release` (validates, then deploys download metadata), `product-update`, `steel-shapes-release`, `steel-shapes-update` (validate only).

## License

MIT License. See [LICENSE](LICENSE) for details.
