const assert = require("node:assert");
const fs = require("node:fs");

const html = fs.readFileSync("index.html", "utf8");

function attributeValue(tag, name) {
  const attributes = tag.matchAll(
    /\b([A-Za-z_:][\w:.-]*)\s*=\s*(["'])(.*?)\2/g
  );
  for (const match of attributes) {
    if (match[1].toLowerCase() === name.toLowerCase()) {
      return match[3];
    }
  }
  return null;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function balancedElementBlock(source, openingTag) {
  const nameMatch = openingTag.match(/^<([A-Za-z][\w:.-]*)\b/);
  assert(nameMatch, "beta target must have a valid opening tag");

  const start = source.indexOf(openingTag);
  assert.notStrictEqual(start, -1, "beta target opening tag must exist in HTML");

  const tagName = nameMatch[1];
  const tagPattern = new RegExp(
    "<\\/?" + escapeRegExp(tagName) + "\\b[^>]*>",
    "gi"
  );
  tagPattern.lastIndex = start;

  let depth = 0;
  let first = true;
  for (;;) {
    const match = tagPattern.exec(source);
    assert(match, "beta target element must have a balanced closing tag");
    if (first) {
      assert.strictEqual(
        match.index,
        start,
        "balanced extraction must begin at the beta target"
      );
      first = false;
    }

    const token = match[0];
    if (/^<\//.test(token)) {
      depth -= 1;
    } else if (!/\/\s*>$/.test(token)) {
      depth += 1;
    }
    assert(depth >= 0, "beta target element nesting must remain balanced");

    if (depth === 0) {
      return source.slice(start, tagPattern.lastIndex);
    }
  }
}

const anchorTags = html.match(/<a\b[^>]*>/gi) || [];
const elementTags = html.match(/<[A-Za-z][^>]*>/g) || [];

assert(
  html.includes("The Windows RBZ includes Poppler for rendering and text helpers."),
  "SketchUp install copy must state that the Windows RBZ includes Poppler"
);
assert(
  html.includes("MuPDF and Ghostscript are optional and are not inside the RBZ."),
  "SketchUp install copy must say MuPDF and Ghostscript are not inside the RBZ"
);
assert(
  !html.includes("The Windows RBZ includes the PDF tools needed for rendering and font repair."),
  "site must not claim font-repair tools are bundled in the Windows RBZ"
);
assert(
  html.includes("No separate helper download is required for normal imports."),
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
assert(
  html.includes("Shop time tracking, plus AISC shapes and calculators"),
  "Steel Logic copy must lead with shop time tracking"
);
assert(
  html.includes("Job Clock for jobs and parts on the floor"),
  "Steel Logic copy must name Job Clock"
);
assert(
  !html.includes("AISC v16.0 Structural Steel Shapes Reference"),
  "site must not keep the old shapes-first Steel Logic headline"
);
assert(
  /<h2\b[^>]*>\s*BlueCollar Tag Logic\s*<\/h2>/.test(html),
  "site must advertise the exact BlueCollar Tag Logic product heading"
);
// Owner decision 2026-10-05: no direct download of Tag QC Builder from the website yet.
assert(
  html.includes("BlueCollar Tag Logic is not available for download from this website yet"),
  "BlueCollar Tag Logic section must say it is not available for download yet"
);
assert(
  html.includes("BCS1:") && html.includes("CS1:"),
  "BlueCollar Tag Logic copy must name the BCS1: prefix and say older CS1: tags still scan"
);
assert(
  html.includes("Coming soon"),
  "App Store button must say Coming soon where people can see it"
);
assert(
  !/v10\.37/.test(html),
  "site must not advertise the unpublished Tag QC v10.37"
);
assert(
  !/1Tag-QC-Builder|Download Tag QC|Download BlueCollar Tag Logic|OPEN_BlueCollar_Systems_Tag_QC_Builder|Tag_QC_Builder_v[0-9_]+_Portable\.zip/.test(html),
  "site must not offer a BlueCollar Tag Logic download until the owner releases it"
);
assert(
  html.includes("GitHub Release"),
  "importer badges must be described as GitHub Release versions"
);
assert(
  !html.includes("1Tag-QC-Builder/releases"),
  "site must not expose direct download access to the Tag tool yet"
);

const primaryCtas = anchorTags.filter((tag) => {
  const classes = attributeValue(tag, "class");
  return classes && classes.split(/\s+/).includes("btn-safety");
});
assert.strictEqual(
  primaryCtas.length,
  1,
  "site must expose exactly one primary .btn-safety CTA"
);
assert.strictEqual(
  attributeValue(primaryCtas[0], "href"),
  "#android-beta",
  "primary .btn-safety CTA must route to the Android beta instructions"
);
assert.strictEqual(
  anchorTags.filter((tag) => attributeValue(tag, "href") === "#android-beta")
    .length,
  1,
  "only the primary CTA may link to the Android beta anchor"
);

const betaTargets = elementTags.filter(
  (tag) => attributeValue(tag, "id") === "android-beta"
);
assert.strictEqual(
  betaTargets.length,
  1,
  "site must expose exactly one Android beta anchor target"
);
assert(
  /^<div\b/i.test(betaTargets[0]),
  "Android beta anchor target must be the beta instruction card"
);

const betaBlock = balancedElementBlock(html, betaTargets[0]);
const betaAnchorTags = betaBlock.match(/<a\b[^>]*>/gi) || [];
const testerGroupUrl =
  "https://groups.google.com/g/steellogic-beta-testers";
const testerEnrollmentUrl =
  "https://play.google.com/apps/testing/com.bluecollarsystems.steellogic";
assert.strictEqual(
  betaAnchorTags.filter(
    (tag) => attributeValue(tag, "href") === testerGroupUrl
  ).length,
  2,
  "Android beta instructions must contain both tester-group links"
);
assert.strictEqual(
  betaAnchorTags.filter(
    (tag) => attributeValue(tag, "href") === testerEnrollmentUrl
  ).length,
  1,
  "Android beta instructions must contain the tester-enrollment link"
);

const publicDetailsBaseUrl =
  "https://play.google.com/store/apps/details?id=com.bluecollarsystems.steellogic";
assert(
  !html.includes(publicDetailsBaseUrl),
  "site must not contain the unavailable public Google Play listing URL"
);

// Downloads: say the importers are free, say they are Windows packages,
// keep the SketchUp 2017 floor current, and caption every Download Latest
// button so nav.js can show the file type and size.
assert(
  html.includes("free and open source"),
  "Toolkit copy must say the PDF importers are free and open source"
);
assert(
  !html.includes("Works on any PC"),
  "site must not claim the Windows packages work on any PC"
);
assert(
  html.includes("64-bit Windows packages"),
  "install copy must say the downloads are Windows packages"
);
assert(
  html.includes("v3.7.90 or newer") && !html.includes("3.7.67"),
  "SketchUp Make 2017 floor must match COMPATIBILITY.md (v3.7.90 or newer)"
);
for (const repo of [
  "BlueCollar-Systems/PDF-Importer-SketchUp",
  "BlueCollar-Systems/PDF-Importer-FreeCAD",
  "BlueCollar-Systems/PDF-Importer-Blender",
  "BlueCollar-Systems/PDF-Importer-LibreCAD",
]) {
  const infoTags = elementTags.filter(
    (tag) => attributeValue(tag, "data-repo-asset-info") === repo
  );
  assert.strictEqual(
    infoTags.length,
    1,
    repo + " Download Latest card must have one data-repo-asset-info caption"
  );
}
for (const host of ["After upgrading FreeCAD", "after upgrading SketchUp", "after upgrading Blender"]) {
  assert(html.includes(host), "install steps must tell people what to do " + host.toLowerCase());
}
assert(html.includes("Tools → Addon Manager"), "FreeCAD install copy must name the Addon Manager path");
assert(html.includes("Window → Extension Manager → Install Extension"), "SketchUp install copy must name Extension Manager");
assert(html.includes("Edit → Preferences → Add-ons → Install"), "Blender install copy must name Preferences → Add-ons");
assert(html.includes("Plugins → Import PDF (BlueCollar)"), "LibreCAD install copy must name the Plugins menu");

const shapesHtml = fs.readFileSync("shapes.html", "utf8");
assert(
  !shapesHtml.includes("listed above"),
  "shapes.html must not point to a checksum 'listed above' that the page does not show"
);
for (const asset of [
  "Structural-Steel-SU-Shapes-latest.zip",
  "Structural-Steel-DXF-DWG-Shapes-latest.zip",
]) {
  assert(
    shapesHtml.includes('data-asset-digest-for="' + asset + '"'),
    "shapes.html must show the SHA-256 under the " + asset + " download"
  );
  assert(
    new RegExp('data-asset-digest-for="' + asset + '"[^>]*>\\s*SHA-256:\\s*[0-9a-f]{64}').test(shapesHtml),
    "shapes.html must include a static SHA-256 for " + asset + " so it shows before JavaScript runs"
  );
}

console.log("site copy contract: PASS");
