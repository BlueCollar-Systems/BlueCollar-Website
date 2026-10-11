// Shared harness for the website's real-browser regressions. It launches an
// already-installed Chromium browser (Chrome, Chromium or Edge) headless,
// loads a local copy of a page with the site's own CSS and JS, runs an
// injected test script, and reads the result from the dumped DOM.
// Same approach as tests/report_doctor_browser_test.js, plus a window size.
'use strict';

var assert = require('assert');
var childProcess = require('child_process');
var fs = require('fs');
var os = require('os');
var path = require('path');
var pathToFileURL = require('url').pathToFileURL;

var ROOT = path.resolve(__dirname, '..');

function findBrowser() {
  var candidates = [];
  if (process.env.BCS_TEST_BROWSER) candidates.push(process.env.BCS_TEST_BROWSER);

  if (process.platform === 'win32') {
    candidates.push(
      'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
      'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
    );
  } else if (process.platform === 'darwin') {
    candidates.push(
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'
    );
  } else {
    candidates.push(
      '/usr/bin/google-chrome',
      '/usr/bin/google-chrome-stable',
      '/usr/bin/chromium',
      '/usr/bin/chromium-browser'
    );
  }

  for (var i = 0; i < candidates.length; i++) {
    if (candidates[i] && fs.existsSync(candidates[i])) return candidates[i];
  }

  throw new Error(
    'No supported Chromium browser found. Set BCS_TEST_BROWSER to an existing Chrome, Chromium, or Edge executable.'
  );
}

function localFileUrl(name) {
  return pathToFileURL(path.join(ROOT, name)).href;
}

// Point the page's root-relative assets at the files in this checkout.
function localizeAssets(html) {
  return html
    .split('href="/styles.css"').join('href="' + localFileUrl('styles.css') + '"')
    .split('href="/part-page.css"').join('href="' + localFileUrl('part-page.css') + '"')
    .split('src="/nav.js"').join('src="' + localFileUrl('nav.js') + '"')
    .split('src="/report-doctor.js"').join('src="' + localFileUrl('report-doctor.js') + '"')
    .split('src="/part-resolver.js"').join('src="' + localFileUrl('part-resolver.js') + '"');
}

function readPage(name) {
  return localizeAssets(fs.readFileSync(path.join(ROOT, name), 'utf8'));
}

// Insert the test script just before </body>, after the page's own scripts.
function injectTest(html, testSource) {
  assert.ok(html.includes('</body>'), 'test page must contain a closing body tag');
  return html.replace('</body>', '<script>' + testSource + '</script></body>');
}

// Insert a script at the top of <head>, before any of the page's scripts run.
function injectEarly(html, source) {
  assert.ok(html.includes('<head>'), 'test page must contain a head tag');
  return html.replace('<head>', '<head><script>' + source + '</script>');
}

function browserTestResult(output) {
  var match = output.match(
    /<pre id="browser-test-result" data-status="([^"]+)">([\s\S]*?)<\/pre>/
  );
  if (!match) return { status: 'missing', text: 'browser result element was not dumped' };
  return { status: match[1], text: match[2] };
}

function makeTempRoot(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix || 'bcs-website-browser-test-'));
}

// The browser can hold files in its profile for a moment after it exits;
// on Windows a plain recursive delete then fails with ENOTEMPTY or EBUSY.
function removeTempRoot(tempRoot) {
  try {
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  } catch (error) {
    console.warn('warning: could not remove temp folder ' + tempRoot + ': ' + error.message);
  }
}

// Headless Chromium cannot shrink its window below about 500 px and adds a
// frame on Windows, so the viewport is set with an iframe instead: the page
// runs in a frame of exactly opts.width x opts.height CSS pixels, and its
// injected test posts the result up to the wrapper, which is what gets dumped.
function framedWrapper(pageFileName, width, height) {
  return '<!DOCTYPE html><html><head><meta charset="utf-8"><title>frame</title></head>' +
    '<body style="margin:0">' +
    '<pre id="browser-test-result" data-status="missing">the framed page sent no result</pre>' +
    '<iframe src="' + pageFileName + '" style="border:0;display:block;width:' + width +
    'px;height:' + height + 'px"></iframe>' +
    '<script>addEventListener("message", function(e) {' +
    ' if (!e.data || !e.data.bcsTest) return;' +
    ' var r = document.getElementById("browser-test-result");' +
    ' r.dataset.status = e.data.status; r.textContent = e.data.text; });</script>' +
    '</body></html>';
}

// opts.width / opts.height run the page at that viewport size (see above).
function runBrowserPage(browser, tempRoot, name, html, opts) {
  opts = opts || {};
  var pagePath = path.join(tempRoot, name + '.html');
  var profilePath = path.join(tempRoot, name + '-profile');
  fs.writeFileSync(pagePath, html, 'utf8');
  var loadPath = pagePath;
  var framed = Boolean(opts.width && opts.height);
  if (framed) {
    loadPath = path.join(tempRoot, name + '-frame.html');
    fs.writeFileSync(loadPath, framedWrapper(path.basename(pagePath), opts.width, opts.height), 'utf8');
  }

  var args = [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-background-networking',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-sync',
    '--metrics-recording-only',
    '--no-first-run',
    '--safebrowsing-disable-auto-update',
    '--allow-file-access-from-files',
    '--hide-scrollbars',
    '--force-device-scale-factor=1',
    // Edge on Windows relaunches itself (de-elevation, compatibility layer)
    // when started from an administrator shell; the relaunched copy loses
    // stdout, so --dump-dom prints nothing. Chrome ignores both switches.
    '--disable-features=AutoDeElevate',
    '--edge-skip-compat-layer-relaunch',
    '--virtual-time-budget=' + (opts.virtualTimeBudget || 3000),
    '--user-data-dir=' + profilePath
  ];
  if (framed) args.push('--window-size=' + (opts.width + 64) + ',' + (opts.height + 200));
  args.push('--dump-dom', pathToFileURL(loadPath).href);

  var result = childProcess.spawnSync(browser, args, {
    encoding: 'utf8',
    timeout: 60000,
    windowsHide: true
  });

  assert.ifError(result.error);
  assert.strictEqual(
    result.status,
    0,
    name + ' browser process failed:\n' + String(result.stderr || result.stdout)
  );
  var browserResult = browserTestResult(result.stdout);
  assert.strictEqual(
    browserResult.status,
    'pass',
    name + ' browser assertions failed:\n' + browserResult.text
  );
  return browserResult.text;
}

// Helpers made available inside injected test scripts (as plain source).
var PAGE_HELPERS = String.raw`
  // Report the result in this page and, when framed, to the wrapper page.
  function bcsFinish(status, text) {
    var result = document.getElementById('browser-test-result');
    if (!result) {
      result = document.createElement('pre');
      result.id = 'browser-test-result';
      document.body.appendChild(result);
    }
    result.dataset.status = status;
    result.textContent = text;
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ bcsTest: true, status: status, text: String(text) }, '*');
    }
  }
  function bcsRun(name, body) {
    Promise.resolve().then(body).then(function(text) {
      bcsFinish('pass', 'PASS ' + name + (text ? ': ' + text : ''));
    }).catch(function(error) {
      bcsFinish('fail', name + ': ' + (error && (error.stack || error.message) || String(error)));
    });
  }
  function check(condition, message) {
    if (!condition) throw new Error(message);
  }
  function parseRgba(value) {
    var m = String(value).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    var parts = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  }
  function blend(top, bottom) {
    var a = top.a;
    return {
      r: top.r * a + bottom.r * (1 - a),
      g: top.g * a + bottom.g * (1 - a),
      b: top.b * a + bottom.b * (1 - a),
      a: 1
    };
  }
  // The colour actually painted behind an element: its own background
  // blended over every ancestor's, ending on the white browser canvas.
  function effectiveBackground(el) {
    var layers = [];
    for (var node = el; node && node.nodeType === 1; node = node.parentElement) {
      var c = parseRgba(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0) layers.push(c);
      if (c && c.a >= 1) break;
    }
    var color = { r: 255, g: 255, b: 255, a: 1 };
    for (var i = layers.length - 1; i >= 0; i--) color = blend(layers[i], color);
    return color;
  }
  function luminance(c) {
    var ch = [c.r, c.g, c.b].map(function(v) {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
  }
  function contrastRatio(a, b) {
    var la = luminance(a), lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }
  // Text colour (with its own alpha and any element opacity) against the
  // painted background behind it.
  function textContrast(el) {
    var bg = effectiveBackground(el);
    var fg = parseRgba(getComputedStyle(el).color);
    var opacity = 1;
    for (var node = el; node && node.nodeType === 1; node = node.parentElement) {
      opacity *= Number(getComputedStyle(node).opacity);
    }
    fg = blend({ r: fg.r, g: fg.g, b: fg.b, a: fg.a * opacity }, bg);
    return contrastRatio(fg, bg);
  }
  function nextFrame() {
    return new Promise(function(resolve) { setTimeout(resolve, 50); });
  }
`;

module.exports = {
  ROOT: ROOT,
  findBrowser: findBrowser,
  localizeAssets: localizeAssets,
  readPage: readPage,
  injectTest: injectTest,
  injectEarly: injectEarly,
  makeTempRoot: makeTempRoot,
  removeTempRoot: removeTempRoot,
  runBrowserPage: runBrowserPage,
  PAGE_HELPERS: PAGE_HELPERS
};
