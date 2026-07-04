# Round 10 — Execution ledger from owner's "Remaining Tasks" document (2026-07-04)

**Source of truth:** owner's `Remaining Tasks.txt` (this folder). Rule: every row gets **claimed or completed**; post completions to the status log with evidence. T-01 human items excluded.

## Completed this session (Reviewer N, evidence in status log)
| Item | Evidence |
|---|---|
| Corpus baselines for 7 new PDFs | SU `3aca3e5` — 29 baselines, placement gate 30/30 PASS |
| R8-E AISC profile catalog | corpus `40ca70f` — 2,299 shapes, dual nomenclature |
| **R8-A foundation: section outlines** | FC `9939c3f` / LC `f45362a` / BL `38ca74a` — `pdfcadcore/section_outlines.py`: designation → exact I/T/C/L polygons + HSS/PIPE rings, `idealized` flag, 6 tests incl. all 1017 shapes |
| parts_bootstrap core slice (with concurrent session) | bundled in same push; suites FC 135 / LC 62 / BL 61 green, ALL IN SYNC |

## Remaining — claim a row, work it, log it
| # | Row | Repo | Notes |
|---|---|---|---|
| 1 | **R8-A host generation** — FC: `Part.Face(outer−holes)` from `section_outline()` → extrude by BOM `length_in` → name `{mark} {designation}`, group by assembly; then BL (bmesh), SU (Ruby port or steel_shapes components) | FC→BL→SU | `test_model3d_generation.py` already started in FC — finish against section_outlines |
| 2 | R8-B v2 plate-outline association (leader → closed path, holes) | core+FC | corpus vector FIRST |
| 3 | R8-F corpus 3D anchor: `model3d_regression.pdf` generator + expected-solids oracle | corpus | mirror fraction-PDF pattern |
| 4 | R7-9 SU CLI merge: one contract over `su_pdf_cli.rb` / `su_batch_cli.rb` / `cli.rb`; contract test = bar | SU | |
| 5 | SU `extrude_depth` dialog HTML field + JS callback (wired everywhere else) | SU | |
| 6 | App **Report Doctor screen**: render already-parsed `model_3d` / intent / provenance / contract-ready | app | data is in memory today |
| 7 | part tag loop: sidecar lookup + reverse-highlight (scan+deep links shipped) | app | offline scan queue too |
| 8 | parts_bootstrap real BOM row extraction (`tables[]` → marks/qty/profile/length) all hosts | core | slice landed; finish rows |
| 9 | Scale-by-Reference parity SU/LC/BL (FC has it) | 3 hosts | |
| 10 | Import Health parity FC/LC/BL (SU has it) | 3 hosts | |
| 11 | GUI parity: lineweight-mode, batch/folder import, page-range controls | all | |
| 12 | BL-2 batching + parallel page extraction + phase timings LC/BL/SU | perf | measure first |
| 13 | Visual regression tooling: golden rasters/overlays (color, lineweight, spacing, rotation) | corpus | reduces future T-01 load |
| 14 | Cross-product corpus CI; dependency-manifest release assets; LC/BL schema CI; R3-4 artifact stamp | pipeline | |
| 15 | Website: Tags tab (in progress — fix duplicate `bootstrap-file` element id in report-doctor.html), `/p/` part pages, AV-guidance page | website | |
| 16 | Omni expansion (mass/pressure/temp/time, sqrt, "to N dp"), omni golden vectors in corpus, app packaging CI | app | |
| 17 | P2 tier: OCG semantics, region hybrid, DXF image durability, Win-ARM, OneDrive placeholders, SU Poppler prune, telemetry envelope, WASM research | various | |

**Owner-only (parked):** code signing; CORPUS_READ_TOKEN secret; Firebase SDK dedup; dist-blob history rewrite; steel-shape repo retirement.
