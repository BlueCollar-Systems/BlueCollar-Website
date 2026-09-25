'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'part-resolver.js'), 'utf8');

async function resolve(pathname, record) {
  const nodes = {};
  for (const id of ['part-id', 'deep-link', 'part-status', 'part-details', 'unpublished-panel']) {
    nodes[id] = { textContent: '', href: '#', hidden: true, innerHTML: '' };
  }
  const requests = [];
  const context = {
    location: { pathname },
    document: { getElementById: (id) => nodes[id], title: '' },
    fetch: (url) => {
      requests.push(url);
      return Promise.resolve(record
        ? { status: 200, ok: true, json: () => Promise.resolve(record) }
        : { status: 404, ok: false });
    }
  };
  vm.runInNewContext(source, context, { filename: 'part-resolver.js' });
  await new Promise((done) => setImmediate(done));
  return { nodes, requests };
}

(async function () {
  for (const route of ['/p/%E0%A4%A', '/p/%', '/p/%FF', '/p/']) {
    const result = await resolve(route);
    assert.strictEqual(result.nodes['part-id'].textContent, 'unknown', route);
    assert.match(result.nodes['part-status'].textContent, /Invalid or missing Part Tracking ID/);
    assert.strictEqual(result.nodes['deep-link'].href, 'steellogic://open');
    assert.deepStrictEqual(result.requests, [], 'invalid routes must not request a record');
  }
  const record = { schema: 'bcs.part/1.0', part_id: 'demo-part', piece_mark: 'DEMO-W10X22' };
  for (const route of ['/p/demo-part', '/p/demo%2Dpart', '/p/demo%2Dpart/']) {
    const result = await resolve(route, record);
    assert.deepStrictEqual(result.requests, ['/p-records/demo-part.json']);
    assert.strictEqual(result.nodes['part-status'].textContent, 'Published part record');
    assert.strictEqual(result.nodes['deep-link'].href, 'steellogic://part/demo-part');
  }
  const slash = await resolve('/p/demo%2Fpart');
  assert.deepStrictEqual(slash.requests, ['/p-records/demo%2Fpart.json']);
  assert.strictEqual(slash.nodes['part-status'].textContent, 'Part not published');
  assert.strictEqual(slash.nodes['deep-link'].href, 'steellogic://part/demo%2Fpart');
  console.log('PASS part resolver: 4 invalid, 3 published/encoded, 1 encoded-slash routes');
})().catch((error) => { console.error(error); process.exitCode = 1; });
