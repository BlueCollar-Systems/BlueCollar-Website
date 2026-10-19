# Cloudflare Pages — bluecollar-website

Account ID (reference): `df143f08ce8d490ebf620fe776fbd375`  
Project: `bluecollar-website`  
Production site changes: manual only. Run GitHub Actions [`.github/workflows/website-ci.yml`](../.github/workflows/website-ci.yml) from `main` with `deploy_production=true` (`python tools/build_site.py`, then `wrangler pages deploy <absolute path of _site>`, branch `main`, started in a new empty folder outside the checkout so that only `_site/` is uploaded: no Pages Functions from `functions/`, no `wrangler.toml`/`.json`/`.jsonc`, no `.env`; every option is one `--name=value` argument, and a `_site/` holding links is refused). An importer's `product-release` dispatch can publish refreshed download metadata and stamped badges only, after the metadata-only guard proves no other site changes would ship. All other runs validate and build without publishing.

## Verified from the public edge (no API token)

| Check | Result |
|-------|--------|
| Apex `https://bluecollar-systems.com/` | HTTP 200, served via Cloudflare (CF-RAY present) |
| Pages hostname `https://bluecollar-website.pages.dev/` | HTTP 200, same security headers as apex |
| `/repo-metadata.json` | `Cache-Control: no-store, max-age=0, must-revalidate` (matches [`_headers`](../_headers)) |
| Last successful metadata snapshot on production | `generated_at` from the last successful production run (the six-hour schedule does not deploy) |

Custom domain **bluecollar-systems.com** is active on the apex; confirm in dashboard: **Workers & Pages → bluecollar-website → Custom domains**.

## Dashboard settings (manual)

Do **not** store API tokens in this repo. Configure in the Cloudflare dashboard or GitHub Actions secrets only.

### Pages project

- **Production branch:** not used for builds (deploy is direct upload from CI); keep project linked to repo only if you use dashboard previews.
- **Build command / output:** leave empty or unused — CI builds `_site/` with [`tools/build_site.py`](../tools/build_site.py) and uploads only that folder.
- **What gets published:** only the allowlist in `tools/build_site.py` (root `*.html` and `*.css`, the site scripts, favicons, `og-image.png`, `robots.txt`, `sitemap.xml`, `repo-metadata.json`, `_headers`, `_redirects`, `.well-known/`, `p/`, `p-records/`). Cloudflare Pages does **not** read `.cfignore`, so that file was removed. A new public file (for example `app-ads.txt`) must be added to the allowlist or it will 404. The build fails if a `.py`, `.md`, `.yml`, `LICENSE` or `VERSION` file would be published, or if any on-site link points at a file outside `_site/`.
- **Disable `*.pages.dev` for production** (optional hardening): redirect `bluecollar-website.pages.dev` → `https://bluecollar-systems.com` via [Bulk Redirect](https://developers.cloudflare.com/rules/url-forwarding/bulk-redirects/) if you want apex-only traffic.

### Caching

- Static HTML/CSS/JS: default Pages caching is fine.
- **`/repo-metadata.json`:** already forced to `no-store` via [`_headers`](../_headers). No extra Cache Rule required unless you add a conflicting zone rule — if you do, set **Bypass cache** for path `/repo-metadata.json`.

### WAF / security

- Zone should stay **proxied** (orange cloud) for `bluecollar-systems.com`.
- Optional: **Security → WAF** managed ruleset on the zone; avoid blocking GitHub Actions deploy IPs (deploy uses API + Wrangler, not browser).
- **SSL/TLS:** Full (strict) recommended when origin is Pages.
- DNS/email hardening: see [`tools/remediate_cloudflare_security.py`](../tools/remediate_cloudflare_security.py) and workflow `security-remediation.yml` (DMARC, Turnstile) — run via Actions secrets, not locally committed tokens.

### Build hooks / deploy triggers

- **Two production deploys, both from `main` only.**
  - **Manual:** open **Actions → website-ci → Run workflow**, pick branch `main`, and set `deploy_production=true`. This is the only way to publish site changes (pages, styles, scripts, files). The input defaults to `false`, and a run from any other branch never deploys.
  - **Importer release:** an importer's `product-release` `repository_dispatch` deploys the download metadata and version badges only. It is compared with the last manual deploy (a release deploy never becomes that baseline) and refuses, deploying nothing, if `main` holds any other site change that was never deployed manually, including a change to the file list in `tools/build_site.py` or to the badge stamping. See the README section on release deploys.
  - Either way, `static-checks` must pass first; `deploy-pages` then re-syncs release metadata, publishes `_site/`, verifies the live metadata and routes, and commits stamped badges back to `main`.
- **Never deploy:** pushes to `main`, pull requests, the six-hour schedule, the `product-update` and steel-shapes dispatches, and a manual run left at `deploy_production=false`. On these runs `deploy-pages` shows as skipped.
- **After an importer release:** make sure `WEBSITE_DISPATCH_TOKEN` (or an alias) can fire `repository_dispatch`, so the download metadata deploys right away. If no dispatch arrives or the release deploy is refused, run the manual production deploy above. The daily `release-drift` workflow turns red if the live downloads still lag a release after 24 hours.
- **After a shape pack (`steel-v*`) release:** it sends no dispatch (it is published with `GITHUB_TOKEN`), so run the manual `deploy_production=true` deploy after each one.
- **No separate Pages “build hook” required** unless you want a manual dashboard redeploy; CI is the source of truth.

## Deploy status

**Resolved (2026-10-10):** the Cloudflare auth 10000 failure noted on 2026-09-15 no longer happens. `deploy-pages` has succeeded since then, for example run `38052687522` on 2026-10-10 ("Deployment complete!") and the manual production run `39149634087` on 2026-10-18. It runs only on a manual production run or an importer release that passes the metadata-only guard; on every other run it shows as skipped, which is not a failure. If the auth failure ever returns, rotate the token in [API Tokens](https://dash.cloudflare.com/profile/api-tokens) with **Account → Cloudflare Pages: Edit** and **Account Settings: Read**, then update the deploy token secret on `BlueCollar-Systems/BlueCollar-Website` (the workflow uses `CLOUDFLARE_PAGES_API_TOKEN`, then `CLOUDFLARE_API_TOKEN`, then `CF_API_TOKEN`, whichever is set first).

Local deploy (only if CI cannot run, and only when a production publication is authorized), after `wrangler login` against the account below:

```
python tools/build_site.py && wrangler pages deploy _site --project-name bluecollar-website --branch main
```

After any deploy, `python tools/verify_deployed_metadata.py` confirms the public metadata matches and that `/README.md` and `/.github/workflows/website-ci.yml` answer 404.

## GitHub secrets (deploy)

| Secret | Purpose |
|--------|---------|
| `CLOUDFLARE_ACCOUNT_ID` | Account `df143f08ce8d490ebf620fe776fbd375` |
| `CLOUDFLARE_PAGES_API_TOKEN` | Pages Edit + Account Settings Read |
| `REPO_METADATA_TOKEN` / dispatch tokens | `sync_repo_metadata.py` in CI |

## Cursor Cloudflare MCP

- **cloudflare-docs:** works without account auth (documentation search).
- **cloudflare-builds / bindings / observability:** require OAuth via Cursor MCP `mcp_auth`; tool descriptors stay at `mcp_auth` only until the IDE session completes Cloudflare login. Use dashboard or `gh`/Wrangler with secrets for account-specific Pages deployment lists.
