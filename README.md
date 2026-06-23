# BlueCollar Systems Website

[![CI](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions/workflows/website-ci.yml/badge.svg)](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Static marketing site for **BlueCollar Systems** — precision software for fabricators, welders, and detailers.

## Products

| Product | Description | Link |
|---------|-------------|------|
| **Steel Logic** | AISC v16.0 Structural Steel Shapes Reference (mobile app) | [Google Play beta](https://play.google.com/store/apps/details?id=com.bluecollarsystems.steellogic) |
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

## Deployment

Deployed to **Cloudflare Pages** (project `bluecollar-website`) via GitHub Actions workflow [`.github/workflows/website-ci.yml`](.github/workflows/website-ci.yml).

- Pushes to `main` run `website-ci`.
- `static-checks` must pass before `deploy-pages` runs.
- `deploy-pages` runs `tools/sync_repo_metadata.py`, then publishes the static tree with Wrangler.
- Pushes to `main`/`master` also run `auto-release` to bump `VERSION` and publish a GitHub Release snapshot zip.
- A **cron** (`17 */6 * * *`) re-syncs release metadata even if no product repo fired a dispatch.

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for app launch/update steps (Google Play + iOS).

## Release metadata and download links

Product versions and ZIP download URLs are **not** hardcoded in HTML for versioned `/releases/download/v…` paths. Instead:

| Layer | Role |
|-------|------|
| [`repo-metadata.json`](repo-metadata.json) | Build-time snapshot of each GitHub repo's importer release plus any `steel-v*` release channel (generated in CI). |
| [`tools/sync_repo_metadata.py`](tools/sync_repo_metadata.py) | Fetches GitHub API data and optionally stamps `data-repo-version` fallbacks in `*.html`. |
| [`nav.js`](nav.js) | Client-side enhancement: loads `/repo-metadata.json` (`Cache-Control: no-store`) and updates `data-repo-version`, `data-repo-release-link`, and `data-repo-asset-link` elements. Supports `data-release-channel="steel"` for shape-pack downloads hosted by importer repos. |
| Static HTML fallbacks | `releases/latest` links and version badges work if JavaScript or metadata fetch fails. |

Tracked repos: `PDF-Importer-SketchUp`, `PDF-Importer-FreeCAD`, `PDF-Importer-Blender`, `PDF-Importer-LibreCAD`, and `Steel-Shapes` (kept only if the API token can read it). The former standalone SketchUp and DXF/DWG shape repos are now represented by `steel-v*` releases in the SketchUp and FreeCAD importer repos.

### End-to-end automation (product release → live site)

1. Importer repo `auto-release` (or manual `release: published`) creates/updates a GitHub Release.
2. Same pipeline dispatches `repository_dispatch` to `BlueCollar-Systems/BlueCollar-Website` with event type `product-release` (or `product-update`).
3. `website-ci` `deploy-pages` re-runs `sync_repo_metadata.py` and deploys to Cloudflare Pages.

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

If `WEBSITE_DISPATCH_TOKEN` is unset, releases still publish on GitHub but the website only updates on the 6-hour cron, the next `main` push, or manual `workflow_dispatch`.

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
