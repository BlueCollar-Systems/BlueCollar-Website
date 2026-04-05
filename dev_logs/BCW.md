# LLM Context Pack — BlueCollar Website

- Generated: `2026-04-05 11:14:07`
- Project Root: `C:/1BlueCollar-Website`
- Output File: `C:/1BlueCollar-Website/dev_logs/llm_context_20260405_111407.md`
- Formatting Safety: dynamic fenced blocks are used to avoid fence collisions.

## Project Inventory

Filtered inventory for context quality. Heavy/generated folders are excluded.

- `.cfignore`: 67.00 B
- `.github/`: 2 files
- `.gitignore`: 185.00 B
- `0build_master_output_1BlueCollar-Website.cmd`: 135.00 B
- `0build_master_output_1BlueCollar-Website.py`: 1.86 KB
- `404.html`: 1.68 KB
- `__pycache__/`: 1 files
- `_headers`: 438.00 B
- `_redirects`: 58.00 B
- `favicon.ico`: 365.00 B
- `favicon.svg`: 285.00 B
- `feedback.html`: 6.75 KB
- `index.html`: 11.62 KB
- `LICENSE`: 1.05 KB
- `nav.js`: 676.00 B
- `README.md`: 1.51 KB
- `RELEASE_CHECKLIST.md`: 1.79 KB
- `repo_context_builder_core.py`: 22.10 KB
- `robots.txt`: 75.00 B
- `sitemap.xml`: 314.00 B
- `styles.css`: 7.32 KB
- `VERSION`: 7.00 B

## Repo Tree

Depth-limited tree. Full depth for selected roots, shallow for noisy areas.

```text
1BlueCollar-Website/
├── .github/
│   └── workflows/
│       ├── auto-release.yml
│       └── website-ci.yml
├── __pycache__/
│   └── repo_context_builder_core.cpython-312.pyc
├── .cfignore
├── .gitignore
├── 0build_master_output_1BlueCollar-Website.cmd
├── 0build_master_output_1BlueCollar-Website.py
├── 404.html
├── _headers
├── _redirects
├── favicon.ico
├── favicon.svg
├── feedback.html
├── index.html
├── LICENSE
├── nav.js
├── README.md
├── RELEASE_CHECKLIST.md
├── repo_context_builder_core.py
├── robots.txt
├── sitemap.xml
├── styles.css
└── VERSION
```

## Dependency Summary

No configured dependency files found.

## Missing Expected Files

### Expected Everywhere

None missing.

### Expected In Some Environments

None missing.

## Core Configuration Files

### README.md

- Path: `README.md`
- Size: `1.51 KB`
- Modified: `2026-03-31 16:39:00`

~~~markdown
# BlueCollar Systems Website

[![CI](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions/workflows/website-ci.yml/badge.svg)](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Static marketing site for **BlueCollar Systems** — precision software for fabricators, welders, and detailers.

## Products

| Product | Description | Link |
|---------|-------------|------|
| **Steel Logic** | AISC v16.0 Structural Steel Shapes Reference (mobile app) | Coming soon |
| **SketchUp PDF Importer** | Vector-accurate PDF geometry import for SketchUp | [GitHub](https://github.com/BlueCollar-Systems/SU-PDFimporter) |
| **FreeCAD PDF Importer** | PDF vector import workbench for FreeCAD | [GitHub](https://github.com/BlueCollar-Systems/FC-PDFimporter) |

## Tech Stack

- Vanilla HTML5
- [Tailwind CSS](https://tailwindcss.com) (CDN)
- Zero build dependencies

## Development

Open `index.html` in a browser. No build step required.

## Deployment

Deployed to Cloudflare Pages via GitHub Actions.

- Pushes to `main` run `website-ci`.
- `static-checks` must pass before `deploy-pages` runs.
- `deploy-pages` publishes with Wrangler to the `bluecollar-website` Pages project.
- Pushes to `main`/`master` also run `auto-release` to bump `VERSION` and publish a GitHub Release snapshot zip.

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for app launch/update steps (Google Play + iOS).

## License

MIT License. See [LICENSE](LICENSE) for details.
~~~

### RELEASE_CHECKLIST.md

- Path: `RELEASE_CHECKLIST.md`
- Size: `1.79 KB`
- Modified: `2026-03-29 18:19:44`

~~~markdown
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

- Deploy job needs repo secrets:
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID` (`df143f08ce8d490ebf620fe776fbd375`)
- Rotate the Cloudflare API token after exposure or team access changes.
~~~

### robots.txt

- Path: `robots.txt`
- Size: `75.00 B`
- Modified: `2026-03-27 17:40:26`

```text
User-agent: *
Allow: /
Sitemap: https://bluecollar-systems.com/sitemap.xml
```

### sitemap.xml

- Path: `sitemap.xml`
- Size: `314.00 B`
- Modified: `2026-04-01 20:02:18`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://bluecollar-systems.com/</loc>
    <lastmod>2026-04-01</lastmod>
  </url>
  <url>
    <loc>https://bluecollar-systems.com/feedback</loc>
    <lastmod>2026-04-01</lastmod>
  </url>
</urlset>
```

## Source Files

Included files: `15`

### .github/workflows/auto-release.yml

- Path: `.github/workflows/auto-release.yml`
- Size: `2.63 KB`
- Modified: `2026-03-31 16:38:20`

~~~yaml
name: auto-release

on:
  push:
    branches:
      - main
      - master
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: auto-release
  cancel-in-progress: false

jobs:
  release:
    if: "!startsWith(github.event.head_commit.message, 'chore: bump version to')"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Read and bump version
        id: version
        run: |
          python - <<'PY'
          import os
          import pathlib
          import re

          version_file = pathlib.Path("VERSION")
          current = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "0.0.0"
          m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", current)
          if not m:
              raise SystemExit(f"Invalid VERSION format: {current!r}")

          major, minor, patch = map(int, m.groups())
          new_version = f"{major}.{minor}.{patch + 1}"
          version_file.write_text(new_version + "\n", encoding="utf-8")

          out = pathlib.Path(os.environ["GITHUB_OUTPUT"])
          out.write_text(f"old_version={current}\nversion={new_version}\n", encoding="utf-8")
          PY

      - name: Commit version bump
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add VERSION
          git diff --cached --quiet && echo "No changes to commit" && exit 0
          git commit -m "chore: bump version to ${{ steps.version.outputs.version }}"
          git push

      - name: Build release archive
        run: |
          set -e
          ZIP="BlueCollar-Website_v${{ steps.version.outputs.version }}.zip"
          git archive --format=zip --output "$ZIP" HEAD
          ls -lh "$ZIP"

      - name: Create or update release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG="v${{ steps.version.outputs.version }}"
          ZIP="BlueCollar-Website_v${{ steps.version.outputs.version }}.zip"
          TITLE="$TAG — BlueCollar Website Snapshot"
          NOTES="Automated release snapshot from latest \`main\` commit.

          This release includes the static site source used for deployment."

          if gh release view "$TAG" >/dev/null 2>&1; then
            gh release upload "$TAG" "$ZIP" --clobber
          else
            gh release create "$TAG" --title "$TITLE" --notes "$NOTES" --latest "$ZIP"
          fi
~~~

### .github/workflows/website-ci.yml

- Path: `.github/workflows/website-ci.yml`
- Size: `2.03 KB`
- Modified: `2026-03-31 15:53:55`

```yaml
name: website-ci

on:
  push:
    branches:
      - main
      - master
  repository_dispatch:
    types:
      - steel-shapes-update
      - steel-shapes-release
  pull_request:
  workflow_dispatch:

concurrency:
  group: website-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  static-checks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Validate index.html basics
        run: |
          python - <<'PY'
          from pathlib import Path

          pages = {
              "index.html": [
                  "<!DOCTYPE html>",
                  "<title>",
                  'meta name="description"',
                  "support@bluecollar-systems.com",
              ],
              "feedback.html": [
                  "<!DOCTYPE html>",
                  "<title>",
                  'meta name="description"',
                  "support@bluecollar-systems.com",
              ],
          }

          for page, tokens in pages.items():
              path = Path(page)
              if not path.exists():
                  raise SystemExit(f"{page} not found")
              text = path.read_text(encoding="utf-8")
              missing = [t for t in tokens if t not in text]
              if missing:
                  raise SystemExit(f"{page} missing required tokens: {missing}")

          print("Static HTML checks passed.")
          PY

  deploy-pages:
    needs: static-checks
    if: |
      (github.event_name == 'push' && github.ref == 'refs/heads/main') ||
      github.event_name == 'repository_dispatch' ||
      github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Deploy to Cloudflare Pages
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
        run: npx --yes wrangler@4.48.0 pages deploy . --project-name bluecollar-website --branch main
```

### 0build_master_output_1BlueCollar-Website.cmd

- Path: `0build_master_output_1BlueCollar-Website.cmd`
- Size: `135.00 B`
- Modified: `2026-04-05 11:08:19`

```bat
@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0\%~n0.py" %*
) else (
  python "%~dp0\%~n0.py" %*
)
endlocal
```

### 0build_master_output_1BlueCollar-Website.py

- Path: `0build_master_output_1BlueCollar-Website.py`
- Size: `1.86 KB`
- Modified: `2026-04-05 11:08:19`

```python

#!/usr/bin/env python3
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from repo_context_builder_core import main_with_preset

PRESET = {
  "title": "LLM Context Pack \u2014 BlueCollar Website",
  "config_paths": [
    "README.md",
    "RELEASE_CHECKLIST.md",
    "robots.txt",
    "sitemap.xml",
    "_headers",
    "_redirects",
    ".gitignore",
    ".cfignore"
  ],
  "script_paths": [
    "0build_master_output.py",
    "0build_master_output.cmd"
  ],
  "source_roots": [
    "."
  ],
  "test_roots": [],
  "dependency_files": [
    "package.json"
  ],
  "expected_files": {
    "expected_everywhere": [
      "index.html",
      "styles.css",
      "README.md"
    ],
    "expected_some_envs": [
      "_headers",
      "_redirects",
      ".github/workflows"
    ]
  },
  "exclude_dir_names": [
    ".git",
    "dev_logs",
    "node_modules",
    "dist",
    "build"
  ],
  "exclude_file_names": [],
  "exclude_suffixes": [],
  "include_extensions": [
    ".bat",
    ".c",
    ".cfg",
    ".cmake",
    ".cmd",
    ".conf",
    ".cpp",
    ".css",
    ".dart",
    ".go",
    ".gradle",
    ".h",
    ".hpp",
    ".htm",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".lua",
    ".md",
    ".php",
    ".plist",
    ".ps1",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".svg",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml"
  ],
  "tree_full_depth_roots": [
    ".github"
  ],
  "tree_shallow_depth_roots": {
    ".git": 1
  },
  "default_tree_depth": 2,
  "navigation_grep_patterns": [
    "\\bhref=",
    "\\bwindow\\.location\\b",
    "\\bfetch\\("
  ],
  "navigation_roots": [
    "."
  ],
  "check_commands": []
}

if __name__ == "__main__":
    raise SystemExit(main_with_preset(PRESET))
```

### 404.html

- Path: `404.html`
- Size: `1.68 KB`
- Modified: `2026-04-01 20:02:08`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Page Not Found | BlueCollar Systems</title>
    <meta name="description" content="The page you're looking for doesn't exist. Head back to BlueCollar Systems.">
    <meta name="theme-color" content="#1a202c">
    <meta name="robots" content="noindex">
    <link rel="icon" href="/favicon.ico" sizes="any">

    <link rel="stylesheet" href="/styles.css">
</head>
<body class="bg-industrial text-gray-100 min-h-screen flex flex-col">

    <nav class="bg-gray-900/90 border-b border-gray-800" aria-label="Main navigation">
        <div class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
            <a href="/" class="font-bold text-xl tracking-tighter uppercase">BLUECOLLAR <span class="accent-steel">SYSTEMS</span></a>
        </div>
    </nav>

    <main class="flex-1 flex items-center justify-center px-6">
        <div class="text-center max-w-md">
            <p class="text-8xl font-extrabold accent-steel mb-4">404</p>
            <h1 class="text-3xl font-bold mb-4">Page Not Found</h1>
            <p class="text-gray-400 mb-8">The page you're looking for doesn't exist or has been moved.</p>
            <a href="/" class="inline-block bg-gray-700 hover:bg-gray-600 px-6 py-3 rounded-lg font-semibold transition">
                Back to Home
            </a>
        </div>
    </main>

    <footer class="text-center py-8 border-t border-gray-800 text-gray-400 text-sm px-6">
        <p>&copy; <script>document.write(new Date().getFullYear())</script> BlueCollar Systems. Built for the shop floor.</p>
    </footer>

</body>
</html>
```

### favicon.svg

- Path: `favicon.svg`
- Size: `285.00 B`
- Modified: `2026-03-29 17:21:04`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#1a202c"/>
  <text x="16" y="22" font-family="Arial,Helvetica,sans-serif" font-weight="800" font-size="16" fill="#63b3ed" text-anchor="middle" letter-spacing="-1">BC</text>
</svg>
```

### feedback.html

- Path: `feedback.html`
- Size: `6.75 KB`
- Modified: `2026-04-01 20:02:04`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Feedback | BlueCollar Systems</title>
    <meta name="description" content="Share feedback, report bugs, or request features for BlueCollar Systems tools — Steel Logic, SketchUp PDF Importer, and FreeCAD PDF Importer.">
    <meta name="theme-color" content="#1a202c">
    <link rel="canonical" href="https://bluecollar-systems.com/feedback">

    <meta property="og:title" content="Feedback | BlueCollar Systems">
    <meta property="og:description" content="Share feedback or report issues with BlueCollar Systems tools.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://bluecollar-systems.com/feedback">
    <meta property="og:image" content="https://bluecollar-systems.com/og-image.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Feedback | BlueCollar Systems">
    <meta name="twitter:description" content="Share feedback or report issues with BlueCollar Systems tools.">
    <meta name="twitter:image" content="https://bluecollar-systems.com/og-image.png">

    <meta name="robots" content="index, follow">
    <link rel="icon" href="/favicon.ico" sizes="any">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">

    <link rel="stylesheet" href="/styles.css">
</head>
<body class="bg-industrial text-gray-100">

    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded focus:z-50">Skip to content</a>

    <nav class="sticky top-0 bg-gray-900/90 backdrop-blur-md border-b border-gray-800 z-50" aria-label="Main navigation">
        <div class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
            <a href="/" class="font-bold text-xl tracking-tighter uppercase">BLUECOLLAR <span class="accent-steel">SYSTEMS</span></a>
            <button id="nav-toggle" class="md:hidden text-gray-300 hover:text-white focus:outline-none" aria-label="Toggle menu" aria-expanded="false" aria-controls="nav-menu">
                <svg class="w-7 h-7" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"/></svg>
            </button>
            <div id="nav-menu" class="hidden md:flex gap-8 text-sm font-medium text-gray-400 max-md:absolute max-md:top-full max-md:left-0 max-md:right-0 max-md:bg-gray-900 max-md:border-b max-md:border-gray-800 max-md:flex-col max-md:px-6 max-md:py-4 max-md:gap-4">
                <a href="/" class="hover:text-white transition">Home</a>
                <a href="/#toolkit" class="hover:text-white transition">Toolkit</a>
                <a href="/#steel-logic" class="hover:text-white transition">Steel Logic</a>
                <a href="/#about" class="hover:text-white transition">About</a>
                <a href="/#contact" class="hover:text-white transition">Contact</a>
                <a href="/feedback" class="hover:text-white transition text-white" aria-current="page">Feedback</a>
            </div>
        </div>
    </nav>

    <main id="main-content">

    <header class="max-w-4xl mx-auto px-6 py-16 text-center">
        <h1 class="text-4xl md:text-5xl font-extrabold mb-4 tracking-tight uppercase">Feedback</h1>
        <p class="text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
            Help us build better tools. Report bugs, request features, or share what's working well.
        </p>
    </header>

    <section class="max-w-4xl mx-auto px-6 pb-20">
        <div class="grid md:grid-cols-2 gap-8 mb-12">

            <div class="bg-gray-800/50 p-8 rounded-xl border border-gray-700">
                <div class="text-3xl mb-4">&#9993;</div>
                <h2 class="text-xl font-bold mb-3">Email Us Directly</h2>
                <p class="text-gray-400 mb-6">Best for detailed bug reports, screenshots, or PDF samples that aren't importing correctly.</p>
                <a href="mailto:support@bluecollar-systems.com" class="inline-block bg-gray-700 hover:bg-gray-600 px-6 py-3 rounded-lg font-semibold transition">
                    support@bluecollar-systems.com
                </a>
            </div>

            <div class="bg-gray-800/50 p-8 rounded-xl border border-gray-700">
                <div class="text-3xl mb-4">&#128736;</div>
                <h2 class="text-xl font-bold mb-3">GitHub Issues</h2>
                <p class="text-gray-400 mb-6">File a bug or feature request directly on the relevant project repository.</p>
                <div class="flex flex-col gap-3">
                    <a href="https://github.com/BlueCollar-Systems/SU-PDFimporter/issues" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">
                        SketchUp PDF Importer &rarr;
                    </a>
                    <a href="https://github.com/BlueCollar-Systems/FC-PDFimporter/issues" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">
                        FreeCAD PDF Importer &rarr;
                    </a>
                </div>
            </div>

        </div>

        <div class="bg-gray-800/50 p-8 rounded-xl border border-gray-700">
            <h2 class="text-xl font-bold mb-3">What makes a great bug report</h2>
            <ul role="list" class="text-gray-400 space-y-2 list-disc list-inside">
                <li>Which tool and version you're using (Steel Logic, SU Importer v3.6, FC Importer v3.6, etc.)</li>
                <li>What you expected to happen vs. what actually happened</li>
                <li>Steps to reproduce the issue</li>
                <li>For importer bugs: the PDF file (or a sample), the preset you used, and a screenshot of the result</li>
                <li>Your platform (SketchUp 2024/2025, FreeCAD 0.21/1.0, Android, iOS, etc.)</li>
            </ul>
        </div>
    </section>

    </main>

    <footer class="text-center py-12 border-t border-gray-800 text-gray-400 text-sm px-6">
        <p class="mb-4">&copy; <script>document.write(new Date().getFullYear())</script> BlueCollar Systems. Built for the shop floor.</p>
        <p class="max-w-2xl mx-auto text-xs uppercase tracking-tighter text-gray-400">
            Disclaimer: All structural data provided by BlueCollar Systems tools is for reference only.
            All output should be verified by a licensed professional engineer before fabrication or construction.
        </p>
    </footer>

<script src="/nav.js"></script>
</body>
</html>
```

### index.html

- Path: `index.html`
- Size: `11.62 KB`
- Modified: `2026-04-04 03:30:11`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>BlueCollar Systems | Professional Steel Tools & PDF Importers</title>
    <meta name="description" content="Precision software for fabricators, welders, and detailers. Get blueprint-accurate steel shapes and powerful PDF import tools for SketchUp and FreeCAD.">
    <meta name="keywords" content="Steel Shapes, AISC, Fabricator Tools, SketchUp PDF Importer, FreeCAD PDF Importer, Steel Detailing Software">
    <meta name="theme-color" content="#1a202c">
    <link rel="canonical" href="https://bluecollar-systems.com/">

    <meta property="og:title" content="BlueCollar Systems | Tools for the Shop Floor">
    <meta property="og:description" content="Professional-grade steel shape generators and CAD importers for detailers.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://bluecollar-systems.com/">
    <meta property="og:image" content="https://bluecollar-systems.com/og-image.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="BlueCollar Systems | Tools for the Shop Floor">
    <meta name="twitter:description" content="Precision software for fabricators, welders, and detailers.">
    <meta name="twitter:image" content="https://bluecollar-systems.com/og-image.png">

    <meta name="robots" content="index, follow">
    <link rel="icon" href="/favicon.ico" sizes="any">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">

    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "BlueCollar Systems",
      "url": "https://bluecollar-systems.com",
      "description": "Precision software for fabricators, welders, and detailers.",
      "contactPoint": {
        "@type": "ContactPoint",
        "email": "support@bluecollar-systems.com",
        "contactType": "customer support"
      },
      "sameAs": ["https://github.com/BlueCollar-Systems"]
    }
    </script>

    <link rel="stylesheet" href="/styles.css">
</head>
<body class="bg-industrial text-gray-100">

    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded focus:z-50">Skip to content</a>

    <nav class="sticky top-0 bg-gray-900/90 backdrop-blur-md border-b border-gray-800 z-50" aria-label="Main navigation">
        <div class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
            <a href="/" class="font-bold text-xl tracking-tighter uppercase">BLUECOLLAR <span class="accent-steel">SYSTEMS</span></a>
            <button id="nav-toggle" class="md:hidden text-gray-300 hover:text-white focus:outline-none" aria-label="Toggle menu" aria-expanded="false" aria-controls="nav-menu">
                <svg class="w-7 h-7" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"/></svg>
            </button>
            <div id="nav-menu" class="hidden md:flex gap-8 text-sm font-medium text-gray-400 max-md:absolute max-md:top-full max-md:left-0 max-md:right-0 max-md:bg-gray-900 max-md:border-b max-md:border-gray-800 max-md:flex-col max-md:px-6 max-md:py-4 max-md:gap-4">
                <a href="/" class="hover:text-white transition" aria-current="page">Home</a>
                <a href="#toolkit" class="hover:text-white transition">Toolkit</a>
                <a href="#steel-logic" class="hover:text-white transition">Steel Logic</a>
                <a href="#about" class="hover:text-white transition">About</a>
                <a href="#contact" class="hover:text-white transition">Contact</a>
                <a href="/feedback" class="hover:text-white transition">Feedback</a>
            </div>
        </div>
    </nav>

    <main id="main-content">

    <header class="max-w-6xl mx-auto px-6 py-24 text-center">
        <h1 class="text-4xl md:text-6xl font-extrabold mb-6 tracking-tight uppercase">Software for the <span class="accent-steel">Shop Floor</span></h1>
        <p class="text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            Eliminate guesswork and manual calculations. Get blueprint-accurate steel shapes and vector PDF tools designed specifically for fabricators and detailers.
        </p>
    </header>

    <!-- STEEL LOGIC APP -->
    <section id="steel-logic" class="max-w-4xl mx-auto px-6 py-16 border-t border-gray-800">
        <div class="bg-gray-800/50 p-10 rounded-2xl border border-gray-700 text-center">
            <h2 class="text-3xl font-bold mb-4">Steel Logic</h2>
            <p class="text-lg text-gray-400 mb-2">AISC v16.0 Structural Steel Shapes Reference</p>
            <p class="text-gray-400 mb-8 max-w-xl mx-auto">Every shape. Every property. Right in your pocket. Blueprint-accurate SVGs, shop floor calculators, inventory tracking, and more.</p>
            <div class="flex flex-wrap justify-center gap-4 mb-6">
                <button disabled aria-disabled="true" aria-label="Google Play - Coming soon" class="btn-safety text-white font-bold py-4 px-8 rounded-lg shadow-xl transition text-base uppercase tracking-wide flex items-center gap-3 opacity-75 cursor-not-allowed" title="Coming soon to Google Play">
                    <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 0 1-.61-.92V2.734a1 1 0 0 1 .609-.92zm10.89 10.893l2.302 2.302-10.937 6.333 8.635-8.635zm3.199-1.38l2.473 1.431a1 1 0 0 1 0 1.484l-2.473 1.431-2.552-2.552 2.552-2.794zM5.864 3.458L16.8 9.791l-2.302 2.302-8.634-8.635z"/></svg>
                    Google Play
                </button>
                <button disabled aria-disabled="true" aria-label="App Store - Coming soon" class="bg-gray-700 font-bold py-4 px-8 rounded-lg shadow-xl transition text-base uppercase tracking-wide flex items-center gap-3 opacity-75 cursor-not-allowed" title="Coming soon to the App Store">
                    <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24" aria-hidden="true"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
                    App Store
                </button>
            </div>
            <p class="text-sm text-gray-400">Android coming soon. iOS in development.</p>
        </div>
    </section>

    <!-- TOOLKIT -->
    <section id="toolkit" class="max-w-6xl mx-auto px-6 py-20 border-t border-gray-800">
        <h2 class="text-3xl font-bold mb-12 text-center uppercase tracking-widest text-gray-400">The Toolkit</h2>
        <div class="grid md:grid-cols-2 gap-8">
            <div class="bg-gray-800/50 p-8 rounded-xl border border-gray-700 hover:border-blue-400 transition group">
                <h3 class="text-2xl font-bold mb-3 group-hover:text-blue-400">SketchUp PDF Importer</h3>
                <p class="text-gray-400 mb-6">Import vector-accurate PDF geometry directly into your SketchUp models. Built for Ruby-based efficiency and clean workflows.</p>
                <a href="https://github.com/BlueCollar-Systems/SU-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
            </div>
            <div class="bg-gray-800/50 p-8 rounded-xl border border-gray-700 hover:border-blue-400 transition group">
                <h3 class="text-2xl font-bold mb-3 group-hover:text-blue-400">FreeCAD PDF Importer</h3>
                <p class="text-gray-400 mb-6">Bridge the gap between 2D blueprints and 3D CAD modeling with our robust FreeCAD extension.</p>
                <a href="https://github.com/BlueCollar-Systems/FC-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
            </div>
            <div class="bg-gray-800/50 p-8 rounded-xl border border-gray-700 hover:border-blue-400 transition group">
                <h3 class="text-2xl font-bold mb-3 group-hover:text-blue-400">Blender PDF Importer</h3>
                <p class="text-gray-400 mb-6">Import PDF vector drawings as native Blender geometry. Curves, Collections, Materials.</p>
                <a href="https://github.com/BlueCollar-Systems/BL-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
            </div>
            <div class="bg-gray-800/50 p-8 rounded-xl border border-gray-700 hover:border-blue-400 transition group">
                <h3 class="text-2xl font-bold mb-3 group-hover:text-blue-400">LibreCAD PDF Converter</h3>
                <p class="text-gray-400 mb-6">Convert PDF drawings to DXF for LibreCAD, AutoCAD, DraftSight, QCAD. CLI + GUI.</p>
                <a href="https://github.com/BlueCollar-Systems/LC-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
            </div>
        </div>
    </section>

    <!-- ABOUT -->
    <section id="about" class="bg-gray-900/50 py-20 border-y border-gray-800">
        <div class="max-w-4xl mx-auto px-6 text-center">
            <h2 class="text-3xl font-bold mb-8">Our Mission</h2>
            <p class="text-lg text-gray-400 leading-relaxed italic">
                "BlueCollar Systems was founded on the belief that software should work as hard as the people using it. We build lightweight, high-precision tools that live in your pocket or on your workstation&mdash;not behind complex corporate paywalls."
            </p>
        </div>
    </section>

    <!-- CONTACT -->
    <section id="contact" class="max-w-4xl mx-auto px-6 py-24 text-center">
        <h2 class="text-3xl font-bold mb-4">Get In Touch</h2>
        <p class="text-gray-400 mb-10">Have a feature request or need support with a tool? We're here to help.</p>
        <div class="bg-gray-800/50 p-8 rounded-2xl border border-gray-700 inline-block w-full max-w-md">
            <p class="text-sm text-gray-400 uppercase mb-2">Support Email</p>
            <a href="mailto:support@bluecollar-systems.com" class="text-2xl font-bold text-blue-400 hover:underline">
                support@bluecollar-systems.com
            </a>
            <p class="mt-6 text-gray-400 text-sm">Want to report a bug or request a feature? <a href="/feedback" class="text-blue-400 hover:underline">Visit our Feedback page &rarr;</a></p>
        </div>
    </section>

    </main>

    <footer class="text-center py-12 border-t border-gray-800 text-gray-400 text-sm px-6">
        <p class="mb-4">&copy; <script>document.write(new Date().getFullYear())</script> BlueCollar Systems. Built for the shop floor.</p>
        <p class="max-w-2xl mx-auto text-xs uppercase tracking-tighter text-gray-400">
            Disclaimer: All structural data provided by BlueCollar Systems tools is for reference only.
            All output should be verified by a licensed professional engineer before fabrication or construction.
        </p>
    </footer>

<script src="/nav.js"></script>
</body>
</html>
```

### nav.js

- Path: `nav.js`
- Size: `676.00 B`
- Modified: `2026-04-01 20:00:39`

```javascript
(function() {
  var btn = document.getElementById('nav-toggle');
  var menu = document.getElementById('nav-menu');
  if (!btn || !menu) return;
  btn.addEventListener('click', function() {
    menu.classList.toggle('hidden');
    var isNowOpen = !menu.classList.contains('hidden');
    btn.setAttribute('aria-expanded', String(isNowOpen));
    if (isNowOpen) { var first = menu.querySelector('a'); if (first) first.focus(); }
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && !menu.classList.contains('hidden')) {
      menu.classList.add('hidden');
      btn.setAttribute('aria-expanded', 'false');
      btn.focus();
    }
  });
})();
```

### README.md

- Path: `README.md`
- Size: `1.51 KB`
- Modified: `2026-03-31 16:39:00`

~~~markdown
# BlueCollar Systems Website

[![CI](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions/workflows/website-ci.yml/badge.svg)](https://github.com/BlueCollar-Systems/BlueCollar-Website/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Static marketing site for **BlueCollar Systems** — precision software for fabricators, welders, and detailers.

## Products

| Product | Description | Link |
|---------|-------------|------|
| **Steel Logic** | AISC v16.0 Structural Steel Shapes Reference (mobile app) | Coming soon |
| **SketchUp PDF Importer** | Vector-accurate PDF geometry import for SketchUp | [GitHub](https://github.com/BlueCollar-Systems/SU-PDFimporter) |
| **FreeCAD PDF Importer** | PDF vector import workbench for FreeCAD | [GitHub](https://github.com/BlueCollar-Systems/FC-PDFimporter) |

## Tech Stack

- Vanilla HTML5
- [Tailwind CSS](https://tailwindcss.com) (CDN)
- Zero build dependencies

## Development

Open `index.html` in a browser. No build step required.

## Deployment

Deployed to Cloudflare Pages via GitHub Actions.

- Pushes to `main` run `website-ci`.
- `static-checks` must pass before `deploy-pages` runs.
- `deploy-pages` publishes with Wrangler to the `bluecollar-website` Pages project.
- Pushes to `main`/`master` also run `auto-release` to bump `VERSION` and publish a GitHub Release snapshot zip.

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for app launch/update steps (Google Play + iOS).

## License

MIT License. See [LICENSE](LICENSE) for details.
~~~

### RELEASE_CHECKLIST.md

- Path: `RELEASE_CHECKLIST.md`
- Size: `1.79 KB`
- Modified: `2026-03-29 18:19:44`

~~~markdown
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

- Deploy job needs repo secrets:
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID` (`df143f08ce8d490ebf620fe776fbd375`)
- Rotate the Cloudflare API token after exposure or team access changes.
~~~

### repo_context_builder_core.py

- Path: `repo_context_builder_core.py`
- Size: `22.10 KB`
- Modified: `2026-04-05 11:11:41`

```python

#!/usr/bin/env python3
"""
Generic LLM Context Builder

Features:
- High-signal project snapshot for LLM analysis
- Depth-limited file tree
- Exclusion/skip report
- Dependency summary
- Missing expected files report
- Optional command checks via --run-checks
- Safe truncation and light secret redaction
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

MAX_FILE_LINES = 3000
MAX_HEAD_LINES = 2000
MAX_TAIL_LINES = 500

DEFAULT_REDACTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"""(?im)(\b(?:api[_-]?key|token|secret|password|client[_-]?secret)\b\s*[:=]\s*)(["'])([^"']+)\2"""
        ),
        r"\1\2<REDACTED>\2",
    ),
    (
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "<REDACTED_PRIVATE_KEY_BLOCK>",
    ),
]

TEXT_PREVIEW_EXTENSIONS = {
    ".py", ".rb", ".dart", ".js", ".ts", ".tsx", ".jsx", ".css", ".scss",
    ".html", ".htm", ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".sql", ".xml", ".plist", ".kts", ".gradle",
    ".cmake", ".sh", ".ps1", ".bat", ".cmd", ".c", ".cpp", ".h", ".hpp",
    ".java", ".kt", ".swift", ".go", ".rs", ".php", ".r", ".lua", ".svg"
}

def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def _choose_fence(text: str) -> str:
    max_backticks = max((len(m.group(0)) for m in re.finditer(r"`+", text)), default=0)
    max_tildes = max((len(m.group(0)) for m in re.finditer(r"~+", text)), default=0)
    if max_backticks <= max_tildes:
        return "`" * max(3, max_backticks + 1)
    return "~" * max(3, max_tildes + 1)

def _detect_language(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    mapping = {
        ".py": "python",".rb": "ruby",".dart": "dart",".js": "javascript",".ts": "typescript",
        ".tsx": "tsx",".jsx": "jsx",".css": "css",".scss": "scss",".html": "html",".htm": "html",
        ".json": "json",".yaml": "yaml",".yml": "yaml",".xml": "xml",".plist": "xml",".md": "markdown",
        ".txt": "text",".sql": "sql",".toml": "toml",".kts": "kotlin",".gradle": "groovy",".sh": "bash",
        ".ps1": "powershell",".bat": "bat",".cmd": "bat",".svg": "xml",
    }
    if suffix == ".cmake" or name == "cmakelists.txt":
        return "cmake"
    return mapping.get(suffix, "")

def _redact(text: str) -> str:
    out = text
    for pattern, replacement in DEFAULT_REDACTION_PATTERNS:
        out = pattern.sub(replacement, out)
    return out

def _truncate_text(text: str):
    lines = text.splitlines()
    if len(lines) <= MAX_FILE_LINES:
        return text, False
    head = lines[:MAX_HEAD_LINES]
    tail = lines[-MAX_TAIL_LINES:]
    clipped = "\n".join(head) + "\n\n# ... SNIPPED ...\n\n" + "\n".join(tail)
    return clipped, True

def _write_heading(out, title: str, level: int = 1) -> None:
    out.write(f"{'#' * max(1, level)} {title}\n\n")

def _write_fenced_block(out, content: str, language: str = "") -> None:
    fence = _choose_fence(content)
    out.write(f"{fence}{language}\n")
    out.write(content)
    if not content.endswith("\n"):
        out.write("\n")
    out.write(f"{fence}\n\n")

def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return path.as_posix()

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

class ContextBuilder:
    def __init__(self, preset: Dict):
        self.preset = preset
        self.project_root = Path(preset.get("project_root", Path(__file__).resolve().parent)).resolve()
        self.dev_logs = self.project_root / preset.get("dev_logs_dir", "dev_logs")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path = self.dev_logs / f"llm_context_{ts}.md"
        self.latest_path = self.dev_logs / "latest_llm_context.md"
        self.skip_reasons = defaultdict(list)
        self.truncated_files = []
        self.previewed_files = []

    @property
    def exclude_dir_names(self):
        return set(self.preset.get("exclude_dir_names", []))

    @property
    def exclude_file_names(self):
        return set(self.preset.get("exclude_file_names", []))

    @property
    def exclude_suffixes(self):
        return tuple(self.preset.get("exclude_suffixes", []))

    @property
    def include_extensions(self):
        return set(self.preset.get("include_extensions", sorted(TEXT_PREVIEW_EXTENSIONS)))

    def is_excluded_dir(self, path: Path) -> bool:
        name = path.name
        for pattern in self.exclude_dir_names:
            if pattern.startswith("*.") and name.endswith(pattern[1:]):
                return True
            if name == pattern:
                return True
        return False

    def is_previewable_file(self, path: Path) -> bool:
        if path.name in self.exclude_file_names:
            self.skip_reasons["excluded_name"].append(_safe_rel(path, self.project_root))
            return False
        if any(path.name.endswith(sfx) for sfx in self.exclude_suffixes):
            self.skip_reasons["excluded_suffix"].append(_safe_rel(path, self.project_root))
            return False
        if path.suffix.lower() in self.include_extensions or path.name.lower() == "cmakelists.txt":
            return True
        self.skip_reasons["non_text_or_unlisted_extension"].append(_safe_rel(path, self.project_root))
        return False

    def iter_filtered_files(self, root: Path):
        for current_root, dirs, files in os.walk(root):
            root_path = Path(current_root)
            original_dirs = list(dirs)
            dirs[:] = [d for d in sorted(dirs) if not self.is_excluded_dir(root_path / d)]
            for d in original_dirs:
                if d not in dirs:
                    self.skip_reasons["excluded_directory"].append(_safe_rel(root_path / d, self.project_root))
            for file_name in sorted(files):
                file_path = root_path / file_name
                if self.is_previewable_file(file_path):
                    yield file_path

    def collect_files(self, relative_roots):
        items = []
        for rel in relative_roots:
            base = self.project_root / rel
            if not base.exists():
                continue
            if base.is_file():
                if self.is_previewable_file(base):
                    items.append(base)
                continue
            for path in self.iter_filtered_files(base):
                items.append(path)
        return sorted(set(items))

    def collect_named_files(self, relative_paths):
        paths = []
        for rel in relative_paths:
            candidate = self.project_root / rel
            if candidate.exists() and candidate.is_file() and self.is_previewable_file(candidate):
                paths.append(candidate)
        return paths

    def file_metadata(self, path: Path) -> str:
        stat = path.stat()
        rel = _safe_rel(path, self.project_root)
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return f"- Path: `{rel}`\n- Size: `{_format_size(stat.st_size)}`\n- Modified: `{modified}`\n"

    def write_file_section(self, out, path: Path) -> None:
        rel = _safe_rel(path, self.project_root)
        _write_heading(out, rel, 3)
        out.write(self.file_metadata(path))
        out.write("\n")
        text = _redact(_read_text(path))
        text, truncated = _truncate_text(text)
        if truncated:
            self.truncated_files.append(rel)
            out.write("- Note: File was truncated for token safety.\n\n")
        self.previewed_files.append(rel)
        _write_fenced_block(out, text, _detect_language(path))

    def top_level_inventory(self):
        rows = []
        for child in sorted(self.project_root.iterdir(), key=lambda p: p.name.lower()):
            if self.is_excluded_dir(child):
                continue
            if child.is_dir():
                count = 0
                for _, dirs, files in os.walk(child):
                    dirs[:] = [d for d in dirs if d not in self.exclude_dir_names]
                    count += len(files)
                rows.append((child.name + "/", count, True))
            else:
                rows.append((child.name, child.stat().st_size, False))
        return rows

    def write_inventory_section(self, out) -> None:
        _write_heading(out, "Project Inventory", 2)
        out.write("Filtered inventory for context quality. Heavy/generated folders are excluded.\n\n")
        for name, metric, is_dir in self.top_level_inventory():
            out.write(f"- `{name}`: {metric} files\n" if is_dir else f"- `{name}`: {_format_size(metric)}\n")
        out.write("\n")

    def _tree_depth_for(self, first_part: str) -> int:
        full = set(self.preset.get("tree_full_depth_roots", []))
        shallow = self.preset.get("tree_shallow_depth_roots", {})
        if first_part in full:
            return 99
        return int(shallow.get(first_part, self.preset.get("default_tree_depth", 2)))

    def _build_tree_lines(self):
        root = self.project_root
        lines = [f"{root.name}/"]
        excluded = self.exclude_dir_names
        def add_dir(dir_path: Path, prefix: str = ""):
            try:
                rel_parts = dir_path.relative_to(root).parts
            except Exception:
                rel_parts = ()
            entries = []
            try:
                for p in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    if p.is_dir() and p.name in excluded:
                        continue
                    entries.append(p)
            except Exception:
                return
            for i, entry in enumerate(entries):
                last = i == len(entries) - 1
                branch = "└── " if last else "├── "
                lines.append(prefix + branch + entry.name + ("/" if entry.is_dir() else ""))
                if entry.is_dir():
                    rel = entry.relative_to(root)
                    rel_parts = rel.parts
                    depth_limit = self._tree_depth_for(rel_parts[0] if rel_parts else "")
                    if len(rel_parts) < depth_limit:
                        add_dir(entry, prefix + ("    " if last else "│   "))
        add_dir(root, "")
        return lines

    def write_tree_section(self, out) -> None:
        _write_heading(out, "Repo Tree", 2)
        out.write("Depth-limited tree. Full depth for selected roots, shallow for noisy areas.\n\n")
        _write_fenced_block(out, "\n".join(self._build_tree_lines()), "text")

    def parse_dependency_summary(self):
        summary = defaultdict(list)
        for rel in self.preset.get("dependency_files", []):
            path = self.project_root / rel
            if not path.exists() or not path.is_file():
                continue
            text = _read_text(path)
            low = rel.lower()
            if path.name == "pubspec.yaml":
                current = None
                for line in text.splitlines():
                    if re.match(r"^\s*dependencies:\s*$", line):
                        current = "dependencies"; continue
                    if re.match(r"^\s*dev_dependencies:\s*$", line):
                        current = "dev_dependencies"; continue
                    if re.match(r"^\S", line):
                        current = None
                    if current and re.match(r"^\s{2,}[A-Za-z0-9_.-]+:\s*", line):
                        name = line.strip().split(":", 1)[0]
                        if name != "sdk":
                            summary[current].append(line.strip())
            elif low.endswith("requirements.txt") or low.endswith("requirements-dev.txt"):
                key = path.name
                for line in text.splitlines():
                    s = line.strip()
                    if s and not s.startswith("#"):
                        summary[key].append(s)
            elif low.endswith("pyproject.toml"):
                section = None
                for line in text.splitlines():
                    s = line.strip()
                    if s.startswith("[tool.poetry.dependencies]"):
                        section = "poetry_dependencies"
                    elif s.startswith("[tool.poetry.group.dev.dependencies]"):
                        section = "poetry_dev_dependencies"
                    elif s.startswith("["):
                        section = None
                    elif "=" in s and section in {"poetry_dependencies", "poetry_dev_dependencies"}:
                        summary[section].append(s)
            elif low.endswith("package.json"):
                try:
                    data = json.loads(text)
                    for key in ("dependencies", "devDependencies"):
                        for name, version in sorted(data.get(key, {}).items()):
                            summary[key].append(f"{name}: {version}")
                except Exception:
                    summary[path.name].append("<failed to parse package.json>")
        return summary

    def write_dependency_summary(self, out) -> None:
        _write_heading(out, "Dependency Summary", 2)
        deps = self.parse_dependency_summary()
        if not deps:
            out.write("No configured dependency files found.\n\n")
            return
        for section, items in deps.items():
            out.write(f"### {section}\n\n")
            _write_fenced_block(out, "\n".join(items) if items else "None detected.", "text")

    def write_missing_expected_files(self, out) -> None:
        _write_heading(out, "Missing Expected Files", 2)
        for group, key in (("Expected Everywhere", "expected_everywhere"), ("Expected In Some Environments", "expected_some_envs")):
            out.write(f"### {group}\n\n")
            expected = self.preset.get("expected_files", {}).get(key, [])
            missing = [rel for rel in expected if not (self.project_root / rel).exists()]
            if missing:
                _write_fenced_block(out, "\n".join(missing), "text")
            else:
                out.write("None missing.\n\n")

    def write_navigation_inventory(self, out) -> None:
        patterns = self.preset.get("navigation_grep_patterns", [])
        roots = self.preset.get("navigation_roots", self.preset.get("source_roots", []))
        if not patterns or not roots:
            return
        compiled = [re.compile(p) for p in patterns]
        matches = []
        for path in self.collect_files(roots):
            try:
                text = _read_text(path)
            except Exception:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for pat in compiled:
                    if pat.search(line):
                        matches.append(f"{_safe_rel(path, self.project_root)}:{line_no}: {line.strip()}")
                        break
        _write_heading(out, "Navigation Call-Site Inventory", 2)
        if not matches:
            out.write("No configured navigation call-sites found.\n\n")
            return
        _write_fenced_block(out, "\n".join(matches[:500]), "text")
        if len(matches) > 500:
            out.write(f"- Note: {len(matches) - 500} additional matches omitted.\n\n")

    def write_sqlite_section(self, out) -> None:
        db_paths = self.preset.get("sqlite_paths", [])
        if not db_paths:
            return
        _write_heading(out, "SQLite Schema Snapshot", 2)
        db_path = None
        for rel in db_paths:
            candidate = self.project_root / rel
            if candidate.exists():
                db_path = candidate
                break
        if db_path is None:
            out.write("No SQLite database found in configured locations.\n\n")
            return
        out.write(f"- Database: `{_safe_rel(db_path, self.project_root)}`\n")
        out.write(f"- Size: `{_format_size(db_path.stat().st_size)}`\n\n")
        try:
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = [r[0] for r in cur.fetchall()]
                out.write("Tables:\n")
                for name in tables:
                    out.write(f"- `{name}`\n")
                out.write("\n")
        except Exception as exc:
            out.write(f"Database read failed: {exc}\n\n")

    def run_checks(self):
        results = []
        for cmd in self.preset.get("check_commands", []):
            try:
                proc = subprocess.run(
                    cmd, cwd=self.project_root, text=True, capture_output=True,
                    shell=isinstance(cmd, str), timeout=int(self.preset.get("check_timeout_seconds", 180)),
                )
                output = (proc.stdout or "") + ("\n" if proc.stdout and proc.stderr else "") + (proc.stderr or "")
                results.append((cmd if isinstance(cmd, str) else " ".join(cmd), proc.returncode, output.strip()))
            except Exception as exc:
                results.append((cmd if isinstance(cmd, str) else " ".join(cmd), 999, f"Check failed to start: {exc}"))
        return results

    def write_checks_section(self, out, run_checks: bool) -> None:
        _write_heading(out, "Optional Checks", 2)
        if not run_checks:
            out.write("Checks were not run. Use `--run-checks` to capture configured command output.\n\n")
            return
        results = self.run_checks()
        if not results:
            out.write("No check commands configured for this repo.\n\n")
            return
        for cmd, code, output in results:
            out.write("### Command\n\n")
            _write_fenced_block(out, cmd, "text")
            out.write(f"- Exit code: `{code}`\n\n")
            _write_fenced_block(out, output or "<no output>", "text")

    def write_exclusion_report(self, out) -> None:
        _write_heading(out, "Exclusion / Skip Report", 2)
        if not self.skip_reasons and not self.truncated_files:
            out.write("No exclusions or truncations recorded.\n\n")
            return
        for reason in sorted(self.skip_reasons):
            items = sorted(set(self.skip_reasons[reason]))
            out.write(f"### {reason.replace('_', ' ').title()}\n\n")
            out.write(f"- Count: {len(items)}\n\n")
            preview = items[:200]
            _write_fenced_block(out, "\n".join(preview), "text")
            if len(items) > len(preview):
                out.write(f"- Note: {len(items) - len(preview)} additional items omitted.\n\n")
        if self.truncated_files:
            out.write("### Truncated Files\n\n")
            _write_fenced_block(out, "\n".join(sorted(set(self.truncated_files))), "text")

    def build(self, run_checks: bool = False):
        self.dev_logs.mkdir(parents=True, exist_ok=True)
        config_files = self.collect_named_files(self.preset.get("config_paths", []))
        script_files = self.collect_named_files(self.preset.get("script_paths", []))
        source_files = self.collect_files(self.preset.get("source_roots", []))
        test_files = self.collect_files(self.preset.get("test_roots", []))
        with self.output_path.open("w", encoding="utf-8", newline="\n") as out:
            _write_heading(out, self.preset.get("title", "LLM Context Pack"), 1)
            out.write(f"- Generated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n")
            out.write(f"- Project Root: `{self.project_root.as_posix()}`\n")
            out.write(f"- Output File: `{self.output_path.as_posix()}`\n")
            out.write("- Formatting Safety: dynamic fenced blocks are used to avoid fence collisions.\n\n")
            self.write_inventory_section(out)
            self.write_tree_section(out)
            self.write_dependency_summary(out)
            self.write_missing_expected_files(out)
            _write_heading(out, "Core Configuration Files", 2)
            if not config_files:
                out.write("No configuration files were found.\n\n")
            for path in config_files:
                self.write_file_section(out, path)
            _write_heading(out, "Source Files", 2)
            out.write(f"Included files: `{len(source_files)}`\n\n")
            for path in source_files:
                self.write_file_section(out, path)
            _write_heading(out, "Test Files", 2)
            out.write(f"Included files: `{len(test_files)}`\n\n")
            for path in test_files:
                self.write_file_section(out, path)
            _write_heading(out, "Project Scripts", 2)
            if not script_files:
                out.write("No script files were found.\n\n")
            for path in script_files:
                self.write_file_section(out, path)
            self.write_navigation_inventory(out)
            self.write_sqlite_section(out)
            self.write_checks_section(out, run_checks)
            self.write_exclusion_report(out)
            _write_heading(out, "End of Pack", 2)
            out.write("Context pack completed.\n")
        shutil.copyfile(self.output_path, self.latest_path)
        return self.output_path

def main_with_preset(preset: Dict) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-checks", action="store_true", help="Run configured optional checks and append output")
    parser.add_argument("--project-root", default=None, help="Override detected project root")
    args = parser.parse_args()
    if args.project_root:
        preset = dict(preset)
        preset["project_root"] = args.project_root
    try:
        builder = ContextBuilder(preset)
        output = builder.build(run_checks=args.run_checks)
        print("=" * 72)
        print("LLM context pack complete")
        print(f"Output: {output}")
        print(f"Latest: {builder.latest_path}")
        print("=" * 72)
        return 0
    except Exception as exc:
        print("Build failed.")
        print(str(exc))
        print(traceback.format_exc())
        return 1
```

### robots.txt

- Path: `robots.txt`
- Size: `75.00 B`
- Modified: `2026-03-27 17:40:26`

```text
User-agent: *
Allow: /
Sitemap: https://bluecollar-systems.com/sitemap.xml
```

### sitemap.xml

- Path: `sitemap.xml`
- Size: `314.00 B`
- Modified: `2026-04-01 20:02:18`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://bluecollar-systems.com/</loc>
    <lastmod>2026-04-01</lastmod>
  </url>
  <url>
    <loc>https://bluecollar-systems.com/feedback</loc>
    <lastmod>2026-04-01</lastmod>
  </url>
</urlset>
```

### styles.css

- Path: `styles.css`
- Size: `7.32 KB`
- Modified: `2026-04-02 17:26:57`

```css
/* BlueCollar Systems — Static CSS (replaces Tailwind CDN) */

/* ─── Reset & Base ─── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; line-height: 1.5; -webkit-text-size-adjust: 100%; }
body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
a { color: inherit; text-decoration: inherit; }
img, svg { display: block; max-width: 100%; }
button { cursor: pointer; font: inherit; color: inherit; }
ul[role="list"] { list-style-position: inside; }

/* ─── Brand tokens ─── */
.bg-industrial { background-color: #1a202c; }
.accent-steel { color: #63b3ed; }
.btn-safety { background-color: #ed8936; }
.btn-safety:hover { background-color: #dd6b20; }

/* ─── Layout utilities ─── */
.min-h-screen { min-height: 100vh; }
.flex { display: flex; }
.flex-1 { flex: 1 1 0%; }
.flex-col { flex-direction: column; }
.flex-wrap { flex-wrap: wrap; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.gap-3 { gap: 0.75rem; }
.gap-4 { gap: 1rem; }
.gap-8 { gap: 2rem; }
.inline-block { display: inline-block; }
.w-full { width: 100%; }
.max-w-md { max-width: 28rem; }
.max-w-xl { max-width: 36rem; }
.max-w-2xl { max-width: 42rem; }
.max-w-4xl { max-width: 56rem; }
.max-w-6xl { max-width: 72rem; }
.mx-auto { margin-left: auto; margin-right: auto; }

/* ─── Spacing ─── */
.px-5 { padding-left: 1.25rem; padding-right: 1.25rem; }
.px-6 { padding-left: 1.5rem; padding-right: 1.5rem; }
.px-8 { padding-left: 2rem; padding-right: 2rem; }
.py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
.py-4 { padding-top: 1rem; padding-bottom: 1rem; }
.py-8 { padding-top: 2rem; padding-bottom: 2rem; }
.py-12 { padding-top: 3rem; padding-bottom: 3rem; }
.py-16 { padding-top: 4rem; padding-bottom: 4rem; }
.py-20 { padding-top: 5rem; padding-bottom: 5rem; }
.py-24 { padding-top: 6rem; padding-bottom: 6rem; }
.p-8 { padding: 2rem; }
.p-10 { padding: 2.5rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-8 { margin-bottom: 2rem; }
.mb-10 { margin-bottom: 2.5rem; }
.mb-12 { margin-bottom: 3rem; }
.mt-6 { margin-top: 1.5rem; }
.space-y-2 > * + * { margin-top: 0.5rem; }

/* ─── Typography ─── */
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-base { font-size: 1rem; line-height: 1.5rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
.text-4xl { font-size: 2.25rem; line-height: 2.5rem; }
.text-8xl { font-size: 6rem; line-height: 1; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }
.font-extrabold { font-weight: 800; }
.italic { font-style: italic; }
.uppercase { text-transform: uppercase; }
.tracking-tight { letter-spacing: -0.025em; }
.tracking-tighter { letter-spacing: -0.05em; }
.tracking-wide { letter-spacing: 0.025em; }
.tracking-widest { letter-spacing: 0.1em; }
.leading-relaxed { line-height: 1.625; }
.text-center { text-align: center; }
.list-disc { list-style-type: disc; }
.list-inside { list-style-position: inside; }

/* ─── Colors ─── */
.text-white { color: #fff; }
.text-gray-100 { color: #f7fafc; }
.text-gray-300 { color: #d1d5db; }
.text-gray-400 { color: #9ca3af; }
.text-blue-400 { color: #63b3ed; }
.bg-gray-700 { background-color: #374151; }
.bg-gray-800\/50 { background-color: rgba(31, 41, 55, 0.5); }
.bg-gray-900\/50 { background-color: rgba(17, 24, 39, 0.5); }
.bg-gray-900\/90 { background-color: rgba(17, 24, 39, 0.9); }

/* ─── Borders & Rounded ─── */
.border { border-width: 1px; border-style: solid; }
.border-t { border-top-width: 1px; border-top-style: solid; }
.border-b { border-bottom-width: 1px; border-bottom-style: solid; }
.border-y { border-top: 1px solid; border-bottom: 1px solid; }
.border-gray-700 { border-color: #374151; }
.border-gray-800 { border-color: #1f2937; }
.rounded { border-radius: 0.25rem; }
.rounded-lg { border-radius: 0.5rem; }
.rounded-xl { border-radius: 0.75rem; }
.rounded-2xl { border-radius: 1rem; }

/* ─── Effects ─── */
.shadow-xl { box-shadow: 0 20px 25px -5px rgba(0,0,0,.1), 0 8px 10px -6px rgba(0,0,0,.1); }
.backdrop-blur-md { -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
.transition { transition-property: color, background-color, border-color; transition-duration: 200ms; }
.opacity-75 { opacity: 0.75; }
.cursor-not-allowed { cursor: not-allowed; }

/* ─── Position & Z-index ─── */
.sticky { position: sticky; }
.top-0 { top: 0; }
.z-50 { z-index: 50; }
.relative { position: relative; }

/* ─── Accessibility ─── */
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border-width: 0; }
.focus\:not-sr-only:focus { position: static; width: auto; height: auto; padding: 0; margin: 0; overflow: visible; clip: auto; white-space: normal; }
.focus\:absolute:focus { position: absolute; }
.focus\:top-4:focus { top: 1rem; }
.focus\:left-4:focus { left: 1rem; }
.focus\:bg-blue-600:focus { background-color: #2563eb; }
.focus\:text-white:focus { color: #fff; }
.focus\:px-4:focus { padding-left: 1rem; padding-right: 1rem; }
.focus\:py-2:focus { padding-top: 0.5rem; padding-bottom: 0.5rem; }
.focus\:rounded:focus { border-radius: 0.25rem; }
.focus\:z-50:focus { z-index: 50; }
.focus\:outline-none:focus { outline: none; }

/* ─── Sizing ─── */
.w-6 { width: 1.5rem; }
.w-7 { width: 1.75rem; }
.h-6 { height: 1.5rem; }
.h-7 { height: 1.75rem; }

/* ─── Hover ─── */
.hover\:text-white:hover { color: #fff; }
.hover\:underline:hover { text-decoration: underline; }
.hover\:bg-gray-600:hover { background-color: #4b5563; }
.hover\:border-blue-400:hover { border-color: #63b3ed; }
.group:hover .group-hover\:text-blue-400 { color: #63b3ed; }

/* ─── Grid ─── */
.grid { display: grid; }

/* ─── Responsive: md (768px+) ─── */
@media (min-width: 768px) {
  .md\:flex { display: flex !important; }
  .md\:hidden { display: none !important; }
  .md\:text-5xl { font-size: 3rem; line-height: 1; }
  .md\:text-6xl { font-size: 3.75rem; line-height: 1; }
  .md\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* ─── max-md (below 768px) — mobile nav ─── */
@media (max-width: 767px) {
  .max-md\:absolute { position: absolute; }
  .max-md\:top-full { top: 100%; }
  .max-md\:left-0 { left: 0; }
  .max-md\:right-0 { right: 0; }
  .max-md\:bg-gray-900 { background-color: #111827; }
  .max-md\:border-b { border-bottom: 1px solid; }
  .max-md\:border-gray-800 { border-color: #1f2937; }
  .max-md\:flex-col { flex-direction: column; }
  .max-md\:px-6 { padding-left: 1.5rem; padding-right: 1.5rem; }
  .max-md\:py-4 { padding-top: 1rem; padding-bottom: 1rem; }
  .max-md\:gap-4 { gap: 1rem; }
}

.pb-20 { padding-bottom: 5rem; }

/* ─── Hidden utility ─── */
.hidden { display: none !important; }

/* ─── Fill-current for SVGs ─── */
.fill-current { fill: currentColor; }
```

## Test Files

Included files: `0`

## Project Scripts

No script files were found.

## Navigation Call-Site Inventory

~~~text
404.html:11: <link rel="icon" href="/favicon.ico" sizes="any">
404.html:13: <link rel="stylesheet" href="/styles.css">
404.html:19: <a href="/" class="font-bold text-xl tracking-tighter uppercase">BLUECOLLAR <span class="accent-steel">SYSTEMS</span></a>
404.html:28: <a href="/" class="inline-block bg-gray-700 hover:bg-gray-600 px-6 py-3 rounded-lg font-semibold transition">
feedback.html:10: <link rel="canonical" href="https://bluecollar-systems.com/feedback">
feedback.html:26: <link rel="icon" href="/favicon.ico" sizes="any">
feedback.html:27: <link rel="icon" href="/favicon.svg" type="image/svg+xml">
feedback.html:29: <link rel="stylesheet" href="/styles.css">
feedback.html:33: <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded focus:z-50">Skip to content</a>
feedback.html:37: <a href="/" class="font-bold text-xl tracking-tighter uppercase">BLUECOLLAR <span class="accent-steel">SYSTEMS</span></a>
feedback.html:42: <a href="/" class="hover:text-white transition">Home</a>
feedback.html:43: <a href="/#toolkit" class="hover:text-white transition">Toolkit</a>
feedback.html:44: <a href="/#steel-logic" class="hover:text-white transition">Steel Logic</a>
feedback.html:45: <a href="/#about" class="hover:text-white transition">About</a>
feedback.html:46: <a href="/#contact" class="hover:text-white transition">Contact</a>
feedback.html:47: <a href="/feedback" class="hover:text-white transition text-white" aria-current="page">Feedback</a>
feedback.html:68: <a href="mailto:support@bluecollar-systems.com" class="inline-block bg-gray-700 hover:bg-gray-600 px-6 py-3 rounded-lg font-semibold transition">
feedback.html:78: <a href="https://github.com/BlueCollar-Systems/SU-PDFimporter/issues" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">
feedback.html:81: <a href="https://github.com/BlueCollar-Systems/FC-PDFimporter/issues" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">
index.html:11: <link rel="canonical" href="https://bluecollar-systems.com/">
index.html:27: <link rel="icon" href="/favicon.ico" sizes="any">
index.html:28: <link rel="icon" href="/favicon.svg" type="image/svg+xml">
index.html:46: <link rel="stylesheet" href="/styles.css">
index.html:50: <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded focus:z-50">Skip to content</a>
index.html:54: <a href="/" class="font-bold text-xl tracking-tighter uppercase">BLUECOLLAR <span class="accent-steel">SYSTEMS</span></a>
index.html:59: <a href="/" class="hover:text-white transition" aria-current="page">Home</a>
index.html:60: <a href="#toolkit" class="hover:text-white transition">Toolkit</a>
index.html:61: <a href="#steel-logic" class="hover:text-white transition">Steel Logic</a>
index.html:62: <a href="#about" class="hover:text-white transition">About</a>
index.html:63: <a href="#contact" class="hover:text-white transition">Contact</a>
index.html:64: <a href="/feedback" class="hover:text-white transition">Feedback</a>
index.html:105: <a href="https://github.com/BlueCollar-Systems/SU-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
index.html:110: <a href="https://github.com/BlueCollar-Systems/FC-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
index.html:115: <a href="https://github.com/BlueCollar-Systems/BL-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
index.html:120: <a href="https://github.com/BlueCollar-Systems/LC-PDFimporter" target="_blank" rel="noopener" class="inline-block bg-gray-700 hover:bg-gray-600 px-5 py-3 rounded font-semibold transition text-sm">View on GitHub &rarr;</a>
index.html:141: <a href="mailto:support@bluecollar-systems.com" class="text-2xl font-bold text-blue-400 hover:underline">
index.html:144: <p class="mt-6 text-gray-400 text-sm">Want to report a bug or request a feature? <a href="/feedback" class="text-blue-400 hover:underline">Visit our Feedback page &rarr;</a></p>
RELEASE_CHECKLIST.md:14: - Replace the disabled Google Play button with a live `<a href="...">` link.
RELEASE_CHECKLIST.md:15: - Replace the disabled App Store button with a live `<a href="...">` link.
~~~

## Optional Checks

Checks were not run. Use `--run-checks` to capture configured command output.

## Exclusion / Skip Report

### Excluded Directory

- Count: 2

```text
.git
dev_logs
```

### Non Text Or Unlisted Extension

- Count: 8

```text
.cfignore
.gitignore
LICENSE
VERSION
__pycache__/repo_context_builder_core.cpython-312.pyc
_headers
_redirects
favicon.ico
```

## End of Pack

Context pack completed.
