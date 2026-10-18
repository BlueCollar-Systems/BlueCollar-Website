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
- `static-checks` must pass before `deploy-pages` runs. Production deployment requires a manual `website-ci` run on `main` with `deploy_production=true`; its default is validation only.
- `deploy-pages` syncs and validates release metadata, builds `_site/` with `tools/build_site.py` (public files only), publishes that folder with Wrangler, then verifies that the public domain serves the exact new metadata bytes and that repository files such as `/README.md` answer 404, then requests every live page and on-site link, before committing stamped badges back to `main`.
- A manual `auto-release` run with `publish_release=true` bumps `VERSION` and publishes a GitHub Release snapshot zip. Its default builds an inspection artifact without publishing.
- Pushes, product dispatches and the six-hour schedule run validation. They do not deploy or publish releases.

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
3. The dispatch runs validation. After product releases finish, manually run `website-ci` on `main` with `deploy_production=true`; `deploy-pages` re-runs `sync_repo_metadata.py` and deploys to Cloudflare Pages.
4. `tools/verify_deployed_metadata.py` requests the public metadata with cache bypass headers and a unique query, allowing up to 12 attempts with 10 seconds between attempts and a 15-second request timeout. It requires exact bytes, so stale tags, download URLs, source revisions, asset digests, or an older snapshot fail the job. Only a verified deployment commits the stamped badges back to `main`.

A product dispatch refreshes only its validation runner's working copy; it does
not persist badges or deploy Pages. A local metadata-sync PR is optional: the
manual production job always fetches fresh metadata itself. The separate
website auto-release publishes a GitHub site snapshot and does not deploy Pages.

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

If `WEBSITE_DISPATCH_TOKEN` is unset, releases still publish on GitHub. Production website updates always require the manual deployment described above.

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

Event types listened by `website-ci`: `product-release`, `product-update`, `steel-shapes-release`, `steel-shapes-update`.

## License

MIT License. See [LICENSE](LICENSE) for details.
