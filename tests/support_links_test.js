'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const root = path.join(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'support-links.js'), 'utf8');
const schema = 'bcs.support-links/1';
const koFi = 'https://ko-fi.com/test-profile';
const sponsors = 'https://github.com/sponsors/test-profile';

async function loadSupport(payload, response = {}) {
  const section = { hidden: true };
  const links = { children: [], appendChild(link) { this.children.push(link); } };
  const requests = [];
  const elements = { 'support-projects': section, 'support-links': links };
  const document = {
    getElementById: (id) => elements[id],
    createElement: (tag) => {
      assert.equal(tag, 'a');
      const element = {};
      Object.defineProperty(element, 'innerHTML', {
        set() { assert.fail('Support links must not parse HTML'); }
      });
      return element;
    }
  };
  vm.runInNewContext(script, {
    document,
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (response.networkError) throw new Error('offline');
      return {
        ok: response.ok ?? true,
        json: async () => {
          if (response.jsonError) throw new Error('invalid JSON');
          return payload;
        }
      };
    }
  });
  await new Promise((done) => setImmediate(done));
  return { section, links: links.children, requests };
}

test('blank configuration creates no controls and the homepage initially hides support links', async () => {
  const config = JSON.parse(fs.readFileSync(path.join(root, 'support-config.json'), 'utf8'));
  assert.equal(config.schema, schema);
  assert.equal(typeof config.ko_fi_url, 'string');
  assert.equal(typeof config.github_sponsors_url, 'string');
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /<section\b[^>]*id="support-projects"[^>]*\bhidden>/);
  assert.match(html, /<div id="support-links"[^>]*><\/div>/);
  assert.match(html, /<script src="\/support-links\.js"><\/script>/);
  const result = await loadSupport({ schema, ko_fi_url: '', github_sponsors_url: '' });
  assert.equal(result.section.hidden, true);
  assert.equal(result.links.length, 0);
  assert.equal(result.requests.length, 1);
  assert.equal(result.requests[0].url, '/support-config.json');
  assert.equal(result.requests[0].options.cache, 'no-store');
  assert.equal(result.requests[0].options.credentials, 'omit');
});

test('both configured profiles produce working, clearly named anchors', async () => {
  const { section, links } = await loadSupport({ schema, ko_fi_url: koFi, github_sponsors_url: sponsors });
  assert.equal(section.hidden, false);
  assert.equal(links.length, 2);
  assert.deepEqual(links.map((link) => [link.href, link.textContent]), [
    [koFi, 'Support on Ko-fi'], [sponsors, 'Support on GitHub Sponsors']
  ]);
});

test('each channel works independently without an empty counterpart', async () => {
  for (const [key, url, label] of [
    ['ko_fi_url', koFi, 'Support on Ko-fi'],
    ['github_sponsors_url', sponsors, 'Support on GitHub Sponsors']
  ]) {
    const { section, links } = await loadSupport({ schema, [key]: '  ' + url + '/  ' });
    assert.equal(section.hidden, false);
    assert.equal(links.length, 1);
    assert.equal(links[0].href, url + '/');
    assert.equal(links[0].textContent, label);
  }
});

test('invalid channels cannot hide or substitute for a valid other channel', async () => {
  const { section, links } = await loadSupport({
    schema, ko_fi_url: 'https://other.example/profile', github_sponsors_url: sponsors
  });
  assert.equal(section.hidden, false);
  assert.equal(links.length, 1);
  assert.equal(links[0].href, sponsors);
});

test('support URLs reject wrong providers, schemes, credentials, ports, extra paths and markup', async () => {
  const invalid = [
    '', ' ', '#', 'http://ko-fi.com/test-profile', 'javascript:alert(1)',
    'https://ko-fi.com.evil.example/test-profile', 'https://other.example/test-profile',
    'https://user:pass@ko-fi.com/test-profile', 'https://ko-fi.com:443/test-profile',
    'https://ko-fi.com/', 'https://ko-fi.com/test-profile/posts',
    'https://ko-fi.com/test-profile?redirect=https://other.example',
    'https://ko-fi.com/test-profile#donate', 'https://ko-fi.com/%74est-profile',
    'https://ko-fi.com/test-profile/<img src=x>', 'https://ko-fi.com\\@other.example/profile',
    'https://github.com/test-profile', 'https://github.com/sponsors/',
    'https://github.com/sponsors/-test-profile', 'https://github.com/sponsors/test_profile',
    'https://github.com/sponsors/test-profile/extra', 'https://github.com/sponsors/test-profile?x=1',
    'https://github.com.evil.example/sponsors/test-profile',
    'https://user@github.com/sponsors/test-profile',
    'https://github.com:443/sponsors/test-profile',
    null, false, 42, {}, []
  ];
  for (const value of invalid) {
    const { section, links } = await loadSupport({ schema, ko_fi_url: value, github_sponsors_url: value });
    assert.equal(section.hidden, true, String(value));
    assert.equal(links.length, 0, String(value));
  }
});

test('provider fields cannot be swapped', async () => {
  const { section, links } = await loadSupport({ schema, ko_fi_url: sponsors, github_sponsors_url: koFi });
  assert.equal(section.hidden, true);
  assert.equal(links.length, 0);
});

test('unsupported or malformed configuration leaves the section hidden', async () => {
  for (const config of [null, [], {}, 'bad', { schema: 'other', ko_fi_url: koFi }]) {
    const { section, links } = await loadSupport(config);
    assert.equal(section.hidden, true);
    assert.equal(links.length, 0);
  }
});

test('HTTP, JSON and network failures leave the section hidden', async () => {
  for (const response of [{ ok: false }, { jsonError: true }, { networkError: true }]) {
    const { section, links } = await loadSupport({ schema, ko_fi_url: koFi }, response);
    assert.equal(section.hidden, true);
    assert.equal(links.length, 0);
  }
});

test('pages without the optional support section do not request its configuration', () => {
  vm.runInNewContext(script, {
    document: { getElementById: () => null },
    fetch: () => assert.fail('No support section, no request')
  });
});
