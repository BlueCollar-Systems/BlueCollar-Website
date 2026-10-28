# Agent guidance — BlueCollar Systems website

This repository is the public website for seven separate products. Steel Logic
leads with Job Clock; shapes and calculators are supporting tools. Keep the four
free PDF importers, Steel Logic and BlueCollar Tag Logic distinct.

## Work and coordination

- Use your own branch and worktree from a fresh `origin/main`. Do not edit the
  shared live checkout `C:\1BlueCollar-Website` or another worker's files.
- Follow the owner's current authorization. Use a pull request and one independent
  review for concrete defects before merging. A Git merge and a website deployment
  are separate actions.
- The authoritative private handoff is `MASTER_HANDOFF_ALL_7_REPOS_2026-10-27.md`
  in the Desktop `PDFTest Files\Q&A` folder. Read newer owner instructions and the
  latest entries in `Q&A\Achived Q&A\WORKER_STATUS_LOG.md`; older notes can be stale.
  Claim work there before starting, and report the result without private data.
- The deployed support-access route for Tag Logic was owner-approved. Preserve
  that route and its no-public-download statement unless the owner changes it.
  Do not replace it using an older handoff's access restriction.

## Website and release facts

- Edit the static HTML, CSS and JavaScript directly. There is no frontend package
  installation or compilation step. `tools/build_site.py` creates the public
  `_site/` folder from an allowlist; repository instructions and tests stay in the
  source repository and are not deployed.
- Versions and public download links follow published GitHub Releases, not branch
  tips. `repo-metadata.json`, `tools/sync_repo_metadata.py` and `nav.js` handle the
  public importer metadata. Do not expose private Steel Logic or Tag Logic assets
  through that metadata. Coordinate private-product version wording separately.
- FreeCAD uses Setup on Windows and manual installation on untested Mac/Linux
  platforms. It is not listed in Addon Manager. LibreCAD is a 2D host. Keep these
  installation and capability limits truthful.
- A push or pull request validates and builds; it does not deploy. A manual
  `website-ci` run with `deploy_production=true` publishes approved site changes.
  An importer's `product-release` dispatch can update only release metadata and
  stamped badges after the metadata-only guard passes. Do not weaken that guard
  or dispatch a deployment without the owner's authorization for publication.
- Snapshot releases are separate from deployment. Follow
  [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) and
  [docs/CLOUDFLARE_PAGES.md](docs/CLOUDFLARE_PAGES.md).

## Check the change

Run these locally before opening a pull request:

```powershell
python -I -B tools/check_python_files.py
python -I -B -m unittest discover -s tests -v
python -I -B tools/validate_private_artifacts.py
node tests/site_copy_contract_test.js
node tests/css_class_coverage_test.js
python -I -B tools/build_site.py
```

On Windows, put Git for Windows Bash on `PATH` for the shell-workflow tests.
WSL's `bash.exe` cannot open the Windows temporary script paths those tests use.

Run the other JavaScript checks listed in
[website-ci.yml](.github/workflows/website-ci.yml) when changing navigation,
downloads, support, part resolution or Report Doctor. Open the changed page in a
real browser at desktop and phone widths; check its links and the next step a
visitor sees. Do not dispatch CI repeatedly without diagnosing a failure.

## Privacy and product promises

- Use fictional jobs, marks and companies. Never publish shop PDFs, CAD files,
  customer details, tokens or credentials. The private privacy guard must pass
  before a commit and across the new commit range before a push.
- Secrets stay in GitHub/Cloudflare configuration. Do not read or print their
  values. No local credential or `.env` file belongs in `_site/`.
- Describe the current product, including install and host limits. Describe future
  features as plans, not shipped behavior. Do not invent a public Play listing,
  cloud shop sync, engineering certification, a paid tier or a price.
- Policy and Terms drafts need factual review and owner approval before
  publication. Do not invent legal identity, data practices or contractual terms.
- Heavy browser suites use the shared `heavy-browser` lock. Locks guard resources,
  not source edits; there is no free-RAM minimum. Keep evidence on
  `G:\BlueCollar-Test-Results`, never on `D:`.
