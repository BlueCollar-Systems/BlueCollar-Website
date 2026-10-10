// Search-result and share-preview text. Google and link previews show the
// <meta> description and Open Graph / Twitter text, so it must say what the
// owner wants people to find: free PDF importers and Steel Logic shop time
// tracking. Sitemap dates must be real dates, not months stale.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
function read(name) {
  return fs.readFileSync(path.join(ROOT, name), "utf8");
}
function meta(html, attr, key) {
  const tags = html.match(/<meta\b[^>]*>/gi) || [];
  for (const tag of tags) {
    const keyMatch = tag.match(new RegExp("\\b" + attr + '="([^"]*)"', "i"));
    if (keyMatch && keyMatch[1] === key) {
      const content = tag.match(/\bcontent="([^"]*)"/i);
      return content ? content[1] : null;
    }
  }
  return null;
}

const index = read("index.html");
const description = meta(index, "name", "description");
const ogDescription = meta(index, "property", "og:description");
const twitterDescription = meta(index, "name", "twitter:description");
for (const [label, text] of [
  ["index meta description", description],
  ["index og:description", ogDescription],
  ["index twitter:description", twitterDescription],
]) {
  assert(text, label + " must exist");
  assert(/\bFree\b/.test(text), label + " must say the importers are Free");
  assert(/time tracking/i.test(text), label + " must mention shop time tracking");
}
assert(
  description.length <= 160,
  "index meta description is " + description.length + " characters; keep it to 160 so search results do not cut it off"
);
for (const host of ["SketchUp", "FreeCAD", "Blender", "LibreCAD"]) {
  assert(description.includes(host), "index meta description must name " + host);
}
assert(
  /Free/.test(meta(index, "property", "og:title") || ""),
  "index og:title must lead with the free importers"
);

const feedbackDescription = meta(read("feedback.html"), "name", "description");
assert(feedbackDescription, "feedback.html must have a meta description");
for (const host of ["Blender", "LibreCAD"]) {
  assert(feedbackDescription.includes(host), "feedback.html description must mention " + host);
}

const sitemap = read("sitemap.xml");
const lastmods = [...sitemap.matchAll(/<lastmod>([^<]*)<\/lastmod>/g)].map((m) => m[1].trim());
assert(lastmods.length > 0, "sitemap.xml must carry lastmod dates");
for (const value of lastmods) {
  assert(/^\d{4}-\d{2}-\d{2}$/.test(value), "sitemap lastmod " + value + " must be YYYY-MM-DD");
  const date = new Date(value + "T00:00:00Z");
  assert(!Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value, "sitemap lastmod " + value + " is not a real date");
  assert(value >= "2026-06-01", "sitemap lastmod " + value + " is older than 2026-06-01");
}

console.log("meta copy: PASS");
