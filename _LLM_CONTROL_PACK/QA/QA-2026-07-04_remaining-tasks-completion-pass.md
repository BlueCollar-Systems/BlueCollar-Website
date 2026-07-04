# QA 2026-07-04 — Remaining Tasks Completion Pass

Scope: `Remaining Tasks.txt` plus the follow-on app/Report Doctor/part tag checks requested in this thread.

## Closed in this pass

- **SketchUp R7-9 CLI contract merge:** `tools/su_pdf_cli.rb` now wraps the unified extension CLI contract while preserving legacy `--json`, `--report`, `--preflight`, positional PDF, and `--extrude-depth` behavior.
- **SketchUp `extrude_depth` dialog:** confirmed already present as `extrude_depth_mm` in the advanced import dialog and covered by `import_dialog_defaults_test`.
- **SketchUp `parts_bootstrap`:** in-host import and CLI paths now retain per-page text maps, populate `import_report.extra.parts_bootstrap`, and write `*_parts_bootstrap.json` sidecars when BOM rows are detected.
- **FreeCAD `parts_bootstrap` rows:** real BOM row extraction verified against `1017 - Rev 0.pdf` with 10 rows.
- **LibreCAD / Blender `parts_bootstrap`:** host report writers now emit `parts_bootstrap.json`, record `extra.parts_bootstrap`, and stamp the sidecar with `report_sha256`.
- **Website Report Doctor:** fixed duplicate `bootstrap-file` id, detects `extra.parts_bootstrap` directly from import reports, renders tag rows from inline or uploaded sidecar data, and includes sidecar details in support summaries.
- **Steel Logic Report Doctor:** app UI surfaces import trust, 3D intent/model fields, and parts-bootstrap sidecar details.
- **part tag bridge:** service now loads `bcs.parts_bootstrap/1.0`, resolves piece marks and `/p/<part_id>` URLs, generates tag URLs, and still prioritizes source-provenance bbox hits when available.
- **Corpus / CI:** LC and BL workflows now run corpus schema + conformance checks; SketchUp baselines regenerated for the current corpus set.

## Verification

- FreeCAD: `python -m pytest tests -q` -> 135 passed, 1 skipped.
- LibreCAD: `python -m pytest tests -q` -> 63 passed, 11 subtests passed.
- Blender: `python -m pytest tests -q` -> 63 passed, 10 subtests passed.
- SketchUp focused gates: `qa_report_test`, `su_cli_test`, `batch_cli_test`, `import_dialog_defaults_test`, `parts_bootstrap_test` all passed.
- Steel Logic app: `flutter analyze` -> no issues; `flutter test` -> all tests passed.
- Website: `node --check report-doctor.js`; only one `id="bootstrap-file"` remains.
- Corpus: `validate_contract_schemas.py` -> OK, 6 schemas; conformance vectors -> python pass, sketchup pass.
- Shared sync: `pdfcadcore_sync_check.py` -> ALL IN SYNC.

## Remaining Non-Human Work

- **Semantic steel solids v2:** FC has a default-off semantic member foundation; cross-host exact member/plate generation from leaders + BOM + AISC catalog remains the next major modeling phase.
- **Scale-by-Reference parity:** still FC-only.
- **Import Health parity:** SketchUp has the richest support snapshot; FC/LC/BL still need equivalent in-host UX.
- **Automated visual regression tooling:** golden raster/overlay checks for color, lineweight, spacing, and alignment are still needed to reduce future manual review.
- **Public `/p/` pages and tag-sheet generation:** app/service can generate and resolve tag URLs; the public web route and printable tag-sheet workflow remain advanced-phase work.
- **Omni/app expansion and packaging hardening:** deferred app backlog remains outside the importer completion pass.

Conclusion: the concrete automatable importer/report/app bridge tasks in the short remaining list are now implemented and locally verified. The remaining items are larger advanced-phase work or owner-controlled release/field actions.
