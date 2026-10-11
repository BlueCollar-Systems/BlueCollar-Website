// Standards-browser regression for Report Doctor file pickers, adjacent
// feedback privacy guidance and the phone menu. This launches an
// already-installed Chromium browser; it does not emulate DOM, File,
// DataTransfer, or FileReader APIs. Browser lookup (Chrome first on Windows),
// page loading and temp-folder cleanup are shared with the other
// real-browser tests through tests/browser_harness.js.
'use strict';

var fs = require('fs');
var path = require('path');
var harness = require('./browser_harness');

var ROOT = harness.ROOT;
var localizeAssets = harness.localizeAssets;
var injectTest = harness.injectTest;
var runBrowserPage = harness.runBrowserPage;

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

var browser = harness.findBrowser();
var NAV_TEST = String.raw`
(function() {
  var result = document.createElement('pre');
  result.id = 'browser-test-result';
  document.body.appendChild(result);
  document.addEventListener('DOMContentLoaded', function() {
    try {
      var button = document.getElementById('nav-toggle');
      var menu = document.getElementById('nav-menu');
      function check(condition, message) { if (!condition) throw new Error(message); }
      button.click();
      check(button.getAttribute('aria-expanded') === 'true', 'menu must open');
      check(!menu.classList.contains('hidden'), 'open menu must be visible');
      menu.querySelector('a[href="#toolkit"]').click();
      check(button.getAttribute('aria-expanded') === 'false', 'selecting a link must close the mobile menu');
      check(menu.classList.contains('hidden'), 'selected menu must be hidden');
      button.click();
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      check(menu.classList.contains('hidden'), 'Escape must close the menu');
      check(document.activeElement === button, 'Escape must return focus to the menu button');
      button.click();
      document.body.click();
      check(menu.classList.contains('hidden'), 'clicking outside must close the menu');
      result.dataset.status = 'pass';
      result.textContent = 'PASS mobile menu open, link selection, Escape and outside click';
    } catch (error) {
      result.dataset.status = 'fail';
      result.textContent = error.stack || error.message;
    }
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ bcsTest: true, status: result.dataset.status, text: result.textContent }, '*');
    }
  });
})();
`;
var tempRoot = harness.makeTempRoot('bcs-website-browser-test-');

try {
  var reportHtml = localizeAssets(
    fs.readFileSync(path.join(ROOT, 'report-doctor.html'), 'utf8')
  );
  runBrowserPage(browser, tempRoot, 'report-doctor', injectTest(reportHtml, REPORT_TEST));

  var feedbackHtml = localizeAssets(
    fs.readFileSync(path.join(ROOT, 'feedback.html'), 'utf8')
  );
  runBrowserPage(browser, tempRoot, 'feedback', injectTest(feedbackHtml, FEEDBACK_TEST));
  var indexHtml = localizeAssets(fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8'));
  // The menu button is a phone control (md:hidden): from 768 px up it is
  // hidden, so Escape cannot move focus back to it. Run the phone-menu checks
  // in a 390 x 844 viewport (the size main chose). The shared harness sets the
  // viewport with a frame, so it is exact on Windows too, where headless
  // browsers will not shrink their window below about 500 px.
  runBrowserPage(browser, tempRoot, 'navigation', injectTest(indexHtml, NAV_TEST), { width: 390, height: 844 });
} finally {
  harness.removeTempRoot(tempRoot);
}

console.log('PASS report_doctor_browser_test: native browser DOM, file-input behavior and mobile navigation');
