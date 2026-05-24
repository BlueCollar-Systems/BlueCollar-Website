# Website Release Checklist

Use this checklist whenever you publish a new app build or update store links.

## 1) Gather release info

- Google Play URL (`https://play.google.com/store/apps/details?id=...`)
- App Store URL (`https://apps.apple.com/.../id...`)
- Optional: release date and short "what's new" notes

## 2) Update website content

- Edit `index.html`:
  - Replace the disabled Google Play button with a live `<a href="...">` link.
  - Replace the disabled App Store button with a live `<a href="...">` link.
  - Remove "coming soon" wording once both stores are live.
- Optional: update product links in `README.md` if needed.

## 3) Commit and push

```bash
git add index.html README.md RELEASE_CHECKLIST.md
git commit -m "website: update app store release links"
git push origin main
```

## 4) Verify CI + deploy

```bash
gh run list -R BlueCollar-Systems/BlueCollar-Website --workflow website-ci.yml --limit 3
```

Expected:
- `static-checks` = success
- `deploy-pages` = success

## 5) Verify production site

```bash
curl -I https://bluecollar-systems.com/
curl -I https://bluecollar-systems.com/feedback
curl -I https://bluecollar-systems.com/robots.txt
curl -I https://bluecollar-systems.com/sitemap.xml
```

Expected:
- `/` -> `200`
- `/feedback` -> `200`
- `/robots.txt` -> `200` (`text/plain`)
- `/sitemap.xml` -> `200` (`application/xml`)

## 6) If something fails

- Open the latest failed run:
```bash
gh run list -R BlueCollar-Systems/BlueCollar-Website --workflow website-ci.yml --limit 1
gh run view <RUN_ID> -R BlueCollar-Systems/BlueCollar-Website --log
```
- Fix, commit, and push again.

## Notes

### BlueCollar-Website secrets

- **Deploy:** `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_PAGES_API_TOKEN` (or `CLOUDFLARE_API_TOKEN` / `CF_API_TOKEN`)
- **Release sync:** `REPO_METADATA_TOKEN` (recommended) — read access to product repos for `tools/sync_repo_metadata.py`
- Rotate Cloudflare tokens after exposure or team access changes.
- Cloudflare token permissions: **Account → Cloudflare Pages: Edit**, **Account Settings: Read**

### Product repo secrets (SU / FC / BL / LC PDF importers)

- **`WEBSITE_DISPATCH_TOKEN`** — triggers `repository_dispatch` on `BlueCollar-Website` after `auto-release` or `release: published`
- Without it, the live site still updates on cron (every 6h), website `main` pushes, or manual `website-ci` dispatch

### Verify download metadata after a product release

```bash
curl -sS https://bluecollar-systems.com/repo-metadata.json | python -m json.tool | head -40
```

Confirm `generated_at` is recent and `latest_release.tag` matches the new GitHub release.

See [README.md](README.md#github-actions-secrets-bluecollar-website-repo) for full secret tables.
