// Contract for the Steel Logic privacy policy (the page Google Play links to).
// The Job Clock asks for each worker's name and an optional PIN, so the
// policy must say so (and that they stay on the device), and every page
// must link to the policy from its footer.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
function read(name) {
  return fs.readFileSync(path.join(ROOT, name), "utf8");
}
function plainText(html) {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z]+;|&#\d+;/gi, " ")
    .replace(/\s+/g, " ");
}

const privacy = read("privacy.html");
const privacyText = plainText(privacy);

assert(
  !/No names/i.test(privacyText),
  "privacy.html must not claim that no names are requested (Job Clock asks for worker names)"
);

const jobClockSentence = privacyText
  .split(/(?<=\.)\s+/)
  .find((sentence) => /Job Clock asks for/i.test(sentence));
assert(jobClockSentence, "privacy.html must explain what Job Clock asks for");
assert(/\bname/i.test(jobClockSentence), "the Job Clock sentence must mention worker names");
assert(/\bPIN/.test(jobClockSentence), "the Job Clock sentence must mention the optional PIN");
assert(
  /Names and PINs stay on this device/i.test(privacyText),
  "privacy.html must say worker names and PINs stay on the device"
);

for (const page of [
  "index.html",
  "shapes.html",
  "feedback.html",
  "report-doctor.html",
  "404.html",
  "privacy.html",
]) {
  const footer = (read(page).match(/<footer\b[\s\S]*?<\/footer>/i) || [])[0];
  assert(footer, page + " must have a <footer>");
  assert(
    /href="\/privacy"/.test(footer),
    page + " footer must link to the privacy policy (/privacy)"
  );
}

assert(
  /href="\/privacy"/.test(read("p/index.html")),
  "p/index.html (part-tag page) must link to the privacy policy"
);

console.log("privacy policy contract: PASS");
