'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const script = fs.readFileSync(path.join(__dirname, '..', 'part-resolver.js'), 'utf8');

async function resolvePart(pathname, response) {
  const elements = {};
  for (const id of ['part-id', 'deep-link', 'part-status', 'part-details', 'unpublished-panel']) {
    elements[id] = { textContent: '', href: '#', hidden: true, innerHTML: '' };
  }
  const requests = [];
  const document = { getElementById: (id) => elements[id], title: '' };
  vm.runInNewContext(script, {
    location: { pathname },
    document,
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (response instanceof Error) throw response;
      return {
        status: response?.status ?? 200,
        ok: (response?.status ?? 200) >= 200 && (response?.status ?? 200) < 300,
        json: async () => {
          if (response?.jsonError) throw response.jsonError;
          return response?.payload;
        }
      };
    }
  });
  await new Promise((done) => setImmediate(done));
  return { elements, requests, document };
}

const record = {
  schema: 'bcs.part/1.0',
  part_id: 'training-part',
  piece_mark: 'TRAINING-B1',
  profile_hint: 'W8X18',
  quantity: 0,
  tag_url: 'https://bluecollar-systems.com/p/training-part'
};

test('valid published part keeps its requested identity and displays zero quantity', async () => {
  const { elements, requests, document } = await resolvePart('/p/training%2Dpart/', { payload: record });
  assert.equal(requests[0].url, '/p-records/training-part.json');
  assert.equal(requests[0].options.cache, 'no-store');
  assert.equal(elements['part-id'].textContent, 'training-part');
  assert.equal(elements['deep-link'].href, 'steellogic://part/training-part');
  assert.equal(elements['part-status'].textContent, 'Published part record');
  assert.equal(elements['part-details'].hidden, false);
  assert.match(elements['part-details'].innerHTML, /<dt>Quantity<\/dt><dd>0<\/dd>/);
  assert.match(document.title, /training-part/);
});

test('malformed or unsupported IDs show invalid-link feedback without fetching', async () => {
  for (const pathname of ['/p/%', '/p/%E0%A4%A', '/p/a%3Fb', '/p/%3Cbad%3E', '/p/%25', '/p/' + 'a'.repeat(65), '/p/']) {
    const { elements, requests } = await resolvePart(pathname);
    assert.equal(requests.length, 0, pathname);
    assert.equal(elements['part-id'].textContent, 'unknown', pathname);
    assert.equal(elements['deep-link'].href, 'steellogic://open', pathname);
    assert.equal(elements['part-status'].textContent, 'Invalid or missing Part Tracking ID.', pathname);
  }
});

test('encoded historical Steel Logic IDs retain their original accepted alphabet', async () => {
  const id = 'training /part#1';
  const { elements, requests } = await resolvePart('/p/' + encodeURIComponent(id), { payload: { ...record, part_id: id } });
  assert.equal(elements['part-status'].textContent, 'Published part record');
  assert.equal(elements['part-id'].textContent, id);
  assert.equal(elements['deep-link'].href, 'steellogic://part/' + encodeURIComponent(id));
  assert.equal(requests[0].url, '/p-records/' + encodeURIComponent(id) + '.json');
});

test('a mirror for another part never changes the requested app link or displays its record', async () => {
  const { elements } = await resolvePart('/p/training-part', { payload: { ...record, part_id: 'other-training-part' } });
  assert.match(elements['part-status'].textContent, /does not match/);
  assert.equal(elements['part-details'].hidden, true);
  assert.equal(elements['part-details'].innerHTML, '');
  assert.equal(elements['deep-link'].href, 'steellogic://part/training-part');
});

test('only an actual 404 is labelled unpublished', async () => {
  const missing = await resolvePart('/p/training-part', { status: 404 });
  assert.equal(missing.elements['part-status'].textContent, 'Part not published');
  assert.equal(missing.elements['unpublished-panel'].hidden, false);
  for (const response of [{ status: 500 }, new Error('offline'), { jsonError: new Error('bad JSON') }]) {
    const { elements } = await resolvePart('/p/training-part', response);
    assert.match(elements['part-status'].textContent, /lookup unavailable/);
    assert.equal(elements['unpublished-panel'].hidden, true);
    assert.equal(elements['deep-link'].href, 'steellogic://part/training-part');
  }
});

test('invalid published records never remain stuck resolving or display details', async () => {
  for (const payload of [null, {}, { ...record, schema: 'other' }, { ...record, piece_mark: {} }, { ...record, piece_mark: ' ' }]) {
    const { elements } = await resolvePart('/p/training-part', { payload });
    assert.match(elements['part-status'].textContent, /does not match/);
    assert.equal(elements['part-details'].hidden, true);
  }
});

test('published mirror text is escaped before rendering', async () => {
  const { elements } = await resolvePart('/p/training-part', {
    payload: { ...record, piece_mark: '<img src=x onerror="alert(1)">', profile_hint: 'A&B' }
  });
  assert.match(elements['part-details'].innerHTML, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/);
  assert.match(elements['part-details'].innerHTML, /A&amp;B/);
  assert.doesNotMatch(elements['part-details'].innerHTML, /<img/);
});
