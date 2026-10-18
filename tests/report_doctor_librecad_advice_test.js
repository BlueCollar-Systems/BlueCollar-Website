// Report Doctor must not send LibreCAD users to Labels or 3D Text for
// editable words: in LibreCAD, Labels and 3D Text requests come in as the
// same exact outlines as "Exact look" (DXF has no label entity and LibreCAD
// is 2D). Since importer v1.0.105 the LibreCAD window offers "Exact look"
// (the default) and "Editable text (LibreCAD font)" (LibreCAD README, "Two
// text choices in the window"), so that is the advice, unless the report
// says Editable text was already chosen. The LibreCAD window always uses
// Auto, so Raster/Hybrid are not window choices there. Advice for the other
// hosts stays as it was. The same cases also run without a browser in
// tests/report_doctor_parts_list_test.js.
// Runs report-doctor.html in a real headless browser (see browser_harness).
'use strict';

var harness = require('./browser_harness');

function report(host, textMode, result, extra) {
  var r = {
    schema: 'bcs.import_report/1.1',
    host: { app: host, version: '1.0.108' },
    result: Object.assign({ pages: 1, geometry: 120 }, result || {}),
    extra: Object.assign({ text_mode: textMode, requested_mode: 'auto', resolved_mode: 'vector' }, extra || {})
  };
  return r;
}

var EDITABLE = 'Editable text (LibreCAD font)';
var LIBRECAD_NEVER = [
  'Use Labels', 'Try Labels', 'compare against Labels mode', 'Labels for editable',
  'once your LibreCAD importer has it', 'Until that release', 'Raster/Hybrid',
  'maps to editable DXF TEXT'
];

var CASES = [
  {
    name: 'LibreCAD Exact look (glyphs)',
    report: report('LibreCAD', 'glyphs'),
    actionsMust: [EDITABLE, 'Exact look'],
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD Exact look (v1.0.108 records text)',
    report: report('LibreCAD', 'text'),
    actionsMust: [EDITABLE],
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD 3D Text',
    report: report('LibreCAD', '3d_text'),
    actionsMust: [EDITABLE],
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD labels',
    report: report('LibreCAD', 'labels', { glyphs: 40 }),
    actionsMust: [EDITABLE],
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD dense glyph page',
    report: report('LibreCAD', 'glyphs', { glyphs: 6000 }),
    actionsMust: [EDITABLE],
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD Editable text already chosen',
    report: report('LibreCAD', 'text', null, { editable_text: { chosen: true, item_count: 12 } }),
    findingsMust: ['12 text item(s) came in as editable text'],
    actionsMustNot: [EDITABLE],
    mustNot: LIBRECAD_NEVER
  },
  {
    // No LibreCAD install found: every word comes in as outlines, so the
    // count is 0 and gets its own reason and fix (LibreCAD README).
    name: 'LibreCAD Editable text chosen, 0 items',
    report: report('LibreCAD', 'text', null, { editable_text: { chosen: true, item_count: 0 } }),
    findingsMust: ['was chosen, but no text came in as editable text', "LibreCAD's font was not found", 'every word comes in as exact outlines'],
    findingsMustNot: ['0 text item(s)', 'letter shapes differ from the PDF'],
    actionsMust: ['Install LibreCAD', 'Locate LibreCAD...', '--librecad-exe', 'import the PDF again'],
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD Editable text chosen, 0 items as a string',
    report: report('LibreCAD', 'text', null, { editable_text: { chosen: true, item_count: '0' } }),
    findingsMust: ['was chosen, but no text came in as editable text'],
    findingsMustNot: ['0 text item(s)'],
    actionsMust: ['Locate LibreCAD...'],
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD Raster result',
    report: report('LibreCAD', 'glyphs', null, { resolved_mode: 'raster' }),
    actionsMust: ['--mode vector'],
    mustNot: LIBRECAD_NEVER.concat(['retry with Auto or Vector'])
  },
  {
    name: 'SketchUp glyphs (unchanged)',
    report: report('SketchUp', 'glyphs'),
    actionsMust: ['Use Labels or 3D Text if the downstream workflow needs editable text.'],
    mustNot: ['LibreCAD']
  },
  {
    name: 'SketchUp 3D Text (unchanged)',
    report: report('SketchUp', '3d_text'),
    actionsMust: ['compare against Labels mode'],
    mustNot: ['LibreCAD']
  },
  {
    name: 'FreeCAD dense glyph page (unchanged)',
    report: report('FreeCAD', 'glyphs', { glyphs: 6000 }),
    actionsMust: ['Try Labels for editable text'],
    mustNot: ['LibreCAD']
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
      (c.actionsMust || []).forEach(function(s) {
        check(actions.indexOf(s) !== -1, c.name + ': actions must mention "' + s + '"; got: ' + actions);
      });
      (c.findingsMust || []).forEach(function(s) {
        check(findings.indexOf(s) !== -1, c.name + ': findings must mention "' + s + '"; got: ' + findings);
      });
      (c.findingsMustNot || []).forEach(function(s) {
        check(findings.indexOf(s) === -1, c.name + ': findings must not say "' + s + '"; got: ' + findings);
      });
      (c.actionsMustNot || []).forEach(function(s) {
        check(actions.indexOf(s) === -1, c.name + ': actions must not say "' + s + '"');
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
