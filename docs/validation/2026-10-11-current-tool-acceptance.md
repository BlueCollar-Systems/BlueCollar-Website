# Current tool acceptance — 2026-10-11

The current application repairs and source checks are complete for the bounded
local test pass. Releases use verified package bytes; ordinary pushes and builds
do not authorize production publication.

| Tool | Published version | Local acceptance |
| --- | --- | --- |
| SketchUp PDF Importer | 3.7.164 | Frozen r8 in Make 2017: 11 import matrix rows, 14 extrusion cases, one dimension case, save/reopen, fresh extrusion reopen and three fresh image-persistence scopes. The production payload differs only in two version constants. |
| FreeCAD PDF Importer | 4.0.113 | Frozen r6 in 0.21.2 and 1.1.4: six modes and ten saved/reopened models per host, cancellation/resume, Start Over/Undo and source-change refusal. Production source differences are package metadata and README. |
| Blender PDF Importer | 1.0.108 | Frozen r8 in 3.1.2 and 5.2.2: all six modes, mixed-height Compact placement, actual save/open and explicitly driven native cancellation/resume controls. Published ZIP retains 442 identical shared payload files. |
| LibreCAD PDF Importer | 1.0.106 | Four cold converter EXEs; three audited/reopened DXFs with zero audit errors/fixes. The unchanged official verifier authenticated the original hosted candidate and all six accepted file hashes; publication used those original bytes. |
| Steel Logic | 1.0.18 TEST prerelease | Windows TEST bundle and fresh extraction each passed eight native checks. Android TEST signature/manifest/ABI checks passed. Normal Windows compiled and extracted inventories passed without opening the shop profile. |
| Tag QC Builder | 10.43 | 302 built-in checks, all 21 browser test files, 94 script tests, package/privacy gates and five drawing-set comparisons with no unexpected/missing outputs. Companion Tag r4 and Website r6 passed a complete cold Edge lifecycle with backup/restore, restart and folder move. |
| Website | Final snapshot/deployment recorded separately | All 22 public source files are allowlisted. The final snapshot helper pins one source commit and verifies uploaded/downloaded draft bytes before publication. Local r6 browser acceptance retains exact source and package identities. |

The local hub preserves historical archives and immutable build identities in
their versioned folders. Its current acceptance aliases link subsequent proof
without rewriting earlier pending or failed receipts. Only fictional samples
are distributed. Existing application profiles and shop data were not migrated.

The source suites recorded with the frozen test builds passed: SketchUp 2,607
Minitest tests and 23,303 assertions, FreeCAD 2,499 tests, Blender 1,932 tests,
LibreCAD 2,075 tests, and Steel Logic 1,202 tests. Their declared skips, native
opt-in exclusions and exact source identities remain in the individual records.
These totals are not combined into an all-platform certification.

Remaining scope includes native LibreCAD GUI/viewer interaction, physical
Android installation/camera/OS links, signed iOS distribution, printer/native
Excel rendering, full physical UI journeys beyond the driven API/browser
checks, broader PDFs and other host versions/hardware. Blender reopen was
same-process with assets available. SketchUp extrusion supports bounded selected
profiles; complete automatic 3D reconstruction from drawing sets is future work.

Production Android account/signing configuration remains gated. The Android
artifact is explicitly TEST and is not a Play production upload. The Tag shop
opener retains its owner-managed version; the new portable release has its own
launcher.
