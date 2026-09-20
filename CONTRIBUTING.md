# Contributing — BlueCollar-Systems website

Static marketing site for **BlueCollar Systems** products: Steel Logic (Job Clock first), Tag QC Builder, and four PDF importers. Live: [https://bluecollar-systems.com/](https://bluecollar-systems.com/). Do not merge the seven products into this repo or advertise feature-branch importer builds as releases.

This repository is [BlueCollar-Systems/BlueCollar-Website](https://github.com/BlueCollar-Systems/BlueCollar-Website). Local folder: `C:\1BlueCollar-Website`. Org access: **BlueCollar-Systems**. Tag QC’s private repo is under **BlueCollarSys-0628**.

## Full private pack (not in git)

`C:\Users\Rowdy Payton\Desktop\PDFTest Files\Q&A\` — `START_HERE.md`, `ONBOARDING.md`, `COMMUNICATION.md`.

GitHub clones do not include that hub; ask the owner. **Communicate there and with GitHub PRs/issues on this repo.** No Slack/Discord.

## Standing rules

- Version badges and download URLs follow **GitHub Releases** (`repo-metadata.json` / `tools/sync_repo_metadata.py`), not feature-branch tips.
- Cloudflare Pages project `bluecollar-website`, account id `df143f08ce8d490ebf620fe776fbd375`. CI workflow `website-ci` needs secrets `CLOUDFLARE_PAGES_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` (see README for aliases). **Never commit token values.**
- Steel Logic copy: time tracking first; shapes/calculators are secondary. LibreCAD is 2D DXF — do not advertise fake 3D TEXT. SketchUp 2017 is native `.skp` and can be slow. Blender and FreeCAD are the 3D CAD wins.
- UI/product names: **BlueCollar Systems** and/or **Steel Logic** only.
- Default: no commit/push/deploy without owner **GO** in the Q&A hub.

```powershell
python -m unittest discover -s tests -v
python tools/validate_private_artifacts.py
```

Open `index.html` locally. No build step.
