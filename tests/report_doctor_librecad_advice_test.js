// Report Doctor must not send LibreCAD users to Labels or 3D Text for
// editable words: measured LibreCAD output for Labels and 3D Text is the
// same outline geometry as Glyphs, with no visible DXF TEXT. Editable words
// in LibreCAD need the new "Editable text (LibreCAD font)" choice. Advice
// for the other hosts stays as it was.
// Runs report-doctor.html in a real headless browser (see browser_harness).
'use strict';

var harness = require('./browser_harness');

function report(host, textMode, result) {
  var r = {
    schema: 'bcs.import_report/1.1',
    host: { app: host, version: '1.0.0' },
    result: Object.assign({ pages: 1, geometry: 120 }, result || {}),
    extra: { text_mode: textMode, requested_mode: 'auto', resolved_mode: 'vector' }
  };
  return r;
}

var CASES = [
  {
    name: 'LibreCAD glyphs',
    report: report('LibreCAD', 'glyphs'),
    actionsMust: ['Editable text (LibreCAD font)'],
    mustNot: ['Use Labels or 3D Text']
  },
  {
    name: 'LibreCAD 3D Text',
    report: report('LibreCAD', '3d_text'),
    actionsMust: ['Editable text (LibreCAD font)'],
    mustNot: ['maps to editable DXF TEXT', 'Use Labels for editable DXF text']
  },
  {
    name: 'LibreCAD labels',
    report: report('LibreCAD', 'labels'),
    actionsMust: ['Editable text (LibreCAD font)'],
    mustNot: []
  },
  {
    name: 'LibreCAD dense glyph page',
    report: report('LibreCAD', 'glyphs', { glyphs: 6000 }),
    actionsMust: ['Editable text (LibreCAD font)'],
    mustNot: ['Try Labels for editable text', 'Use Labels or 3D Text']
  },
  {
    name: 'SketchUp glyphs (unchanged)',
    report: report('SketchUp', 'glyphs'),
    actionsMust: ['Use Labels or 3D Text if the downstream workflow needs editable text.'],
    mustNot: ['LibreCAD font']
  },
  {
    name: 'FreeCAD dense glyph page (unchanged)',
    report: report('FreeCAD', 'glyphs', { glyphs: 6000 }),
    actionsMust: ['Try Labels for editable text'],
    mustNot: ['LibreCAD font']
  }
];

var DOCTOR_TEST = String.raw`
(function() {
  __HELPERS__
  var CASES = __CASES__;
  function wait(ms) { return new Promise(function(resolve) { setTimeout(resolve, ms); }); }
  bcsRun('Report Doctor LibreCAD advice', async function() {
    await wait(50);
    var input = document.getElementById('report-json');
    var button = document.getElementById('analyze-report');
    var notes = [];
    for (var i = 0; i < CASES.length; i++) {
      var c = CASES[i];
      input.value = JSON.stringify(c.report);
      button.click();
      await wait(50);
      var actions = document.getElementById('doctor-actions').textContent;
      var findings = document.getElementById('doctor-findings').textContent;
      check(actions.length > 0, c.name + ': Report Doctor gave no actions (error: ' + document.getElementById('doctor-error').textContent + ')');
      c.actionsMust.forEach(function(s) {
        check(actions.indexOf(s) !== -1, c.name + ': actions must mention "' + s + '"; got: ' + actions);
      });
      c.mustNot.forEach(function(s) {
        check((actions + findings).indexOf(s) === -1, c.name + ': must not say "' + s + '"');
      });
      notes.push(c.name);
    }
    return notes.join('; ');
  });
})();
`;

var source = DOCTOR_TEST
  .replace('__HELPERS__', function() { return harness.PAGE_HELPERS; })
  .replace('__CASES__', function() { return JSON.stringify(CASES).replace(/</g, '\\u003c'); });

var browser = harness.findBrowser();
var tempRoot = harness.makeTempRoot('bcs-website-doctor-advice-test-');
var failure = null;
var line = '';
try {
  line = harness.runBrowserPage(browser, tempRoot, 'report-doctor-advice',
    harness.injectTest(harness.readPage('report-doctor.html'), source));
} catch (error) {
  failure = error;
} finally {
  harness.removeTempRoot(tempRoot);
}

if (failure) {
  console.error(failure.message);
  console.error('FAIL report_doctor_librecad_advice_test');
  process.exit(1);
}
console.log(line);
console.log('PASS report_doctor_librecad_advice_test');
