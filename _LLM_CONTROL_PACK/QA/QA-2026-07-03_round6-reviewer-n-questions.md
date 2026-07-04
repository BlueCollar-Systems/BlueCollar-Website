# Round 6 — Reviewer N Questions (2026-07-03 evening)

**Author:** Anonymous Reviewer N
**Rules:** per `Instructions 0607202613216.txt` — no self-answers; peers reply in answer docs.
**Owner directive:** *"What have we promised but not done? What does each importer have that the others don't? Are they 100% accurate, functional, complete? Have we made them as powerful as they can be? If any answer says there's more work — do it. Nail them down."* This round exists to converge the importers to DONE, then unlock the owner's advanced-feature phase.

---

## Q-N12 — The promised-but-not-shipped ledger: confirm, claim, or kill each item

Compiled from R2–R5 resolutions, open threads, and today's T-01 evidence. For each: is it still wanted, who claims it, or do we kill it with a reason?

| # | Item | Source | Status believed |
|---|------|--------|-----------------|
| 1 | Artifact version stamp (embedded == tag always) | R3-4 | Not started |
| 2 | Code signing (LC EXEs + FC Setup.exe) | R3-8 | Blocked on owner cert decision |
| 3 | `actual_text_entity_types` emitters: LC → BL → SU | R4-4 | FC only |
| 4 | SU parity floor test + `performance_hint` in RBZ | R4-5 | Partial (verify) |
| 5 | Dependency manifest attached as release asset | R4-3ii | Not wired into workflows |
| 6 | `generate_human_summary.py` (T-01 pass/fail automation) | R3-3 | Doesn't exist |
| 7 | `bcs.part/1.0` schema + importer `parts_bootstrap` sidecar | R5 | Schema not in corpus |
| 8 | Report Doctor tag lookup + tag-sheet PDF | R5 | Not started |
| 9 | Telemetry envelope (opt-in failure reports) | R5/Q-N11 | Not started |
| 10 | FC-1 dense-dimension spacing fix | T-01 today | Corpus vector needed first (N is building it) |
| 11 | BL-2 large-file object batching | T-01 today | Unclaimed |
| 12 | SU QUAN rotation fix — CONFIRM SHIPPED + owner retest | T-01 today | Was mid-fix, red test |
| 13 | FC-2 ShapeColor + BL-1 lineweight — CONFIRM SHIPPED + owner retest | T-01 today | Believed committed today (verify release) |
| 14 | Windows-on-ARM support statement | R4 backlog | Unknown |
| 15 | OneDrive online-only placeholder handling | backlog | Unknown |
| 16 | SU Poppler prune (~8 MB unused OpenSSL/libcurl/libssh2) | §6 handoff | Not done |
| 17 | OCG full semantics (T-12), region-level hybrid (T-13), LC DXF image durability (T-14) | open threads | Research/backlog |

**Question:** Which rows are wrong, which get claimed this round, and which do we explicitly close as won't-do so the ledger reaches zero?

## Q-N13 — Feature-parity matrix: every importer's exclusive features — which should ALL of them have?

Verified-by-use today (owner screenshots + repo evidence):

| Feature | SU | FC | LC | BL | Cross-pollinate? |
|---------|----|----|----|----|------------------|
| **Scale by Reference / Quick Scale Factor** (toolbar) | ? | ✅ | ? | ? | Strong candidate for all hosts |
| **Import Health / Compatibility Report** (in-host self-check) | ✅ | ? | preflight CLI | preflight CLI | GUI health check everywhere? |
| **Safe Mode import** | ✅ | ? | ? | ? | ? |
| **DXF version selection** (R12–R2018) | n/a | n/a | ✅ | n/a | FC/BL DXF *export* with same selector? |
| **Batch CLI** (folder of PDFs) | ? | ? | ✅ | ✅ (`batch_cli`) | SU/FC batch story? |
| **Portable no-install EXE** | n/a | Setup.exe | ✅ | n/a | — |
| **Page arrangement (spread/stack) + gap ratio** | ? | ✅ | ? | ? | All hosts for multi-page |
| **`--lineweight-mode` (paper/scaled/hairline)** | ? | px-based | ? | ✅ CLI | Unify as shared contract option in all four + GUI |
| **Raster DPI / cleanup-level knobs** | ? | ? | ? | ✅ CLI | Shared contract? |
| **phase_timings_ms** | ? | ✅ | ? | ? | R3-10 says all hosts |

**Question:** Correct the ?s from code (not memory), then rank the cross-pollination slices by shop value. Proposal to beat: (1) Scale-by-Reference everywhere, (2) lineweight-mode everywhere incl. GUIs, (3) batch import everywhere, (4) in-host Health check everywhere.

## Q-N14 — "100% accurate, functional, complete" — define DONE or it never happens

Today alone produced 5 field defects (SU QUAN, FC spacing, FC fill color, BL lineweight, BL slow-load) on ONE drawing + ONE map. "Perfect" needs exit criteria, not vibes.

**Question:** Adopt (or amend) this Definition of DONE per importer, then drive each row green:
1. Corpus Tier-1 + Tier-2 all pass with per-host oracles (not just extraction: entity counts, colors, text modes, scale).
2. T-01 human matrix complete for that host (all test PDF classes: shop drawing, topo/map, raster scan, hybrid, encrypted-refusal) with machine artifacts attached.
3. Zero open P0/P1 defects tagged to that host in the ledger.
4. Contract fields emitted (`actual_text_entity_types`, ready_check, performance_hint) and Report Doctor renders them.
5. Release pipeline green including artifact smoke + (new) dependency manifest asset.
Who owns the per-host DONE scoreboard doc, and does it live in the corpus repo (neutral ground)?

## Q-N15 — Power ceiling: what would make these the most powerful importers in existence?

Beyond parity and bug-fixing — capabilities no competitor ships. Seeds (rank, add, or kill):
1. **Parallel multi-core page extraction** (FC/LC/BL) — biggest honest speed lever, accuracy-identical.
2. **Import presets per drawing type** ("Shop drawing", "Topo/map", "Scan") bundling mode+text+layers+scale defaults — zero-decision imports for non-technical users.
3. **Scale self-verification** — after import, measure 2–3 detected dimension strings against their measured geometry and report agreement % (turns scale_crosscheck into a user-facing trust number).
4. **BOM extraction to CSV/Steel Logic** on import (the parts already parse; R5's `parts_bootstrap` makes it a product feature).
5. **Snap-verified dimension audit tool** in-host: click two points, compare to nearest dimension string, flag drift.
6. **Cross-host project file**: one `.bcsproj` (PDF + chosen options + report) reopenable in any of the four hosts.

**Question:** Which of these are in scope for "nailed down" v1-perfect, and which belong to the owner's post-perfection advanced phase? Answer with a ranked build order and claims.

---

*End Round 6 questions. Reviewer N is concurrently building item Q-N12 #10 (dense-cluster corpus vector) as declared work, not an answer.*
