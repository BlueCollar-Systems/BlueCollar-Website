# Round 7 — Reviewer N: SU CLI + embedded images + app-phase kickoff (2026-07-04)

**Author:** Anonymous Reviewer N
**Owner directive:** add SketchUp CLI support and SketchUp individual embedded-image extraction + remaining unimplemented features; then apply the full Q&A engineering approach to the other repos, **especially the Steel Logic app**.

---

## ⚠️ COORDINATION FIRST — two SU CLI lanes are live simultaneously

1. **Shipped (this session):** `tools/su_pdf_cli.rb` + `test/su_cli_test.rb` (SU `4a3b96e`) — dev-Ruby headless CLI over the existing `CorpusHarness`/`PDFParser` pipeline: JSON summary, `bcs.import_report/1.1` with `report_meta`, `bcs.ready_check/1.0` preflight, 18-assertion contract test, visible corpus skip. Deliberately emits **no** `actual_text_entity_types` (host proof needs the host).
2. **In progress (another session, uncommitted):** `extracted/sketchup_ext/bc_pdf_vector_importer/cli.rb` — in-extension CLI. **Heads-up before you commit:** lines 376–377 use `Hash#dig` → the Ruby 2.2 gate fails (`ruby22_compat_test.rb` red locally right now). Replace with guarded `[]` chains or the repo's existing dig-free pattern, or your release will bounce.

**Q-N16:** Merge plan — should the in-extension `cli.rb` become the single engine (2.2-safe, shippable in the RBZ) with `tools/su_pdf_cli.rb` reduced to a thin dev wrapper around it, so we get ONE contract (`--json/--report/--preflight`, matching LC `pdf2dxf` and BL `batch_cli` flags) instead of two drifting CLIs? Whoever owns the in-extension lane: claim, fix the dig calls, and align flags with the shipped tool's contract test.

## Q-N17 — SU individual embedded-image extraction (owner-requested): spec to claim

No image/XObject support exists in `pdf_parser.rb` today (verified by grep). Two viable paths, pick and claim:
1. **SVG route (no new binaries, no new licenses):** the pipeline already renders pages via `pdftocairo -svg`; embedded rasters appear as `<image>` elements with transforms + base64 payloads. Parse those → decode to PNG/JPEG files → return `{file, page, transform, w, h}` → create `Entities#add_image` placements (API present since SU 2017). Fully headless-testable (SVG fixture, no Poppler needed for unit tests).
2. **pdfimages route:** bundle `pdfimages.exe` via `tools/fetch_third_party_binaries.ps1` (+ THIRD_PARTY notice + dependency_audit entry). Gets original image bytes (no re-encode) but **no placement coordinates** — would still need route 1's transforms for placement.

Recommendation to beat: route 1 first (placement included, zero packaging/legal work); route 2 later only if lossless originals matter. Acceptance: corpus gains a redistributable PDF with ≥2 embedded images (generator tool, like the fraction PDF); import produces one SketchUp Image entity per embedded image at the right position; report gains `extra.embedded_images: {count, extracted}` and the CLI a `--extract-images DIR` flag.

## Q-N18 — Remaining unimplemented-features sweep (close the parity matrix)

Still open from R6/Q-N13 after this week's shipping: Scale-by-Reference in SU/LC/BL (FC-only today), lineweight-mode in all GUIs, batch/folder import for SU (CLI now exists — GUI batch next?) and FC, in-host Health check for FC/LC/BL (SU-only today), parallel page extraction (R6 P1), FC dependency-manifest release asset, `source_provenance` completion (R6-8 — SU partial). **Which rows land before the owner's "importers done" line, with names on them?**

## Q-N19 — App-phase kickoff (owner directive: same approach, QA and all)

The importer playbook that worked — evidence-first Q&A rounds, ledgers with confirm/claim/kill, definition-of-DONE scoreboards, conformance vectors, contract schemas, release-gate CI, T-01 human matrices — applied to `C:\1 Structural_Steel_Shapes_App`:
1. **Open the app's own Q&A track** (`QA-app-*` docs, same anonymous rules) — first round questions: omni engine completion (unit dimensions beyond length: mass/pressure/temp/time from the deleted-but-specced 8-dim registry), R5-1…R5-7 backlog (Part Tracking scanner, `bcs.part/1.0`, tag-sheet, deep links), test-coverage map vs the 193 current tests, release/packaging gates (`package_windows_release.ps1` has no CI), store-readiness (Android/iOS), crash/ANR telemetry policy.
2. **App Definition of DONE** mirroring Q-N14: contract schemas for app outputs, scoreboard in corpus repo, human field-test script for shop-floor flows (lookup, inventory count, time clock, scan).
3. **First conformance artifact:** omni-box golden vectors (input phrase → exact expected output at N dp) in the corpus, consumed by `flutter test` — same pattern as the fraction vectors.
**Question:** confirm this track structure, claim the app round's first reviewer slots, and name the app CI gate owner.

---
*Reviewer N continues on unclaimed rows; SU CLI contract test is the compatibility bar for the merged CLI (Q-N16).*
