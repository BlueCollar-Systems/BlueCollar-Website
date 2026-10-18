// Report Doctor parts list (T18) and LibreCAD text advice. Runs under plain
// `node tests/report_doctor_parts_list_test.js` with a small DOM stub built
// from report-doctor.html, so it also runs where the real-browser tests
// cannot (the same checks run in Chrome in report_doctor_browser_test.js and
// report_doctor_librecad_advice_test.js).
//
// Contract under test:
//  1. The parts list section is outside #doctor-output, so a parts file
//     shows without an import report (file picker, paste + blur, and the
//     Analyze button with an empty report box). No "Tags tab" wording.
//  2. A real importer parts file lists every row with no tag link and says
//     why; a file with no rows says so (with the file's own note).
//  3. Audit 7b: rows that carry a part_id get exactly the tag URL that the
//     published part record uses, and the part page accepts every ID that
//     Report Doctor links.
//  4. LibreCAD users are never told to use Labels or 3D Text for editable
//     words; they are told about "Editable text (LibreCAD font)" unless the
//     report says they already chose it. Other hosts keep their advice.
//
// The two fixtures in tests/fixtures/report_doctor were written by the
// importers' own writer (pdfcadcore/parts_bootstrap.py
// write_parts_bootstrap_sidecar, FreeCAD main 92ba7b6) from fictional
// bill-of-material text (job D042, marks EX###).
'use strict';

var assert = require('assert');
var fs = require('fs');
var path = require('path');
var vm = require('vm');

var ROOT = path.join(__dirname, '..');
var html = fs.readFileSync(path.join(ROOT, 'report-doctor.html'), 'utf8');
var script = fs.readFileSync(path.join(ROOT, 'report-doctor.js'), 'utf8');

function fixture(name) {
  return fs.readFileSync(path.join(__dirname, 'fixtures', 'report_doctor', name), 'utf8');
}

// ---------------------------------------------------------------------------
// 1a. Page structure and wording
// ---------------------------------------------------------------------------

// The end of the element that starts at `start`, counting nested tags of the
// same name.
function elementEnd(source, start, tagName) {
  var pattern = new RegExp('<(/?)' + tagName + '\\b[^>]*>', 'gi');
  pattern.lastIndex = start;
  var depth = 0;
  var match;
  while ((match = pattern.exec(source))) {
    depth += match[1] ? -1 : 1;
    if (depth === 0) return pattern.lastIndex;
  }
  throw new Error('unclosed <' + tagName + '> at ' + start);
}

var outputStart = html.indexOf('<section id="doctor-output"');
var tagsStart = html.indexOf('id="doctor-tags-section"');
assert.ok(outputStart >= 0, '#doctor-output section must exist');
assert.ok(tagsStart >= 0, '#doctor-tags-section must exist');
var outputEnd = elementEnd(html, outputStart, 'section');
assert.ok(
  tagsStart < outputStart || tagsStart > outputEnd,
  'the parts list must not sit inside #doctor-output, or it stays hidden until a report is analyzed'
);
assert.ok(!/Tags tab/i.test(html) && !/Tags tab/i.test(script), 'there is no Tags tab; the wording must not mention one');
var bootstrapLabel = html.match(/<label for="bootstrap-file"[^>]*>([^<]*)<\/label>/);
assert.ok(bootstrapLabel && /parts list/i.test(bootstrapLabel[1]) && /parts_bootstrap\.json/.test(bootstrapLabel[1]),
  'the parts picker label must name the parts list and the file');
assert.ok(/<label for="bootstrap-json"/.test(html), 'the parts paste box needs its own label');

// ---------------------------------------------------------------------------
// DOM stub built from the page (ids and their starting classes)
// ---------------------------------------------------------------------------

var innerHTMLWrites = [];

function StubElement(tagName, className) {
  this.tagName = String(tagName || 'div').toUpperCase();
  this.childNodes = [];
  this.attributes = {};
  this.listeners = {};
  this.className = className || '';
  this._textContent = '';
  this.value = '';
  this.href = '';
  this.files = [];
  this.style = {};
  var classes = new Set(String(className || '').split(/\s+/).filter(Boolean));
  this.classList = {
    add: classes.add.bind(classes),
    remove: classes.delete.bind(classes),
    contains: classes.has.bind(classes)
  };
}
Object.defineProperty(StubElement.prototype, 'innerHTML', {
  get: function() { return ''; },
  set: function(v) { innerHTMLWrites.push(String(v)); }
});
Object.defineProperty(StubElement.prototype, 'textContent', {
  get: function() {
    return this._textContent + this.childNodes.map(function(c) { return c.textContent; }).join(' ');
  },
  set: function(v) { this._textContent = String(v); this.childNodes = []; }
});
Object.defineProperty(StubElement.prototype, 'firstChild', {
  get: function() { return this.childNodes.length ? this.childNodes[0] : null; }
});
StubElement.prototype.appendChild = function(child) { this.childNodes.push(child); return child; };
StubElement.prototype.removeChild = function(child) {
  var i = this.childNodes.indexOf(child);
  if (i >= 0) this.childNodes.splice(i, 1);
  return child;
};
StubElement.prototype.insertBefore = function(node, ref) {
  var i = ref ? this.childNodes.indexOf(ref) : -1;
  if (i >= 0) this.childNodes.splice(i, 0, node); else this.childNodes.unshift(node);
  return node;
};
StubElement.prototype.setAttribute = function(name, value) { this.attributes[name] = String(value); };
StubElement.prototype.getAttribute = function(name) {
  return Object.prototype.hasOwnProperty.call(this.attributes, name) ? this.attributes[name] : null;
};
StubElement.prototype.addEventListener = function(type, fn) {
  (this.listeners[type] = this.listeners[type] || []).push(fn);
};
StubElement.prototype.dispatch = function(type) {
  (this.listeners[type] || []).forEach(function(fn) { fn.call(this); }, this);
};
StubElement.prototype.querySelectorAll = function(selector) {
  var cls = selector.slice(1);
  var out = [];
  (function walk(node) {
    node.childNodes.forEach(function(child) {
      if (String(child.className || '').split(/\s+/).indexOf(cls) >= 0) out.push(child);
      walk(child);
    });
  })(this);
  return out;
};

function loadPage() {
  var elements = {};
  var tagPattern = /<([A-Za-z][\w-]*)\b([^>]*)>/g;
  var match;
  while ((match = tagPattern.exec(html))) {
    var id = match[2].match(/\bid="([^"]+)"/);
    if (!id) continue;
    var cls = match[2].match(/\bclass="([^"]*)"/);
    elements[id[1]] = new StubElement(match[1], cls ? cls[1] : '');
  }
  function FileReader() {}
  FileReader.prototype.readAsText = function(file) {
    this.result = file.contents;
    this.onload();
  };
  vm.runInNewContext(script, {
    document: {
      getElementById: function(id) { return elements[id] || null; },
      createElement: function(tag) { return new StubElement(tag); }
    },
    navigator: {},
    FileReader: FileReader,
    setTimeout: setTimeout,
    console: console
  }, { filename: 'report-doctor.js' });
  return elements;
}

function visible(el) { return !el.classList.contains('hidden'); }

function tableRows(elements) {
  var table = elements['doctor-tags-table'].childNodes[0];
  if (!table) return [];
  return table.childNodes[1].childNodes.map(function(tr) {
    return tr.childNodes.map(function(td) { return td.textContent; });
  });
}

var IMPORTER_PARTS = fixture('parts_bootstrap_importer.json');
var IMPORTER_EMPTY = fixture('parts_bootstrap_importer_no_rows.json');
var EXPECTED_ROWS = [
  ['EX101', 'W12X26', '2', '— (no part_id in sidecar)', ''],
  ['EX102', 'L3X3X1/4', '4', '— (no part_id in sidecar)', ''],
  ['EX103', 'PL1/2"X8', '1', '— (no part_id in sidecar)', '']
];
var NO_LINK_SUMMARY = '3 parts listed. No row carries a part_id, so there are no tag links.';

// ---------------------------------------------------------------------------
// 1b/2. A real importer parts file on its own
// ---------------------------------------------------------------------------

// File picker, no report.
var page = loadPage();
assert.ok(!visible(page['doctor-tags-section']) && !visible(page['doctor-output']), 'both result areas start hidden');
page['bootstrap-file'].files = [{ contents: IMPORTER_PARTS }];
page['bootstrap-file'].dispatch('change');
assert.strictEqual(page['bootstrap-json'].value, IMPORTER_PARTS);
assert.strictEqual(page['doctor-error'].textContent, '');
assert.ok(visible(page['doctor-tags-section']), 'a parts file alone must show the parts list');
assert.ok(!visible(page['doctor-output']), 'a parts file alone has no report diagnosis');
assert.deepStrictEqual(tableRows(page), EXPECTED_ROWS);
assert.strictEqual(page['doctor-tags-summary'].textContent, NO_LINK_SUMMARY);
assert.strictEqual(page['doctor-tags-table'].querySelectorAll('.copy-tag').length, 0);

// Analyze with an empty report box lists the parts again; no error.
page['analyze-report'].dispatch('click');
assert.strictEqual(page['doctor-error'].textContent, '');
assert.ok(visible(page['doctor-tags-section']));
assert.ok(!visible(page['doctor-output']));
assert.deepStrictEqual(tableRows(page), EXPECTED_ROWS);
assert.strictEqual(page['doctor-tags-table'].childNodes.length, 1, 'the table is replaced, not appended');

// Paste + blur, no report.
page = loadPage();
page['bootstrap-json'].value = IMPORTER_PARTS;
page['bootstrap-json'].dispatch('blur');
assert.ok(visible(page['doctor-tags-section']));
assert.deepStrictEqual(tableRows(page), EXPECTED_ROWS);

// With a report too: the diagnosis and the parts list both show.
page['report-json'].value = JSON.stringify({
  schema: 'bcs.import_report/1.1', host: { app: 'freecad' }, result: { pages: 1, primitives: 7 },
  extra: { text_mode: 'labels', result_status: 'success' }
});
page['analyze-report'].dispatch('click');
assert.strictEqual(page['doctor-error'].textContent, '');
assert.ok(visible(page['doctor-output']));
assert.ok(visible(page['doctor-tags-section']));
assert.deepStrictEqual(tableRows(page), EXPECTED_ROWS);

// Clear hides everything again.
page['clear-report'].dispatch('click');
assert.ok(!visible(page['doctor-tags-section']) && !visible(page['doctor-output']));
assert.strictEqual(page['doctor-tags-summary'].textContent, '');
assert.strictEqual(page['doctor-tags-table'].childNodes.length, 0);

// Nothing loaded at all: Analyze explains what to load.
page['analyze-report'].dispatch('click');
assert.ok(/parts file/i.test(page['doctor-error'].textContent), 'the empty-request message must mention the parts file option');
assert.ok(!visible(page['doctor-tags-section']));

// An importer file with no rows says so, with the file's own note.
page = loadPage();
page['bootstrap-json'].value = IMPORTER_EMPTY;
page['analyze-report'].dispatch('click');
assert.strictEqual(page['doctor-error'].textContent, '');
assert.ok(visible(page['doctor-tags-section']));
assert.strictEqual(page['doctor-tags-table'].childNodes.length, 0);
assert.strictEqual(page['doctor-tags-summary'].textContent,
  'This parts file lists no parts (note in the file: no BOM rows detected).');

// A JSON object with no rows, parts or candidates is not a parts file.
page['bootstrap-json'].value = '{"schema":"bcs.parts_bootstrap/1.0","note":"x"}';
page['analyze-report'].dispatch('click');
assert.ok(/rows, parts, or candidates/.test(page['doctor-error'].textContent));
assert.ok(!visible(page['doctor-tags-section']));

// ---------------------------------------------------------------------------
// 3. Audit 7b: tag links for rows that carry a part_id
// ---------------------------------------------------------------------------

var demoRecord = JSON.parse(fs.readFileSync(path.join(ROOT, 'p-records', 'demo-part.json'), 'utf8'));
var withIds = JSON.parse(IMPORTER_PARTS);
var UUID = '0f8fad5b-d9cb-469f-a165-70867728950e';
withIds.rows[0].part_id = demoRecord.part_id;
withIds.rows[1].part_id = UUID;
page = loadPage();
page['bootstrap-json'].value = JSON.stringify(withIds);
page['analyze-report'].dispatch('click');
var linkedRows = tableRows(page);
assert.strictEqual(linkedRows[0][3], demoRecord.tag_url,
  'the tag link must be exactly the URL the published part record uses');
assert.strictEqual(linkedRows[1][3], 'https://bluecollar-systems.com/p/' + UUID);
assert.strictEqual(linkedRows[2][3], '— (no part_id in sidecar)');
var copyButtons = page['doctor-tags-table'].querySelectorAll('.copy-tag');
assert.deepStrictEqual(copyButtons.map(function(b) { return b.getAttribute('data-url'); }),
  [demoRecord.tag_url, 'https://bluecollar-systems.com/p/' + UUID]);
assert.strictEqual(copyButtons[0].getAttribute('aria-label'), 'Copy tag URL for EX101');
assert.strictEqual(page['doctor-tags-summary'].textContent,
  '3 parts listed. 2 of 3 have a tag link; the others carry no valid part_id.');
withIds.rows[2].part_id = 'EX103.rev-2_b';
page['bootstrap-json'].value = JSON.stringify(withIds);
page['bootstrap-json'].dispatch('blur');
assert.strictEqual(page['doctor-tags-summary'].textContent, '3 parts listed. Every part has a tag link.');
assert.strictEqual(innerHTMLWrites.length, 0, 'the parts list must never use innerHTML');

// Every ID Report Doctor links must be one the part page (/p/<id>) accepts,
// so a copied tag link never lands on "Invalid or missing Part Tracking ID".
var resolver = fs.readFileSync(path.join(ROOT, 'part-resolver.js'), 'utf8');
var resolverPattern = resolver.match(/if \(!id \|\| !(\/\^[^\n]*?\$\/)\.test\(id\)\)/);
assert.ok(resolverPattern, 'could not find the part page ID check in part-resolver.js');
var accepts = vm.runInNewContext(resolverPattern[1]);
[demoRecord.part_id, UUID, 'EX103.rev-2_b', 'A', 'a'.repeat(64)].forEach(function(id) {
  var url = 'https://bluecollar-systems.com/p/' + encodeURIComponent(id);
  var decoded = decodeURIComponent(url.split('/p/')[1]);
  assert.ok(accepts.test(decoded), 'the part page must accept linked ID ' + id);
});

// ---------------------------------------------------------------------------
// 4. LibreCAD text advice
// ---------------------------------------------------------------------------

function report(host, textMode, result, extra) {
  return {
    schema: 'bcs.import_report/1.1',
    host: { app: host, version: '1.0.108' },
    result: Object.assign({ pages: 1, geometry: 120 }, result || {}),
    extra: Object.assign({ text_mode: textMode, requested_mode: 'auto', resolved_mode: 'vector' }, extra || {})
  };
}

var EDITABLE = 'Editable text (LibreCAD font)';
// Advice that is wrong for LibreCAD, where Labels and 3D Text come in as the
// same outlines as Exact look and the window has no Raster/Hybrid choice.
var LIBRECAD_NEVER = [
  'Use Labels', 'Try Labels', 'compare against Labels mode', 'Labels for editable',
  'once your LibreCAD importer has it', 'Until that release', 'Raster/Hybrid',
  'editable labels where the host can support it'
];

var CASES = [
  { name: 'LibreCAD Exact look (main: glyphs)', report: report('librecad', 'glyphs'), actions: [EDITABLE, 'Exact look'] },
  { name: 'LibreCAD Exact look (v1.0.108: text)', report: report('librecad', 'text'), actions: [EDITABLE], findings: ['Exact look'] },
  { name: 'LibreCAD raw outlines', report: report('librecad', 'geometry'), actions: [EDITABLE] },
  { name: 'LibreCAD Labels', report: report('librecad', 'labels', { glyphs: 40 }), actions: [EDITABLE], findings: ['DXF has no label entity'], status: 'Healthy' },
  { name: 'LibreCAD 3D Text', report: report('librecad', '3d_text'), actions: [EDITABLE], findings: ['LibreCAD is 2D-only'] },
  { name: 'LibreCAD dense page', report: report('librecad', 'glyphs', { glyphs: 6000 }), actions: [EDITABLE] },
  {
    name: 'LibreCAD Editable text chosen',
    report: report('librecad', 'text', null, { editable_text: { chosen: true, item_count: 12, font: 'LibreCAD unicode' } }),
    findings: ['"Editable text (LibreCAD font)" was chosen: 12 text item(s) came in as editable text'],
    actionsNot: [EDITABLE]
  },
  {
    name: 'LibreCAD Raster result',
    report: report('librecad', 'glyphs', null, { resolved_mode: 'raster' }),
    actions: ['--mode vector', EDITABLE],
    actionsNot: ['retry with Auto or Vector']
  },
  // Other hosts keep their advice.
  { name: 'SketchUp glyphs', report: report('sketchup', 'glyphs'), actions: ['Use Labels or 3D Text if the downstream workflow needs editable text.'], allNot: ['LibreCAD'] },
  { name: 'SketchUp 3D Text', report: report('sketchup', '3d_text'), actions: ['compare against Labels mode'], allNot: ['LibreCAD'] },
  { name: 'FreeCAD dense page', report: report('freecad', 'glyphs', { glyphs: 6000 }), actions: ['Try Labels for editable text'], allNot: ['LibreCAD'] },
  { name: 'Blender Labels with outlines', report: report('blender', 'labels', { glyphs: 40 }), findings: ['even though Labels mode was requested'], status: 'Review' }
];

page = loadPage();
CASES.forEach(function(c) {
  page['report-json'].value = JSON.stringify(c.report);
  page['analyze-report'].dispatch('click');
  assert.strictEqual(page['doctor-error'].textContent, '', c.name + ': report was rejected');
  var actions = page['doctor-actions'].textContent;
  var findings = page['doctor-findings'].textContent;
  var isLibreCAD = c.report.host.app === 'librecad';
  (c.actions || []).forEach(function(s) {
    assert.ok(actions.indexOf(s) >= 0, c.name + ': actions must mention "' + s + '"; got: ' + actions);
  });
  (c.findings || []).forEach(function(s) {
    assert.ok(findings.indexOf(s) >= 0, c.name + ': findings must mention "' + s + '"; got: ' + findings);
  });
  (c.actionsNot || []).forEach(function(s) {
    assert.ok(actions.indexOf(s) < 0, c.name + ': actions must not say "' + s + '"');
  });
  (isLibreCAD ? LIBRECAD_NEVER : []).concat(c.allNot || []).forEach(function(s) {
    assert.ok((actions + findings).indexOf(s) < 0, c.name + ': must not say "' + s + '"');
  });
  if (c.status) assert.strictEqual(page['doctor-status'].textContent, c.status, c.name + ': status');
  var editableMentions = actions.split(EDITABLE).length - 1;
  assert.ok(editableMentions <= 1, c.name + ': the Editable text advice must be given at most once');
});

console.log('PASS report_doctor_parts_list_test: parts list without a report (picker, paste, Analyze), importer files with and without rows, ' +
  'part_id tag links match the published record, ' + CASES.length + ' text-advice cases');
