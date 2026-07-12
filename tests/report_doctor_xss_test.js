// Report Doctor hostile-sidecar DOM-XSS regression test (Round 21 corrective
// spec section 6). Runs under plain `node tests/report_doctor_xss_test.js`
// with a minimal DOM stub — no browser, no dependencies.
//
// Contract under test:
//  1. report-doctor.js loads without throwing (a load-time throw silently
//     detaches every later event listener — the 3a7564a regression class).
//  2. A sidecar with '<img src=x onerror=alert(1)>' in EVERY displayed field
//     renders literal text: no element is created from the payload, no
//     event-handler attribute appears, and no innerHTML assignment happens
//     anywhere in the Tags rendering path.
//  3. A row without part_id gets NO tag link and NO random UUID.
//  4. A valid opaque part_id yields exactly the fixed-origin encoded
//     https://bluecollar-systems.com/p/<id> URL (text + copy button data-url).
//  5. A hostile/malformed part_id is rejected: no tag link.
'use strict';

var fs = require('fs');
var path = require('path');
var vm = require('vm');
var assert = require('assert');

// ---------------------------------------------------------------------------
// Minimal DOM stub
// ---------------------------------------------------------------------------

var innerHTMLWrites = [];

function StubElement(tagName) {
  this.tagName = String(tagName || 'div').toUpperCase();
  this.childNodes = [];
  this.attributes = {};
  this.listeners = {};
  this.className = '';
  this._textContent = '';
  this.value = '';
  this.href = '';
  this.hidden = false;
  this.classList = {
    add: function () {},
    remove: function () {}
  };
}

Object.defineProperty(StubElement.prototype, 'innerHTML', {
  get: function () { return ''; },
  set: function (v) {
    innerHTMLWrites.push({ tag: this.tagName, html: String(v) });
  }
});

Object.defineProperty(StubElement.prototype, 'textContent', {
  get: function () { return this._textContent; },
  set: function (v) { this._textContent = String(v); }
});

Object.defineProperty(StubElement.prototype, 'firstChild', {
  get: function () { return this.childNodes.length ? this.childNodes[0] : null; }
});

StubElement.prototype.appendChild = function (child) {
  this.childNodes.push(child);
  return child;
};

StubElement.prototype.removeChild = function (child) {
  var i = this.childNodes.indexOf(child);
  if (i >= 0) this.childNodes.splice(i, 1);
  return child;
};

StubElement.prototype.insertBefore = function (node, ref) {
  var i = ref ? this.childNodes.indexOf(ref) : -1;
  if (i >= 0) this.childNodes.splice(i, 0, node);
  else this.childNodes.unshift(node);
  return node;
};

StubElement.prototype.setAttribute = function (name, value) {
  this.attributes[String(name)] = String(value);
};

StubElement.prototype.getAttribute = function (name) {
  return Object.prototype.hasOwnProperty.call(this.attributes, name)
    ? this.attributes[name]
    : null;
};

StubElement.prototype.addEventListener = function (type, fn) {
  (this.listeners[type] = this.listeners[type] || []).push(fn);
};

StubElement.prototype.dispatch = function (type) {
  var fns = this.listeners[type] || [];
  for (var i = 0; i < fns.length; i++) fns[i].call(this);
};

StubElement.prototype.querySelectorAll = function (selector) {
  var cls = selector.charAt(0) === '.' ? selector.slice(1) : null;
  var out = [];
  (function walk(node) {
    for (var i = 0; i < node.childNodes.length; i++) {
      var child = node.childNodes[i];
      if (cls !== null && String(child.className || '').split(/\s+/).indexOf(cls) >= 0) {
        out.push(child);
      }
      walk(child);
    }
  })(this);
  return out;
};

function collectDescendants(root) {
  var out = [];
  (function walk(node) {
    for (var i = 0; i < node.childNodes.length; i++) {
      out.push(node.childNodes[i]);
      walk(node.childNodes[i]);
    }
  })(root);
  return out;
}

function rowText(tr) {
  return collectDescendants(tr)
    .map(function (n) { return n.textContent; })
    .concat([tr.textContent])
    .join(' ');
}

// Every element id report-doctor.js queries.
var IDS = [
  'report-file', 'report-json', 'analyze-report', 'clear-report',
  'doctor-error', 'doctor-output', 'doctor-title', 'doctor-status',
  'doctor-metrics', 'doctor-findings', 'doctor-actions', 'doctor-support',
  'copy-support', 'email-support', 'bootstrap-file', 'bootstrap-json',
  'doctor-tags-section', 'doctor-tags-table'
];

var elements = {};
IDS.forEach(function (id) { elements[id] = new StubElement('div'); });

var documentStub = {
  getElementById: function (id) { return elements[id] || null; },
  createElement: function (tag) { return new StubElement(tag); }
};

// ---------------------------------------------------------------------------
// Load report-doctor.js
// ---------------------------------------------------------------------------

var source = fs.readFileSync(path.join(__dirname, '..', 'report-doctor.js'), 'utf8');
var sandbox = {
  document: documentStub,
  navigator: {},
  console: console,
  setTimeout: setTimeout
};

try {
  vm.runInNewContext(source, sandbox, { filename: 'report-doctor.js' });
} catch (err) {
  console.error('FAIL: report-doctor.js threw at load time — every listener');
  console.error('registered after the throw is silently dead in production.');
  throw err;
}

// ---------------------------------------------------------------------------
// Drive the Tags tab with a hostile sidecar
// ---------------------------------------------------------------------------

var HOSTILE = '<img src=x onerror=alert(1)>';
var VALID_ID = '0f8fad5b-d9cb-469f-a165-70867728950e';
var sidecar = {
  schema: 'bcs.parts_bootstrap/1.0',
  rows: [
    // 0: hostile markup in every displayed field, including part_id
    { piece_mark: HOSTILE, profile_hint: HOSTILE, quantity: HOSTILE, part_id: HOSTILE },
    // 1: valid opaque part_id, hostile piece mark
    { piece_mark: HOSTILE, profile_hint: 'W12x26', quantity: 2, part_id: VALID_ID },
    // 2: no part_id at all
    { piece_mark: 'C3', profile_hint: 'L3x3x1/4', quantity: 1 },
    // 3: attribute-injection attempt in part_id and quote-laden text fields
    { piece_mark: 'D"4', profile_hint: 'attr" onmouseover="alert(1)', quantity: 4, part_id: 'abc" onmouseover="alert(1)' }
  ]
};

var bootstrapInput = elements['bootstrap-json'];
var tagsTable = elements['doctor-tags-table'];

assert.ok(
  (bootstrapInput.listeners.blur || []).length > 0,
  'bootstrap-json blur listener was never attached (load-time regression?)'
);

bootstrapInput.value = JSON.stringify(sidecar);
bootstrapInput.dispatch('blur');

// ---------------------------------------------------------------------------
// Assertions
// ---------------------------------------------------------------------------

// A. The rendering path must never assign innerHTML at all.
assert.strictEqual(
  innerHTMLWrites.length, 0,
  'innerHTML was assigned during Tags rendering: ' + JSON.stringify(innerHTMLWrites)
);

// B. Only the expected table elements exist — the hostile payload must not
//    materialize as an element of any kind.
var ALLOWED_TAGS = ['TABLE', 'THEAD', 'TBODY', 'TR', 'TH', 'TD', 'BUTTON'];
var everything = collectDescendants(tagsTable);
everything.forEach(function (node) {
  assert.ok(
    ALLOWED_TAGS.indexOf(node.tagName) >= 0,
    'unexpected element created during rendering: <' + node.tagName + '>'
  );
});

// C. No event-handler attribute and no attribute other than data-url.
everything.forEach(function (node) {
  Object.keys(node.attributes).forEach(function (name) {
    assert.ok(!/^on/i.test(name), 'event-handler attribute injected: ' + name);
    assert.strictEqual(name, 'data-url', 'unexpected attribute: ' + name);
  });
});

var table = tagsTable.childNodes[0];
assert.ok(table && table.tagName === 'TABLE', 'tags table was not rendered');
var tbody = table.childNodes[1];
assert.ok(tbody && tbody.tagName === 'TBODY', 'tbody missing');
var trs = tbody.childNodes;
assert.strictEqual(trs.length, 4, 'expected 4 rendered rows, got ' + trs.length);

var UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

// Row 0: every field hostile — literal text, no tag link.
var r0 = trs[0].childNodes;
assert.strictEqual(r0[0].textContent, HOSTILE, 'piece mark must render the payload literally');
assert.strictEqual(r0[1].textContent, HOSTILE, 'profile must render the payload literally');
assert.strictEqual(r0[2].textContent, HOSTILE, 'quantity must render the payload literally');
assert.ok(rowText(trs[0]).indexOf('bluecollar-systems.com') < 0, 'hostile part_id must not produce a tag URL');
assert.strictEqual(trs[0].querySelectorAll('.copy-tag').length, 0, 'hostile part_id row must have no copy button');

// Row 1: valid opaque part_id — exactly the fixed-origin encoded URL.
var expectedUrl = 'https://bluecollar-systems.com/p/' + encodeURIComponent(VALID_ID);
var r1 = trs[1].childNodes;
assert.strictEqual(r1[0].textContent, HOSTILE, 'hostile mark next to a valid id still renders literally');
assert.strictEqual(r1[3].textContent, expectedUrl, 'valid part_id must yield the fixed-origin encoded tag URL');
var copyButtons = trs[1].querySelectorAll('.copy-tag');
assert.strictEqual(copyButtons.length, 1, 'valid part_id row must have one copy button');
assert.strictEqual(copyButtons[0].getAttribute('data-url'), expectedUrl, 'copy button data-url must match the tag URL');

// Row 2: no part_id — no tag link, and no random UUID minted.
assert.ok(rowText(trs[2]).indexOf('bluecollar-systems.com') < 0, 'row without part_id must not get a tag URL');
assert.ok(!UUID_RE.test(rowText(trs[2])), 'row without part_id must not receive a random UUID');
assert.strictEqual(trs[2].childNodes[3].textContent, '— (no part_id in sidecar)');

// Row 3: attribute-injection part_id rejected; quoted text renders literally.
var r3 = trs[3].childNodes;
assert.strictEqual(r3[0].textContent, 'D"4');
assert.strictEqual(r3[1].textContent, 'attr" onmouseover="alert(1)');
assert.ok(rowText(trs[3]).indexOf('bluecollar-systems.com') < 0, 'malformed part_id must not produce a tag URL');
assert.strictEqual(trs[3].querySelectorAll('.copy-tag').length, 0, 'malformed part_id row must have no copy button');

// D. Re-render replaces (not appends) the table.
bootstrapInput.dispatch('blur');
assert.strictEqual(tagsTable.childNodes.length, 1, 're-render must replace the previous table');
assert.strictEqual(innerHTMLWrites.length, 0, 're-render must not assign innerHTML');

console.log('PASS report_doctor_xss_test: hostile sidecar rendered as literal text;');
console.log('  no injected elements/attributes, no innerHTML, no random UUIDs,');
console.log('  valid part_id -> ' + expectedUrl);
