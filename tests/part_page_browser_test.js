// Real-browser regression for the Part Tracking page that tag links open
// (/p/<id>). The page must be dark with readable text, the piece-mark
// details must lay out as a two-column list (one column on phones), and
// nothing may push the page sideways. A CSP meta tag mirrors the live
// site's style-src rule, so an inline <style> block would be blocked here
// just as it is on bluecollar-systems.com.
'use strict';

var harness = require('./browser_harness');

var PART_TEST = String.raw`
(function() {
  __HELPERS__
  function wait(ms) { return new Promise(function(resolve) { setTimeout(resolve, ms); }); }
  function loaded() {
    return new Promise(function(resolve) {
      if (document.readyState === 'complete') return resolve();
      window.addEventListener('load', function() { resolve(); });
    });
  }

  bcsRun('p/index.html @' + innerWidth + 'x' + innerHeight, async function() {
    await loaded();
    await wait(100);
    var details = document.getElementById('part-details');
    details.innerHTML = '<dl class="part-dl"><dt>Piece mark</dt><dd>EX101</dd>' +
      '<dt>Profile</dt><dd>W10X22</dd><dt>Quantity</dt><dd>1</dd>' +
      '<dt>Tag URL</dt><dd>https://bluecollar-systems.com/p/EX101-0123456789abcdef0123456789abcdef</dd></dl>';
    details.hidden = false;
    var unpublished = document.getElementById('unpublished-panel');
    unpublished.hidden = false;
    await wait(50);

    var bodyBg = effectiveBackground(document.body);
    var bodyLum = luminance(bodyBg);
    check(bodyLum < 0.05, 'page background is light (luminance ' + bodyLum.toFixed(3) + '); text on it is unreadable');

    var dl = document.querySelector('.part-dl');
    check(getComputedStyle(dl).display === 'grid', '.part-dl display ' + getComputedStyle(dl).display + ', expected grid');
    var dd = dl.querySelector('dd');
    var dt = dl.querySelector('dt');
    var ddContrast = textContrast(dd);
    check(ddContrast >= 4.5, 'piece mark contrast ' + ddContrast.toFixed(2) + ' is below 4.5');
    var dtContrast = textContrast(dt);
    check(dtContrast >= 4.5, 'piece mark label contrast ' + dtContrast.toFixed(2) + ' is below 4.5');
    var h1 = document.querySelector('h1');
    var h1Contrast = textContrast(h1);
    check(h1Contrast >= 4.5, 'heading contrast ' + h1Contrast.toFixed(2) + ' is below 4.5');

    var panelText = unpublished.querySelector('p');
    var panelContrast = textContrast(panelText);
    check(panelContrast >= 4.5, '"Part not published" text contrast ' + panelContrast.toFixed(2) + ' is below 4.5');
    Array.from(document.querySelectorAll('main li')).forEach(function(li) {
      var c = textContrast(li);
      check(c >= 4.5, '"' + li.textContent.trim().slice(0, 30) + '" contrast ' + c.toFixed(2) + ' is below 4.5');
    });

    var ddRect = dd.getBoundingClientRect();
    var dtRect = dt.getBoundingClientRect();
    if (innerWidth >= 480) {
      check(Math.abs(ddRect.top - dtRect.top) < 2 && ddRect.left > dtRect.right,
        'piece mark must sit beside its label on wider screens');
    } else {
      check(ddRect.top >= dtRect.bottom - 1, 'piece mark must sit under its label on phones');
    }
    check(document.documentElement.scrollWidth <= innerWidth,
      'page scrolls sideways: scrollWidth ' + document.documentElement.scrollWidth + ' > ' + innerWidth);

    return 'dark page (luminance ' + bodyLum.toFixed(3) + '), piece mark ' + ddContrast.toFixed(1) +
      ':1, heading ' + h1Contrast.toFixed(1) + ':1, panel ' + panelContrast.toFixed(1) + ':1';
  });
})();
`;

function testSource() {
  return PART_TEST.replace('__HELPERS__', function() { return harness.PAGE_HELPERS; });
}

// Mirror the live CSP's style-src: stylesheets from the site only, no inline <style>.
function withStyleCsp(html) {
  return html.replace('<head>', '<head><meta http-equiv="Content-Security-Policy" content="style-src file:">');
}

var SIZES = [
  { width: 1280, height: 900 },
  { width: 375, height: 812 }
];

var browser = harness.findBrowser();
var tempRoot = harness.makeTempRoot('bcs-website-part-test-');
var failures = [];
var passes = [];

try {
  var html = withStyleCsp(harness.readPage('p/index.html'));
  SIZES.forEach(function(size) {
    try {
      passes.push(harness.runBrowserPage(browser, tempRoot, 'part-' + size.width, harness.injectTest(html, testSource()), size));
    } catch (error) {
      failures.push(error.message);
    }
  });
} finally {
  harness.removeTempRoot(tempRoot);
}

passes.forEach(function(line) { console.log(line); });
if (failures.length) {
  console.error(failures.join('\n\n'));
  console.error('FAIL part_page_browser_test: ' + failures.length + ' problem(s) found');
  process.exit(1);
}
console.log('PASS part_page_browser_test: Part Tracking page is dark and readable at 1280 and 375 px');
