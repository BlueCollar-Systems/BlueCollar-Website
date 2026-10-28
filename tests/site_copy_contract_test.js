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
// Latest published Tag Logic build is v10.48. Its repository requires access:
// an anonymous request for the prior release URL returned HTTP 404. Offer the
// existing support route and do not publish a repository, release, or ZIP
// link. The version is typed in the badge, the published-build sentence, and
// the README product table; all three must name this same build.
const tagPublishedVersion = "10.48";
const tagAccessLabel = "Ask for Tag Logic access";
const tagSectionOpening = elementTags.find(
  (tag) => /^<section\b/i.test(tag) && attributeValue(tag, "id") === "tag-qc"
);
assert(tagSectionOpening, "Tag Logic must keep its existing section anchor");
const tagCard = balancedElementBlock(html, tagSectionOpening);
const tagCardText = tagCard.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ");
const tagBadge = tagCard.match(
  /<h2\b[^>]*>\s*BlueCollar Tag Logic\s*<\/h2>\s*<span\b[^>]*>\s*v(\d+\.\d+)\s*<\/span>/
);
assert(tagBadge, "BlueCollar Tag Logic heading must carry a version badge");
assert.strictEqual(
  tagBadge[1],
  tagPublishedVersion,
  "Tag Logic badge must name the latest published build v" + tagPublishedVersion
);
assert(
  new RegExp(
    "Tag Logic v" +
      tagPublishedVersion.replace(".", "\\.") +
      " is published on GitHub\\."
  ).test(tagCardText),
  "Tag Logic published-version copy must name released v" + tagPublishedVersion
);
assert(
  [...tagCardText.matchAll(/\bv[0-9]+\.[0-9]+\b/g)].every(
    (match) => match[0] === "v" + tagPublishedVersion
  ),
  "Tag Logic card must not advertise stale or unpublished versions"
);
assert(
  tagCardText.includes("Downloads currently require access to its GitHub repository.") &&
    tagCardText.includes("Contact support if you need access.") &&
    tagCardText.includes("There is no public download from this website."),
  "Tag Logic must visibly explain private GitHub access and the lack of a public website download"
);
assert(
  tagCardText.includes("Save a JSON Job Backup before changing versions.") &&
    tagCardText.includes("Extract the whole ZIP, keep its files together and run the inner") &&
    tagCardText.includes("OPEN_BlueCollar_Systems_Tag_QC_Builder.bat") &&
    /choose a PNG or JPG.*preview.*click Apply logo.*save another Job Backup/.test(tagCardText),
  "Tag Logic setup must preserve backup, whole ZIP, inner launcher and logo preview/Apply steps"
);
const tagAccessLinks = [...tagCard.matchAll(/(<a\b[^>]*>)([\s\S]*?)<\/a>/gi)];
assert.strictEqual(tagAccessLinks.length, 1, "Tag Logic card must offer one support-access action");
assert.strictEqual(attributeValue(tagAccessLinks[0][1], "href"), "#contact", "Tag Logic access action must use the existing contact section");
assert.strictEqual(tagAccessLinks[0][2].trim(), tagAccessLabel, "Tag Logic access action must ask for access rather than promise a download");
assert(
  !/\b(hidden|sr-only)\b/.test(attributeValue(tagAccessLinks[0][1], "class") || ""),
  "Tag Logic access label must remain visible"
);
const contactSectionOpening = elementTags.find(
  (tag) => /^<section\b/i.test(tag) && attributeValue(tag, "id") === "contact"
);
assert(contactSectionOpening, "Tag Logic access action must have a real contact target");
assert(
  balancedElementBlock(html, contactSectionOpening).includes('href="mailto:support@bluecollar-systems.com"'),
  "Contact section must keep its existing support email action"
);

function assertNoTagDownloadActivation(source, name) {
  assert(
    !/1Tag-QC-Builder|Tag_QC_Builder_v[0-9_]+_Portable\.zip/i.test(source),
    name + " must not activate or hide a private Tag repository, release or ZIP URL"
  );
  assert(
    !/Download (Tag QC|(BlueCollar )?Tag Logic)|Open v10\.[0-9]+ release/i.test(source),
    name + " must not offer an anonymous-unusable Tag release or download action"
  );
}
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
  "site must not advertise the unpublished BlueCollar Tag Logic v10.37 build"
);
assert(
  !/v10\.46/.test(html),
  "site must not advertise the superseded BlueCollar Tag Logic v10.46 build"
);
const readme = fs.readFileSync("README.md", "utf8");
const readmeTagRow = readme.match(
  /^\| \*\*BlueCollar Tag Logic\*\* \|.*Published v(\d+\.\d+) on GitHub;.*$/m
);
assert(readmeTagRow, "README product table must name the BlueCollar Tag Logic build");
assert.strictEqual(
  readmeTagRow[1],
  tagBadge[1],
  "README and the home page must name the same BlueCollar Tag Logic build"
);
assert(
  /downloads require access to its GitHub repository/.test(readmeTagRow[0]) &&
    /there is no public download from this website/.test(readmeTagRow[0]) &&
    /Save a JSON Job Backup before changing versions and extract the whole ZIP/.test(
      readmeTagRow[0]
    ),
  "README must explain private GitHub access, no public website download, and the Job Backup / whole ZIP steps"
);
assert(
  readme.includes("[Tag Logic access](https://bluecollar-systems.com/#tag-qc)"),
  "README Tag Logic link must point at the on-site access section"
);
assert(
  !/v10\.46/.test(readme),
  "README must not advertise the superseded BlueCollar Tag Logic v10.46 build"
);
assertNoTagDownloadActivation(html, "index.html");
assertNoTagDownloadActivation(readme, "README.md");
assert(
  html.includes("GitHub Release"),
  "importer badges must be described as GitHub Release versions"
);
const tagClaimsText = tagCardText.replace("There is no public download from this website.", "");
assert(
  !/anonymous(?:ly)?|unrestricted|public download|no (?:GitHub |repository )?access required|without (?:GitHub |repository )?access|no sign[- ]?in required/i.test(tagClaimsText),
  "Tag Logic must not promise anonymous or unrestricted repository access"
);

// Owner decision 2026-10-18: the tag tool is named "BlueCollar Tag Logic"
// ("Tag Logic" where space is tight), always two words. Current pages,
// shipped scripts and docs must not show the old name or the one-word
// spelling. The public site offers support access to published v10.48;
// private repository, release and direct ZIP activation remain forbidden.
// The #tag-qc anchor stays because outside links use it. Dated records under
// docs/validation/ keep the name they were written with and are not checked.
const currentCopyFiles = [
  ...fs.readdirSync(".").filter((name) => /\.(html|js|md)$/i.test(name)),
  "p/index.html",
  ...fs.readdirSync("docs")
    .filter((name) => /\.md$/i.test(name))
    .map((name) => "docs/" + name),
];
for (const name of currentCopyFiles) {
  const text = fs.readFileSync(name, "latin1");
  assert(
    !/taglogic/i.test(text),
    name + " must write the tag tool's name as two words: Tag Logic"
  );
  assert(
    !/\bTag QC\b|QC Builder/i.test(text),
    name + " must call the tag tool BlueCollar Tag Logic, not Tag QC Builder"
  );
  if (/\.html$/i.test(name)) {
    assertNoTagDownloadActivation(text, name);
    // The top menu uses the short form: with the full name the menu breaks
    // onto a second row at 1024 px; "Tag Logic" keeps it on one row, as
    // "Tag QC" did. The section heading on the home page carries the full
    // name.
    const tagLinks = [...text.matchAll(/<a\b[^>]*href="\/?#tag-qc"[^>]*>([^<]*)<\/a>/g)];
    if (text.includes('id="nav-menu"')) {
      assert.strictEqual(
        tagLinks.length,
        1,
        name + " menu must link to the tag tool section once"
      );
    }
    for (const link of tagLinks) {
      assert.strictEqual(
        link[1].trim(),
        "Tag Logic",
        name + " menu link to the tag tool must read Tag Logic"
      );
    }
  }
}

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
