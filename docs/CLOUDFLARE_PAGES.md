# Cloudflare Pages — bluecollar-website

Account ID (reference): `df143f08ce8d490ebf620fe776fbd375`  
Project: `bluecollar-website`  
Production deploy: GitHub Actions [`.github/workflows/website-ci.yml`](../.github/workflows/website-ci.yml) (`wrangler pages deploy`, branch `main`).

## Verified from the public edge (no API token)

| Check | Result |
|-------|--------|
| Apex `https://bluecollar-systems.com/` | HTTP 200, served via Cloudflare (CF-RAY present) |
| Pages hostname `https://bluecollar-website.pages.dev/` | HTTP 200, same security headers as apex |
| `/repo-metadata.json` | `Cache-Control: no-store, max-age=0, must-revalidate` (matches [`_headers`](../_headers)) |
| Last successful metadata snapshot on production | `generated_at` from scheduled deploy (~6h cadence in workflow) |

Custom domain **bluecollar-systems.com** is active on the apex; confirm in dashboard: **Workers & Pages → bluecollar-website → Custom domains**.

## Dashboard settings (manual)

Do **not** store API tokens in this repo. Configure in the Cloudflare dashboard or GitHub Actions secrets only.

### Pages project

- **Production branch:** not used for builds (deploy is direct upload from CI); keep project linked to repo only if you use dashboard previews.
- **Build command / output:** leave empty or unused — CI uploads the repo root as static assets.
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

- **Primary trigger:** push to `main`, `repository_dispatch` (`product-release`, `product-update`, steel-shapes events), 6-hour schedule, `workflow_dispatch`.
- **No separate Pages “build hook” required** unless you want a manual dashboard redeploy; CI is the source of truth.
- After publishing a new GitHub **release** on an importer repo, ensure `WEBSITE_DISPATCH_TOKEN` (or equivalent) can fire `repository_dispatch` so metadata and deploy refresh without waiting for cron.

## GitHub secrets (deploy)

| Secret | Purpose |
|--------|---------|
| `CLOUDFLARE_ACCOUNT_ID` | Account `df143f08ce8d490ebf620fe776fbd375` |
| `CLOUDFLARE_PAGES_API_TOKEN` | Pages Edit + Account Settings Read |
| `REPO_METADATA_TOKEN` / dispatch tokens | `sync_repo_metadata.py` in CI |

## Cursor Cloudflare MCP

- **cloudflare-docs:** works without account auth (documentation search).
- **cloudflare-builds / bindings / observability:** require OAuth via Cursor MCP `mcp_auth`; tool descriptors stay at `mcp_auth` only until the IDE session completes Cloudflare login. Use dashboard or `gh`/Wrangler with secrets for account-specific Pages deployment lists.
