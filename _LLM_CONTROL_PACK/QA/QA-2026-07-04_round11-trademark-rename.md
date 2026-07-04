# Round 11 - Brand-Neutral Part Tag Naming (2026-07-04)

## Problem

The owner flagged that a third-party galvanizing-tag brand had been used as shorthand for our QR/barcode lookup feature. That is not acceptable for product naming: it is vendor-specific, not every shop uses that product, and it creates avoidable trademark ambiguity.

## Decision R11-1 - Canonical Name

Use **Part Tag** as the product-neutral term.

| Layer | Replacement |
|-------|-------------|
| Service class | `PartTagService` |
| Hit model | `PartTagHit` |
| Source file | `part_tag_service.dart` |
| Test file | `part_tag_service_test.dart` |
| UI copy | "part tag / QR lookup" |

Rationale: "Part Tag" is generic, vendor-neutral, and descriptive across bar code, QR, stamped, laser-etched, or handwritten tags. It also aligns with the existing `bcs.part/1.0` digital-thread naming.

## Decision R11-2 - Brand Policy

Do not use third-party product or brand names in identifiers, UI strings, file names, fixture names, feature names, or QA identifiers. Vendor examples may appear only nominatively in design discussion when unavoidable, phrased generically enough that a scrub check can stay clean. Historical git commits are not rewritten; current working-tree files are scrubbed.

## Status

Implemented and verified:

| Area | Status |
|------|--------|
| Steel Logic app | App service/test/UI names use `PartTagService`, `PartTagHit`, `part_tag_service.dart`, and "part tag / QR lookup" wording. |
| QA docs | Desktop Q&A and repo QA mirrors use "part tag", "Part Tag", or "third-party metal part tags". |
| Importer, website, corpus code | No live code identifiers used the retired brand after the app rename. |

Post-scrub verification grep target (2026-07-04): zero hits in current files for the retired brand spelling, compact spelling, hyphen/underscore variants, and vendor spelling variants across all seven repos plus Desktop Q&A.

## Ballot

The QA agreement is to ratify **Part Tag** as the canonical neutral term for QR/barcode piece-mark lookup across the app, importers, website, and corpus.

Rejected alternatives:

| Alternative | Why rejected |
|-------------|--------------|
| Piece mark tag | Redundant with existing piece-mark vocabulary; conflates mark text with the physical tag. |
| Shop tag | Too informal and ambiguous. |
| Barcode lookup | Too narrow because the workflow includes QR tags and physical part-tag handling. |
