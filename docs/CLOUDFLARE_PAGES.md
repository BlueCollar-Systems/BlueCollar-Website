# Cloudflare Pages — bluecollar-website

Account ID (reference): `df143f08ce8d490ebf620fe776fbd375`  
Project: `bluecollar-website`  
Production site changes: manual only. Run GitHub Actions [`.github/workflows/website-ci.yml`](../.github/workflows/website-ci.yml) from `main` with `deploy_production=true` (`python tools/build_site.py`, then `wrangler pages deploy _site`, branch `main`). An importer's `product-release` dispatch can publish refreshed download metadata and stamped badges only, after the metadata-only guard proves no other site changes would ship. All other runs validate and build without publishing.

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

- **Validation triggers:** push to `main`, pull requests, the 6-hour schedule, and the `product-update` and steel-shapes dispatches. None of them deploy.
- **Deploy triggers:** a manual `workflow_dispatch` on `main` with `deploy_production=true` (any approved site change), and an importer's `product-release` `repository_dispatch` (download metadata and badges only; the deploy refuses if `main` holds other undeployed site changes). See the README sections on release deploys and the release drift check.
- **No separate Pages “build hook” required** unless you want a manual dashboard redeploy; CI is the source of truth.
- After publishing a new GitHub **release** on an importer repo, ensure `WEBSITE_DISPATCH_TOKEN` (or equivalent) can fire `repository_dispatch` so the download metadata deploys right away. The daily `release-drift` workflow turns red if the live downloads still lag a release after 24 hours.
- A shape pack (`steel-v*`) release sends no dispatch (it is published with `GITHUB_TOKEN`), so run the manual `deploy_production=true` deploy after each one.

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
