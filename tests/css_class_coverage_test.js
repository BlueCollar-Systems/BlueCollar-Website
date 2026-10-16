// Every class the pages and scripts use must have a rule in styles.css or in
// a page stylesheet beside it (part-page.css for the Part Tracking page).
// The site has no Tailwind build: a class with no rule silently does
// nothing (that is how the Part Tracking page ended up white on white).
// Also: the Content-Security-Policy in _headers blocks inline <style>, so
// no page may carry one unless style-src allows 'unsafe-inline'.
'use strict';

var assert = require('assert');
var fs = require('fs');
var path = require('path');

var ROOT = path.resolve(__dirname, '..');
var STYLESHEETS = fs.readdirSync(ROOT).filter(function(name) { return /\.css$/i.test(name); }).sort();
var css = STYLESHEETS.map(function(name) {
  return fs.readFileSync(path.join(ROOT, name), 'utf8');
}).join('\n');

// Classes used only as hooks, never styled on their own (footer-version
// marks the version that .github/workflows/auto-release.yml stamps).
var HOOK_CLASSES = ['doctor-output', 'doctor-summary', 'copy-tag', 'footer-version'];
// Prefixes completed at run time (e.g. 'doctor-pill-' + level).
var HOOK_PREFIXES = ['doctor-pill-'];

function selectorFor(cls) {
  return '.' + cls.replace(/[:\/.\[\]]/g, function(ch) { return '\\' + ch; });
}

function isDefined(cls) {
  var selector = selectorFor(cls);
  var index = css.indexOf(selector);
  while (index !== -1) {
    var next = css.charAt(index + selector.length);
    if (!/[A-Za-z0-9_\-\\]/.test(next)) return true;
    index = css.indexOf(selector, index + 1);
  }
  return false;
}

function htmlFiles() {
  var files = fs.readdirSync(ROOT).filter(function(name) { return /\.html$/i.test(name); });
  files.push('p/index.html');
  return files.sort();
}

var used = {};
function note(cls, source) {
  if (!cls) return;
  (used[cls] = used[cls] || new Set()).add(source);
}

htmlFiles().forEach(function(file) {
  var text = fs.readFileSync(path.join(ROOT, file), 'utf8');
  var match;
  var classAttr = /\bclass="([^"]*)"/g;
  while ((match = classAttr.exec(text))) {
    match[1].split(/\s+/).forEach(function(cls) { note(cls, file); });
  }
});

['nav.js', 'report-doctor.js', 'part-resolver.js', 'support-links.js'].forEach(function(file) {
  var text = fs.readFileSync(path.join(ROOT, file), 'utf8');
  var patterns = [
    /className\s*=\s*'([^']*)'/g,
    /className\s*=\s*"([^"]*)"/g,
    /tableCell\(\s*'([^']*)'/g,
    /classList\.(?:add|remove|toggle)\(\s*'([^']*)'/g
  ];
  patterns.forEach(function(pattern) {
    var match;
    while ((match = pattern.exec(text))) {
      match[1].split(/\s+/).forEach(function(cls) { note(cls, file); });
    }
  });
});

var missing = Object.keys(used).filter(function(cls) {
  if (HOOK_CLASSES.indexOf(cls) !== -1) return false;
  if (HOOK_PREFIXES.some(function(prefix) { return cls === prefix; })) return false;
  return !isDefined(cls);
}).sort();

var problems = [];
if (missing.length) {
  problems.push('Classes with no rule in ' + STYLESHEETS.join(' or ') + ':\n' + missing.map(function(cls) {
    return '  ' + cls + '  (' + Array.from(used[cls]).sort().join(', ') + ')';
  }).join('\n'));
}

var headers = fs.readFileSync(path.join(ROOT, '_headers'), 'utf8');
var cspMatch = headers.match(/Content-Security-Policy:\s*(.+)/);
assert(cspMatch, '_headers must set a Content-Security-Policy');
var styleSrc = (cspMatch[1].match(/style-src([^;]*)/) || [])[1] || '';
if (styleSrc.indexOf("'unsafe-inline'") === -1) {
  htmlFiles().forEach(function(file) {
    var text = fs.readFileSync(path.join(ROOT, file), 'utf8');
    if (/<style[\s>]/i.test(text)) {
      problems.push(file + ' has an inline <style> block, which the site CSP (style-src' + styleSrc + ') blocks; move it into styles.css or a page stylesheet');
    }
  });
}

if (problems.length) {
  console.error(problems.join('\n\n'));
  console.error('FAIL css_class_coverage_test');
  process.exit(1);
}
console.log('PASS css_class_coverage_test: ' + Object.keys(used).length + ' classes covered, no inline styles');
