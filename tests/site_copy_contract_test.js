const assert = require("node:assert");
const fs = require("node:fs");

const html = fs.readFileSync("index.html", "utf8");

assert(
  html.includes("The SketchUp RBZ is source-only"),
  "SketchUp install copy must state that the RBZ is source-only"
);
assert(
  !html.includes("Current Windows RBZ files bundle Poppler helpers"),
  "site must not claim that the source-only SketchUp RBZ bundles Poppler"
);
assert(
  html.includes("FreeCAD, LibreCAD, and Blender release packages bundle"),
  "dependency copy must identify which hosts ship bundled runtimes"
);

console.log("site copy contract: PASS");
