'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '..', 'report-doctor.js'), 'utf8');

function harness(clipboard, fallback = false) {
  const elements = {};
  const readers = [];
  const copied = [];
  function element() {
    const classes = new Set();
    const node = {
      childNodes: [], attributes: {}, listeners: {}, style: {}, value: '', textContent: '', files: [],
      classList: { add: classes.add.bind(classes), remove: classes.delete.bind(classes) },
      appendChild(child) { this.childNodes.push(child); return child; },
      removeChild(child) { this.childNodes.splice(this.childNodes.indexOf(child), 1); },
      setAttribute(name, value) { this.attributes[name] = String(value); },
      getAttribute(name) { return this.attributes[name]; },
      addEventListener(type, fn) { this.listeners[type] = fn; },
      dispatch(type) { this.listeners[type]?.call(this); },
      select() { copied.push(this.value); }, focus() {},
      querySelectorAll(selector) {
        const matches = [];
        function visit(current) {
          current.childNodes.forEach((child) => {
            if (String(child.className || '').split(' ').includes(selector.slice(1))) matches.push(child);
            visit(child);
          });
        }
        visit(this);
        return matches;
      }
    };
    Object.defineProperty(node, 'firstChild', { get() { return this.childNodes[0]; } });
    return node;
  }
  const document = {
    body: element(),
    getElementById(id) { return elements[id] || (elements[id] = element()); },
    createElement: element,
    execCommand() { return fallback; }
  };
  class FileReader {
    constructor() { readers.push(this); }
    readAsText(file) { this.file = file; }
  }
  vm.runInNewContext(source, { document, navigator: { clipboard }, FileReader, setTimeout() {} });
  function sidecar(rows) {
    elements['bootstrap-json'].value = JSON.stringify({ schema: 'bcs.parts_bootstrap/1.0', rows });
    elements['bootstrap-json'].dispatch('blur');
    return elements['doctor-tags-table'].querySelectorAll('.copy-tag');
  }
  function select(id) {
    elements[id].files = [{ name: 'fictional.json' }];
    elements[id].dispatch('change');
    return readers[readers.length - 1];
  }
  return { elements, document, copied, sidecar, select };
}
const row = { part_id: 'training-part', piece_mark: 'DEMO-1', quantity: 0 };

test('tag copy confirms success and preserves zero quantities', async () => {
  const writes = [];
  const h = harness({ writeText: async (value) => { writes.push(value); } });
  const button = h.sidecar([row])[0];
  const table = h.elements['doctor-tags-table'].childNodes[0];
  assert.equal(table.childNodes[1].childNodes[0].childNodes[2].textContent, '0');
  assert.equal(button.attributes['aria-label'], 'Copy tag URL for DEMO-1');
  button.dispatch('click');
  await new Promise(setImmediate);
  assert.deepEqual(writes, ['https://bluecollar-systems.com/p/training-part']);
  assert.equal(button.textContent, 'Copied');
});

for (const [name, clipboard] of [
  ['unavailable', undefined],
  ['rejected', { writeText: async () => { throw new Error('denied'); } }],
  ['throws', { writeText() { throw new Error('denied'); } }]
]) {
  test('clipboard fallback works when API is ' + name, async () => {
    const h = harness(clipboard, true);
    const button = h.sidecar([row])[0];
    button.dispatch('click');
    await new Promise(setImmediate);
    assert.equal(button.textContent, 'Copied');
    assert.deepEqual(h.copied, ['https://bluecollar-systems.com/p/training-part']);
    assert.equal(h.document.body.childNodes.length, 0);
  });
}

test('failed copy offers manual recovery without a rejected promise', async () => {
  const h = harness({ writeText: async () => { throw new Error('denied'); } });
  h.sidecar([row])[0].dispatch('click');
  await new Promise(setImmediate);
  assert.match(h.elements['doctor-error'].textContent, /Select the displayed text/);
  assert.equal(h.document.body.childNodes.length, 0);
});

test('invalid sidecars explain parse, shape, and schema failures', () => {
  const h = harness();
  for (const [value, message] of [['{', /parse parts sidecar/], ['null', /JSON object/], ['[]', /JSON object/], ['{"schema":"other"}', /Unsupported/]]) {
    h.elements['bootstrap-json'].value = value;
    h.elements['bootstrap-json'].dispatch('blur');
    assert.match(h.elements['doctor-error'].textContent, message);
  }
});

test('older file reads cannot overwrite a newer selected file', () => {
  const h = harness();
  for (const [picker, input, contents] of [
    ['report-file', 'report-json', 'invalid new report'],
    ['bootstrap-file', 'bootstrap-json', '{"rows":[]}']
  ]) {
    const older = h.select(picker);
    const newer = h.select(picker);
    newer.result = contents;
    newer.onload();
    older.result = 'old stale contents';
    older.onload();
    assert.equal(h.elements[input].value, contents);
  }
});

test('Clear invalidates pending file reads and file errors explain recovery', () => {
  const h = harness();
  const report = h.select('report-file');
  const sidecar = h.select('bootstrap-file');
  h.elements['clear-report'].dispatch('click');
  report.result = 'late report';
  sidecar.result = 'late sidecar';
  report.onload();
  sidecar.onload();
  assert.equal(h.elements['report-json'].value, '');
  assert.equal(h.elements['bootstrap-json'].value, '');
  h.select('bootstrap-file').onerror();
  assert.match(h.elements['doctor-error'].textContent, /Could not read the selected parts sidecar/);
  h.select('report-file').onerror();
  assert.match(h.elements['doctor-error'].textContent, /Could not read the selected file/);
});
