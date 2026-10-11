# Workflow review — 2026-10-10

Report Doctor's tag and summary **Copy** buttons now show success, use a fallback
when the Clipboard API is missing or rejects access, and explain manual recovery
if both methods fail. Tag copy buttons have specific accessible names, and a
sidecar quantity of zero displays as zero.

Malformed or unsupported parts sidecars now explain the problem. Sidecar file
read failures have a visible error. Finishing an older read cannot replace a
newer selection, and **Clear** invalidates pending reads. All sidecar values
still render as literal text. The mobile navigation closes after selecting a
link, while Escape and clicking outside retain their existing behavior.

`tools/preview_site.py` provides a localhost preview with the hosted extensionless
page routes and `/p/<part_id>` resolver route. It serves public site files and
rejects development paths, directory browsing and path traversal.

## Validation

| Check | Result |
| --- | --- |
| Python unittest discovery | 28 passed, including four new preview route tests |
| Part resolver | Seven passed |
| New Report Doctor controls | Eight passed: copy outcomes/fallbacks, zero quantity, invalid sidecars, stale file reads and Clear |
| Existing file input and hostile-sidecar tests | Passed; 47 valid report renders and 16 invalid input rejections remained correct |
| Real Edge browser | Report/file input, feedback privacy and mobile menu scenarios passed |
| Site copy contract | Passed |
| Static release metadata | Passed: eight labels, two asset filenames, six digests and four immutable releases |
| Private artifact guard and diff whitespace check | Passed |
| Ruff for new Python preview helper/tests | Passed |
| Local HTTP preview | Home, Report Doctor, Shapes, Privacy, a fictional part tag and release metadata all returned HTTP 200 |

The new Report Doctor controls and local preview route regressions are included
in the website CI job.
The site remains static HTML/CSS/JavaScript and needs no build step.

## Try the local website

The review preview is running at `http://127.0.0.1:18181/`. To start it later:

```powershell
cd C:\1BlueCollar-Website
python tools/preview_site.py
```

Open `http://127.0.0.1:8082/`. Press Ctrl+C in that terminal to stop it. The
preview provides working navigation between pages and supports the localhost
clipboard. Report Doctor processes selected JSON locally.

## Release boundary and remaining checks

These are local source improvements. The hosted website was not deployed,
GitHub release/download metadata was preserved, and no commit or push was made.
The existing iOS Coming Soon status remains truthful. Private Tag QC assets
were not exposed or copied to this public website.

Part-tag mirrors still require an explicitly published matching record; a
fictional preview tag correctly has no published data. App installation,
actual mobile deep-link resolution and cross-device tracking require their
own integration tests.
## Source-free Windows website test bundle

`C:\BlueCollar-Test-Builds\2026-10-10\Website\OPEN_BlueCollar_Website.bat`
opens `http://127.0.0.1:18341/`. Bundled Windows x64 Node 22.13.1 serves the
explicit public asset allowlist; no Python, npm, source checkout or internet is
needed for local pages. Its STOP launcher validates the owning folder. Hosted
pages, release metadata and external download/support destinations are unchanged.

The bundle contains only **35** files: public site assets, loopback server and
launchers/runtime, notices, and unmistakably fictional report/bootstrap/part
fixtures. Development paths, credentials, real shop records and runtime `data/`
are excluded. Public part-page styles moved to an external CSS file so the local
site works with a strict same-origin content policy. TEST markup alone selects
`steellogictest://` part links and localhost Report Doctor copy links; normal
source pages retain their production links. No part records were published.

Source checks passed: **28 Python tests/35 subtests**, **8 control tests**,
**7 part-resolver tests**, and the report contract's **47 valid cases/16 input
rejections**. The native extracted-package browser accepted sample file pickers,
copied the real summary/tag URL to the clipboard, resolved exact fictional
part IDs with TEST app links, and closed mobile navigation after choosing a page.

Archive: `Website-Windows-Test-2026-10-10.zip`.
SHA-256: `e96439b3d45315a39ac834b3c413972d030002261ff9ea9ec000d18016a198c5`.
All archive-member hashes were checked after extracting into a fresh folder
whose name contains spaces. **10** public routes returned HTTP 200, and **8**
private/development routes returned 404. Repeated Start reused the owning
process, changing its port while running was refused, and another bundle's
Stop launcher could not stop it. Restart/move tests preserved the Tag scanner
database and both original website/Tag previews stayed available. Package
evidence is saved as
`C:\BlueCollar-Test-Builds\2026-10-10\Tag-QC-Website-Package-Verification.json`;
the extracted servers were stopped through their own launchers.

The bundled runtime is checked on this computer; other Windows versions and
hardware need separate tests. External download/support links need internet.
Part links still require the matching register in Steel Logic TEST; a real
mobile device/OS dispatch check remains outstanding. No production content,
website deployment, commit or push was made by this review.
