# Website Release Checklist

Use this checklist whenever you publish a new app build or update store links.

## 1) Gather release info

- Google Play URL (`https://play.google.com/store/apps/details?id=...`)
- App Store URL (`https://apps.apple.com/.../id...`)
- Optional: release date and short "what's new" notes

## 2) Update website content

- Edit `index.html`:
  - After the public listing is confirmed, replace conditional Android testing instructions with the verified public Google Play link.
  - Replace the disabled App Store button with a live `<a href="...">` link.
  - Remove "coming soon" wording once both stores are live.
- Optional: update product links in `README.md` if needed.

## 3) Commit and push

```bash
git add index.html README.md RELEASE_CHECKLIST.md
git commit -m "website: update app store release links"
git push origin main
```

## 4) Validate, then explicitly deploy when authorized

A push runs static checks only; production deployment is skipped. The
six-hour schedule and `product-update` / steel-shapes dispatches also validate
without publishing. An importer's `product-release` dispatch is the one
automatic deploy: after every check passes it refreshes only the download
metadata and version badges, and it refuses (deploying nothing) when `main`
holds other website changes that are not live yet (including a change to the
public file list in `tools/build_site.py` or to the badge stamping). A website
change like this one therefore still needs the manual run below. A shape pack
(`steel-v*`) release never deploys by itself (its release workflow publishes
with `GITHUB_TOKEN`, so no dispatch reaches the website): run the manual
deploy below after each one.

When production publication is authorized, run **website-ci** manually from
**main** with **deploy_production=true**. The default is validation only.
The deployment job re-syncs release metadata, publishes the allowlisted site,
verifies exact public metadata and routes, then commits stamped badges.

```bash
gh run list -R BlueCollar-Systems/BlueCollar-Website --workflow website-ci.yml --limit 3
```

Expected for validation-only runs:
- static-checks = success
- deploy-pages = skipped

Expected for the explicitly requested production run:
- static-checks = success
- deploy-pages = success, including public metadata and route verification

The separate auto-release workflow publishes a GitHub snapshot; it does not
deploy the live Pages site.

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
- Fix, commit, and push for validation. When checks pass and production publication is authorized, repeat the manual production run.

## Notes

### BlueCollar-Website secrets

- **Deploy:** `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_PAGES_API_TOKEN` (or `CLOUDFLARE_API_TOKEN` / `CF_API_TOKEN`)
- **Release sync:** `REPO_METADATA_TOKEN` (recommended) — read access to product repos for `tools/sync_repo_metadata.py`
- Rotate Cloudflare tokens after exposure or team access changes.
- Cloudflare token permissions: **Account → Cloudflare Pages: Edit**, **Account Settings: Read**

### Product repo secrets (SU / FC / BL / LC PDF importers)

- **`WEBSITE_DISPATCH_TOKEN`** — triggers `repository_dispatch` on `BlueCollar-Website` after `auto-release` or `release: published`
- Without it, no product dispatch is sent. Cron and pushes still validate, but live publication requires the explicit manual website-ci production run; its fresh metadata sync does not depend on receiving a product dispatch.

### Verify download metadata after a product release

```bash
curl -sS https://bluecollar-systems.com/repo-metadata.json | python -m json.tool | head -40
```

Confirm `generated_at` is recent and `latest_release.tag` matches the new GitHub release.

### Website snapshot version numbers

- **There is no v1.0.106 release; a failed run used the number up.** The
  manual `auto-release` run `38169167314` on 2026-10-11 bumped `VERSION` to
  1.0.106 and pushed that commit (`bf66a72`) to `main`, then failed at
  "Verify source and uploaded draft bytes before publication"
  (`Minted draft missing`). No `v1.0.106` tag or GitHub release was made.
  After the draft-upload fix (`3fb617c`), the next run published `v1.0.107`.
  The gap is expected; do not create a `v1.0.106` by hand.
- `auto-release` commits and pushes the version bump before it builds and
  checks the snapshot, so any failed `publish_release=true` run can use up a
  number the same way. Check
  `gh release list -R BlueCollar-Systems/BlueCollar-Website --limit 5` before
  quoting a website version.

See [README.md](README.md#github-actions-secrets-bluecollar-website-repo) for full secret tables.
