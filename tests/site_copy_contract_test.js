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

console.log("site copy contract: PASS");
