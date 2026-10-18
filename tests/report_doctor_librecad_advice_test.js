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
// --librecad-exe exists only on lcpdf-import, which has no Editable text
// option; pdf2dxf.py (the command line with --editable-text) rejects it.
var LIBRECAD_NEVER = [
  'Use Labels', 'Try Labels', 'compare against Labels mode', 'Labels for editable',
  'once your LibreCAD importer has it', 'Until that release', 'Raster/Hybrid',
  'maps to editable DXF TEXT', '--librecad-exe'
];

// Per-word delivery records shaped like the ones LibreCAD importer main
// e4f089b wrote for pdf2dxf.py --editable-text on a fictional 2-line PDF with
// embedded Arial (TrueType): the native Text attempt is refused and the word
// comes in as Glyphs. Evidence values and reasons are the measured ones.
var NOT_FOUND = 'no resolved LibreCAD executable is available to bind the unicode.lff asset';
var NO_CFF_PEN = 'native text has no source-bound positive CFF pen: source has no usable CFF dominant-stem metric';
var NO_ROMANS = 'native Romans has no safe linear layout';
function nativeTextRecords(evidence, reasons) {
  return {
    text_representation_delivery: {
      requested_representation: 'text',
      items: reasons.map(function(reason, i) {
        return {
          source_id: 'text_span:1:' + (i + 1), requested_representation: 'text', final_representation: 'glyphs',
          attempts: [
            { attempted_representation: 'text', strategy: 'native_dxf_text', outcome: 'impossible',
              reason: '_RepresentationImpossible: ' + reason, evidence: evidence },
            { attempted_representation: 'glyphs', strategy: 'entity_text2path', outcome: 'verified', reason: '', evidence: {} }
          ]
        };
      })
    }
  };
}
function zeroEditable(records, count) {
  return Object.assign({ editable_text: { chosen: true, item_count: count === undefined ? 0 : count } }, records || {});
}
// LibreCAD installed and found: the font is verified, another check failed.
var FONT_FOUND = nativeTextRecords({
  librecad_lff_asset_verified: true, librecad_parent_installation_verified: true,
  librecad_lff_resolution_reason: 'verified LibreCAD Font 1 romans.lff asset'
}, [NO_CFF_PEN, NO_ROMANS]);
// BCS_LIBRECAD_EXECUTABLE pointed at a missing file: no LibreCAD, no font.
var FONT_NOT_FOUND = nativeTextRecords({
  librecad_lff_asset_verified: false, librecad_parent_installation_verified: false,
  librecad_lff_resolution_reason: NOT_FOUND
}, [NOT_FOUND, NOT_FOUND]);
var INSTALL_ADVICE = ['Install LibreCAD', 'Locate LibreCAD...'];

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
    // 0 editable words gets its own message. With no LibreCAD found the
    // report says so per item, and only then is install/locate the advice;
    // pdf2dxf.py users set BCS_LIBRECAD_EXECUTABLE (LibreCAD INSTALL.md).
    name: 'LibreCAD Editable text chosen, 0 items, LibreCAD not found',
    report: report('LibreCAD', 'text', null, zeroEditable(FONT_NOT_FOUND)),
    findingsMust: ['was chosen, but no text came in as editable text', 'LibreCAD was not found', "LibreCAD's font was not found", 'every word comes in as exact outlines'],
    findingsMustNot: ['0 text item(s)', 'letter shapes differ from the PDF'],
    actionsMust: INSTALL_ADVICE.concat(['pdf2dxf.py', 'BCS_LIBRECAD_EXECUTABLE', 'full path of LibreCAD.exe', 'import the PDF again']),
    mustNot: LIBRECAD_NEVER
  },
  {
    // Only the reason text (no installation field) and a string count.
    name: 'LibreCAD Editable text chosen, 0 items as a string, not-found reason only',
    report: report('LibreCAD', 'text', null, zeroEditable(nativeTextRecords({ librecad_lff_asset_verified: false }, [NOT_FOUND]), '0')),
    findingsMust: ['was chosen, but no text came in as editable text', 'LibreCAD was not found'],
    findingsMustNot: ['0 text item(s)'],
    actionsMust: INSTALL_ADVICE.concat(['BCS_LIBRECAD_EXECUTABLE']),
    mustNot: LIBRECAD_NEVER
  },
  {
    // Measured: LibreCAD installed and found, embedded Arial, 0 of 2 words.
    // The cause is the per-item check, not a missing font, and the
    // "Locate LibreCAD..." button is not on screen.
    name: 'LibreCAD Editable text chosen, 0 items, LibreCAD found',
    report: report('LibreCAD', 'text', null, zeroEditable(FONT_FOUND)),
    findingsMust: ['was chosen, but no text came in as editable text', "LibreCAD's font was found", NO_CFF_PEN, NO_ROMANS],
    findingsMustNot: ['0 text item(s)', 'letter shapes differ from the PDF', 'not found', 'likely reason', '_RepresentationImpossible'],
    actionsMust: ['ordinary TrueType', 'CID-keyed CFF', 'symbol font', 'R12', 'reason for each word'],
    actionsMustNot: INSTALL_ADVICE.concat(['BCS_LIBRECAD_EXECUTABLE']),
    mustNot: LIBRECAD_NEVER
  },
  {
    name: 'LibreCAD Editable text chosen, 0 items, LibreCAD found but its font unusable',
    report: report('LibreCAD', 'text', null, zeroEditable(nativeTextRecords({
      librecad_lff_asset_verified: false, librecad_parent_installation_verified: true
    }, ['file is not a parseable LibreCAD Font 1 asset']))),
    findingsMust: ['LibreCAD was found, but its font could not be used', 'file is not a parseable LibreCAD Font 1 asset'],
    findingsMustNot: ['not found'],
    actionsMust: ['Repair or reinstall LibreCAD', 'import the PDF again'],
    actionsMustNot: INSTALL_ADVICE,
    mustNot: LIBRECAD_NEVER
  },
  {
    // No per-item records: the cause is unknown, so no "likely reason";
    // both causes are named, the not-found one only as a condition.
    name: 'LibreCAD Editable text chosen, 0 items, no per-item records',
    report: report('LibreCAD', 'text', null, zeroEditable()),
    findingsMust: ['was chosen, but no text came in as editable text', 'does not record why'],
    findingsMustNot: ['0 text item(s)', 'not found', 'likely reason'],
    actionsMust: ['If the importer said LibreCAD was not found', 'Locate LibreCAD...', 'BCS_LIBRECAD_EXECUTABLE', 'ordinary TrueType'],
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
