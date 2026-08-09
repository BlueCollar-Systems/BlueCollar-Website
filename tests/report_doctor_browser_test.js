// Standards-browser regression for Report Doctor file pickers and adjacent
// feedback privacy guidance. This launches an already-installed Chromium
// browser; it does not emulate DOM, File, DataTransfer, or FileReader APIs.
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

function localizeAssets(html) {
  return html
    .replace('href="/styles.css"', 'href="' + localFileUrl('styles.css') + '"')
    .replace('src="/nav.js"', 'src="' + localFileUrl('nav.js') + '"')
    .replace('src="/report-doctor.js"', 'src="' + localFileUrl('report-doctor.js') + '"');
}

function injectTest(html, testSource) {
  assert.ok(html.includes('</body>'), 'test page must contain a closing body tag');
  return html.replace('</body>', '<script>' + testSource + '</script></body>');
}

function browserTestResult(output) {
  var match = output.match(
    /<pre id="browser-test-result" data-status="([^"]+)">([\s\S]*?)<\/pre>/
  );
  if (!match) return { status: 'missing', text: 'browser result element was not dumped' };
  return { status: match[1], text: match[2] };
}

function runBrowserPage(browser, tempRoot, name, html) {
  var pagePath = path.join(tempRoot, name + '.html');
  var profilePath = path.join(tempRoot, name + '-profile');
  fs.writeFileSync(pagePath, html, 'utf8');

  var result = childProcess.spawnSync(browser, [
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
    '--virtual-time-budget=3000',
    '--user-data-dir=' + profilePath,
    '--dump-dom',
    pathToFileURL(pagePath).href
  ], {
    encoding: 'utf8',
    timeout: 30000,
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
}

var REPORT_TEST = String.raw`
(function() {
  var result = document.createElement('pre');
  result.id = 'browser-test-result';
  result.dataset.status = 'running';
  document.body.appendChild(result);

  function check(condition, message) {
    if (!condition) throw new Error(message);
  }

  function selectFile(input, fileName, contents) {
    var transfer = new DataTransfer();
    transfer.items.add(new File([contents], fileName, { type: 'application/json' }));
    input.files = transfer.files;
    check(input.files.length === 1, '#' + input.id + ' must expose one selected file');
    check(input.files[0] instanceof File, '#' + input.id + ' must expose a real File');
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function waitForValue(input, expected) {
    return new Promise(function(resolve, reject) {
      var attempts = 0;
      function poll() {
        if (input.value === expected) return resolve();
        attempts += 1;
        if (attempts >= 100) return reject(new Error('#' + input.id + ' was not populated by FileReader'));
        setTimeout(poll, 10);
      }
      poll();
    });
  }

  Promise.resolve().then(async function() {
    var reportFile = document.getElementById('report-file');
    var bootstrapFile = document.getElementById('bootstrap-file');
    var reportJson = document.getElementById('report-json');
    var bootstrapJson = document.getElementById('bootstrap-json');
    var pickers = [reportFile, bootstrapFile];

    pickers.forEach(function(input) {
      check(input instanceof HTMLInputElement, '#' + input.id + ' must be a real HTMLInputElement');
      check(input.type === 'file', '#' + input.id + ' must remain a file input');
      check(input.labels.length === 1, '#' + input.id + ' must have exactly one associated label');
      check(input.labels[0].control === input, '#' + input.id + ' label must control that exact picker');
      check(document.querySelectorAll('[id="' + input.id + '"]').length === 1, '#' + input.id + ' must be unique');
    });

    var reportContents = 'deliberately invalid report JSON';
    reportJson.value = 'report sentinel';
    bootstrapJson.value = 'bootstrap sentinel';
    selectFile(reportFile, 'import_report.json', reportContents);
    await waitForValue(reportJson, reportContents);
    check(bootstrapJson.value === 'bootstrap sentinel', 'report picker must not update bootstrap JSON');

    var bootstrapContents = '{"schema":"bcs.parts_bootstrap/1.0","rows":[]}';
    reportJson.value = 'report sentinel';
    bootstrapJson.value = 'bootstrap sentinel';
    selectFile(bootstrapFile, 'parts_bootstrap.json', bootstrapContents);
    await waitForValue(bootstrapJson, bootstrapContents);
    check(reportJson.value === 'report sentinel', 'bootstrap picker must not update report JSON');

    result.dataset.status = 'pass';
    result.textContent = 'PASS real label, File, input.files, change, and FileReader behavior';
  }).catch(function(error) {
    result.dataset.status = 'fail';
    result.textContent = error.stack || error.message || String(error);
  });
})();
`;

var FEEDBACK_TEST = String.raw`
(function() {
  var result = document.createElement('pre');
  result.id = 'browser-test-result';
  result.dataset.status = 'running';
  document.body.appendChild(result);

  try {
    var instruction = 'Do not send confidential or sensitive PDFs.';
    var sampleRequest = Array.from(document.querySelectorAll('p')).find(function(node) {
      return node.textContent.includes('PDF samples');
    });
    if (!sampleRequest) throw new Error('PDF sample request is missing');

    var adjacentWarning = sampleRequest.nextElementSibling;
    if (!adjacentWarning || adjacentWarning.textContent.trim() !== 'Privacy: ' + instruction) {
      throw new Error('PDF sample request must be followed by the unqualified confidential-or-sensitive warning');
    }

    var checklistItem = Array.from(document.querySelectorAll('li')).find(function(node) {
      return node.textContent.includes('For importer bugs:');
    });
    if (!checklistItem || !checklistItem.textContent.trim().endsWith(instruction)) {
      throw new Error('Importer checklist must repeat the unqualified confidential-or-sensitive warning');
    }

    result.dataset.status = 'pass';
    result.textContent = 'PASS rendered privacy guidance';
  } catch (error) {
    result.dataset.status = 'fail';
    result.textContent = error.stack || error.message || String(error);
  }
})();
`;

var browser = findBrowser();
var tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'bcs-website-browser-test-'));

try {
  var reportHtml = localizeAssets(
    fs.readFileSync(path.join(ROOT, 'report-doctor.html'), 'utf8')
  );
  runBrowserPage(browser, tempRoot, 'report-doctor', injectTest(reportHtml, REPORT_TEST));

  var feedbackHtml = localizeAssets(
    fs.readFileSync(path.join(ROOT, 'feedback.html'), 'utf8')
  );
  runBrowserPage(browser, tempRoot, 'feedback', injectTest(feedbackHtml, FEEDBACK_TEST));
} finally {
  fs.rmSync(tempRoot, { recursive: true, force: true });
}

console.log('PASS report_doctor_browser_test: native browser DOM and file-input behavior');
