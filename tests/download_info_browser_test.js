// Real-browser regression for the download captions and checksums that
// nav.js fills from /repo-metadata.json:
// - home page: each importer's Download Latest button shows file type and
//   size (and "Windows" for Windows packages), and still links to the
//   release asset;
// - Free Shapes: each shape pack shows its SHA-256 under Download ZIP, and
//   SHA256SUMS.txt links to the release file;
// - without sizes in the metadata the static captions stay in place.
// fetch is stubbed with this checkout's repo-metadata.json; expected values
// are computed from that file so the test keeps working as releases change.
'use strict';

var fs = require('fs');
var path = require('path');
var harness = require('./browser_harness');

var metadata = JSON.parse(fs.readFileSync(path.join(harness.ROOT, 'repo-metadata.json'), 'utf8'));
var IMPORTERS = ['SketchUp', 'FreeCAD', 'Blender', 'LibreCAD'];

function releaseAssets(repoKey, channel) {
  var repo = metadata.repos[repoKey] || {};
  var release = channel === 'steel' ? repo.steel_release : repo.latest_release;
  return (release && release.assets) || [];
}

function primaryAsset(host) {
  var assets = releaseAssets('BlueCollar-Systems/PDF-Importer-' + host);
  var ranked = assets.filter(function(a) {
    return /^(SketchUp|FreeCAD|LibreCAD|Blender)-PDF-Importer(-Setup|-Windows-Portable)?_v\d+(\.\d+){2}\.(rbz|zip|exe)$/i.test(a.name);
  }).sort(function(a, b) { return rank(a.name) - rank(b.name); });
  if (!ranked.length) throw new Error('repo-metadata.json has no primary ' + host + ' asset');
  return ranked[0];
}

function rank(name) {
  if (/-Setup_v/i.test(name)) return 0;
  if (/-Windows-Portable_v/i.test(name)) return 1;
  if (/^LibreCAD-PDF-Importer_v/i.test(name)) return 20;
  return 5;
}

var expectedIndex = IMPORTERS.map(function(host) {
  var asset = primaryAsset(host);
  return {
    repo: 'BlueCollar-Systems/PDF-Importer-' + host,
    host: host,
    url: asset.url,
    ext: asset.name.slice(asset.name.lastIndexOf('.')).toLowerCase(),
    mb: Math.max(1, Math.round(asset.size / 1048576)) + ' MB'
  };
});

var expectedShapes = [
  ['BlueCollar-Systems/PDF-Importer-SketchUp', 'Structural-Steel-SU-Shapes-latest.zip'],
  ['BlueCollar-Systems/PDF-Importer-FreeCAD', 'Structural-Steel-DXF-DWG-Shapes-latest.zip']
].map(function(pair) {
  var assets = releaseAssets(pair[0], 'steel');
  var zip = assets.find(function(a) { return a.name === pair[1]; });
  var sums = assets.find(function(a) { return a.name === 'SHA256SUMS.txt'; });
  if (!zip || !/^sha256:[0-9a-f]{64}$/.test(zip.digest)) throw new Error('repo-metadata.json has no digest for ' + pair[1]);
  return { repo: pair[0], name: pair[1], digest: zip.digest.slice(7), zipUrl: zip.url, sumsUrl: sums ? sums.url : null };
});

function stubFetch(payload) {
  var json = JSON.stringify(payload).replace(/</g, '\\u003c');
  return 'window.fetch = function(url) {' +
    ' if (String(url).indexOf("repo-metadata.json") === -1) return Promise.reject(new Error("unexpected fetch " + url));' +
    ' var body = ' + json + ';' +
    ' return Promise.resolve({ ok: true, status: 200, json: function() { return Promise.resolve(body); } });' +
    '};';
}

var INDEX_TEST = String.raw`
(function() {
  __HELPERS__
  var EXPECT = __EXPECT__;
  function wait(ms) { return new Promise(function(resolve) { setTimeout(resolve, ms); }); }
  bcsRun('index.html download captions' + (EXPECT.noSizes ? ' (no sizes)' : ''), async function() {
    await wait(300);
    var notes = [];
    EXPECT.importers.forEach(function(e) {
      var info = document.querySelectorAll('[data-repo-asset-info="' + e.repo + '"]');
      check(info.length === 1, e.host + ' must have one download caption');
      var text = info[0].textContent.trim();
      var link = document.querySelector('a[data-repo-asset-link="' + e.repo + '"]:not([data-asset-name])');
      check(link && link.href === e.url, e.host + ' Download Latest must link to ' + e.url + ', got ' + (link && link.href));
      if (EXPECT.noSizes) {
        check(text === 'Windows package', e.host + ' caption must keep its static text without sizes, got "' + text + '"');
      } else {
        check(text.indexOf(e.ext) === 0, e.host + ' caption "' + text + '" must start with ' + e.ext);
        check(text.indexOf(e.mb) !== -1, e.host + ' caption "' + text + '" must show ' + e.mb);
        check(text.indexOf('Windows') !== -1, e.host + ' caption "' + text + '" must say Windows');
      }
      notes.push(e.host + ': ' + text);
    });
    return notes.join('; ');
  });
})();
`;

var SHAPES_TEST = String.raw`
(function() {
  __HELPERS__
  var EXPECT = __EXPECT__;
  function wait(ms) { return new Promise(function(resolve) { setTimeout(resolve, ms); }); }
  bcsRun('shapes.html checksums', async function() {
    await wait(300);
    var notes = [];
    EXPECT.shapes.forEach(function(e) {
      var el = document.querySelector('[data-asset-digest-for="' + e.name + '"]');
      check(el, e.name + ' must have a checksum line under its Download button');
      var shown = (el.textContent.match(/[0-9a-f]{64}/) || [])[0];
      check(shown === e.digest, e.name + ' shows "' + el.textContent.trim() + '", expected ' + e.digest);
      var zip = document.querySelector('a[data-asset-name="' + e.name + '"]');
      check(zip && zip.href === e.zipUrl, e.name + ' Download ZIP must link to ' + e.zipUrl);
      if (e.sumsUrl) {
        var sums = document.querySelector('a[data-repo-asset-link="' + e.repo + '"][data-asset-name="SHA256SUMS.txt"]');
        check(sums && sums.href === e.sumsUrl, 'SHA256SUMS.txt for ' + e.name + ' must link to ' + e.sumsUrl + ', got ' + (sums && sums.href));
      }
      check(el.getBoundingClientRect().right <= innerWidth + 0.5, e.name + ' checksum runs off the screen');
      notes.push(e.name + ' ' + shown.slice(0, 8) + '...');
    });
    check(document.documentElement.scrollWidth <= innerWidth, 'page scrolls sideways at ' + innerWidth + ' px');
    check(document.querySelector('main').innerText.indexOf('listed above') === -1, 'page must not mention a checksum "listed above"');
    return notes.join('; ');
  });
})();
`;

function source(template, expect) {
  return template
    .replace('__HELPERS__', function() { return harness.PAGE_HELPERS; })
    .replace('__EXPECT__', function() { return JSON.stringify(expect); });
}

function withoutSizes(payload) {
  var copy = JSON.parse(JSON.stringify(payload));
  Object.keys(copy.repos).forEach(function(key) {
    ['latest_release', 'steel_release'].forEach(function(channel) {
      var release = copy.repos[key][channel];
      if (release && release.assets) release.assets.forEach(function(a) { delete a.size; });
    });
  });
  return copy;
}

var browser = harness.findBrowser();
var tempRoot = harness.makeTempRoot('bcs-website-download-test-');
var failures = [];
var passes = [];

function run(name, page, template, expect, payload, size) {
  try {
    var html = harness.readPage(page);
    html = harness.injectTest(html, stubFetch(payload) + source(template, expect));
    passes.push(harness.runBrowserPage(browser, tempRoot, name, html, size));
  } catch (error) {
    failures.push(error.message);
  }
}

try {
  run('index-downloads', 'index.html', INDEX_TEST, { importers: expectedIndex }, metadata, { width: 1280, height: 900 });
  run('index-downloads-nosize', 'index.html', INDEX_TEST, { importers: expectedIndex, noSizes: true }, withoutSizes(metadata), { width: 1280, height: 900 });
  run('shapes-checksums', 'shapes.html', SHAPES_TEST, { shapes: expectedShapes }, metadata, { width: 1280, height: 900 });
  run('shapes-checksums-phone', 'shapes.html', SHAPES_TEST, { shapes: expectedShapes }, metadata, { width: 375, height: 812 });
} finally {
  harness.removeTempRoot(tempRoot);
}

passes.forEach(function(line) { console.log(line); });
if (failures.length) {
  console.error(failures.join('\n\n'));
  console.error('FAIL download_info_browser_test: ' + failures.length + ' problem(s) found');
  process.exit(1);
}
console.log('PASS download_info_browser_test: captions, links and checksums match repo-metadata.json');
