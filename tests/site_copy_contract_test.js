const assert = require("node:assert");
const fs = require("node:fs");

const html = fs.readFileSync("index.html", "utf8");

assert(
  html.includes("Current Windows RBZ files bundle Poppler helpers"),
  "SketchUp install copy must state that the Windows RBZ bundles Poppler"
);
assert(
  html.includes("no separate helper download is required for normal imports"),
  "SketchUp install copy must state that normal imports need no helper download"
);
assert(
  !html.includes("The SketchUp RBZ is source-only"),
  "site must not retain the obsolete source-only SketchUp claim"
);
assert(
  !html.includes("Install free Poppler or MuPDF once"),
  "site must not ask users to install helpers already included in the RBZ"
);

console.log("site copy contract: PASS");
