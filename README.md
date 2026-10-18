# BlueCollar-Systems Website

[![CI](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions/workflows/website-ci.yml/badge.svg)](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Static marketing site for **BlueCollar-Systems** — precision software for fabricators, welders, and detailers.

## Products

| Product | Description | Link |
|---------|-------------|------|
| **Steel Logic** | Job Clock for fitter and welder time, plus AISC v16.0 shapes, calculators, converters, and inventory. The Android beta is free with ads. A free version and a paid Pro version are the plan; iOS is in development. | [Check Android test access (Google sign-in)](https://play.google.com/apps/testing/com.bluecollarsystems.steellogic) |
| **Tag QC Builder** | Hang tags with a QR code that opens the piece in Steel Logic. New tags start with an editable BCS1: prefix; older CS1: tags still scan. Latest published build v10.43; not a download from this website yet. | [bluecollar-systems.com/#tag-qc](https://bluecollar-systems.com/#tag-qc) |
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
- The daily [`release-drift`](.github/workflows/release-drift.yml) workflow turns red when the live downloads have lagged GitHub releases for more than 24 hours; see [Release drift check](#release-drift-check).

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for app launch/update steps (Google Play + iOS).

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

Tracked repos: `PDF-Importer-SketchUp`, `PDF-Importer-FreeCAD`, `PDF-Importer-Blender`, and `PDF-Importer-LibreCAD`. Private Steel Logic and Tag QC release assets are not exposed in this public snapshot. The former standalone SketchUp and DXF/DWG shape repos are now represented by `steel-v*` releases in the SketchUp and FreeCAD importer repos.

### End-to-end automation (product release → live site)

1. Importer repo `auto-release` (or manual `release: published`) creates/updates a GitHub Release.
2. Same pipeline dispatches `repository_dispatch` to `BlueCollar-Systems/BlueCollar-Website` with event type `product-release` (or `product-update`).
3. A `product-release` dispatch runs every static check, then `deploy-pages` on `main`: it re-runs `sync_repo_metadata.py` (all four importers, not only the one that dispatched), validates the metadata, builds `_site/`, confirms the deploy changes only download metadata, and deploys to Cloudflare Pages. A `product-update` dispatch only validates.
4. `tools/verify_deployed_metadata.py` requests the public metadata with cache bypass headers and a unique query, allowing up to 12 attempts with 10 seconds between attempts and a 15-second request timeout. It requires exact bytes, so stale tags, download URLs, source revisions, asset digests, or an older snapshot fail the job. Only a verified deployment commits the stamped badges back to `main`.
5. The daily drift check reports any release the site still lacks after 24 hours.

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

1. It finds the commit that is live now: the head commit of the newest
   `website-ci` run whose **Deploy to Cloudflare Pages** step succeeded (read
   from the Actions API with the run's own read-only token).
2. It checks that commit out in a temporary worktree, gives it the same freshly
   synced `repo-metadata.json`, stamps its version badges and builds its public
   folder with `tools/build_site.py`.
3. It requires that folder to be byte-for-byte identical to the `_site/` about
   to be deployed.

So only `repo-metadata.json` and the badges stamped from it can differ from
production. Changes to README, tests, tools or workflows are not published
and do not matter. If `main` holds any public change that is not live yet (a
page, a style, a script, a new or removed file), the release deploy stops
before upload, names the files and deploys nothing. Run `website-ci` manually
on `main` with `deploy_production=true` once those changes are approved; it
publishes them and the new downloads together. The guard also refuses when it
cannot tell which commit is live (no earlier deploy run found, or the commit
cannot be fetched or built). Manual deploys skip this step.

To see what a release deploy would decide, after `python tools/sync_repo_metadata.py`
and `python tools/build_site.py`, run `python tools/check_metadata_only_deploy.py`
(add `--deployed-sha <commit>` to skip the Actions API lookup). It only reads;
it never deploys.

### Release drift check

[`.github/workflows/release-drift.yml`](.github/workflows/release-drift.yml)
runs once a day (13:41 UTC), and on demand from the Actions tab. It runs
[`tools/check_release_drift.py`](tools/check_release_drift.py), which reads the
live `https://bluecollar-systems.com/repo-metadata.json` (cache bypassed) and
compares each importer with the release a deploy would publish now: the newest
published, final `v*` release, and the newest `steel-v*` shape-pack release in
the SketchUp and FreeCAD repos. That is the same selection rule as
`sync_repo_metadata.py`, so a deploy always clears what it reports. Drafts and
prereleases never count.

- **Behind for less than 24 hours:** a warning only; the job stays green. The
  release deploy normally closes this within minutes.
- **Behind for more than 24 hours:** the job turns red and opens one issue,
  *Live site downloads are behind GitHub releases*, or updates it if it is
  already open. The age counts from the publish time of the first release the
  site is missing, so a fresh release on top of an old gap does not reset it.
- **A live release that GitHub no longer lists** (deleted, back to draft or
  prerelease) turns red at once, because its Download link may be dead.
- **In sync again:** the next run comments with the result and closes the issue.
- **Site or GitHub API unreachable:** red, no issue change.

The fix for a red run is the manual `website-ci` run with
`deploy_production=true`. The workflow never builds, deploys or pushes. Pull
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
