(function() {
  var fileInput = document.getElementById('report-file');
  var jsonInput = document.getElementById('report-json');
  var analyzeButton = document.getElementById('analyze-report');
  var sampleButton = document.getElementById('load-sample-report');
  var clearButton = document.getElementById('clear-report');
  var errorBox = document.getElementById('doctor-error');
  var output = document.getElementById('doctor-output');
  var title = document.getElementById('doctor-title');
  var status = document.getElementById('doctor-status');
  var metrics = document.getElementById('doctor-metrics');
  var findings = document.getElementById('doctor-findings');
  var actions = document.getElementById('doctor-actions');
  var support = document.getElementById('doctor-support');
  var copyButton = document.getElementById('copy-support');
  var emailLink = document.getElementById('email-support');

  if (!jsonInput || !analyzeButton) return;

  var SAMPLE_REPORT = {
    schema: 'bcs.import_report/1.1',
    app: { name: 'SketchUp PDF Importer', version: '3.7.60' },
    source: { file: 'sample-shop-drawing.pdf', pages: '1' },
    result: { pages: 1, geometry: 12544, text: 342, images: 0, layers: 4 },
    fallback: { used: false, reason: null },
    performance: { total_ms: 12800, phases: { open_pdf_ms: 120, pages_import_ms: 12400 } },
    extra: {
      mode: 'auto',
      resolved_mode: 'vector',
      import_text: true,
      text_mode: 'labels',
      actual_text_breakdown: { labels: 328, text3d: 0, outlines: 14 },
      actual_text_entity_types: { entity_type: 'labels', count: 328, font_rendered: true, native_label: 328, examples: ['W12X26', '1/4', 'BILL OF MATERIAL'] },
      text_renderers: [{ page: 1, renderer: 'Poppler SVG', mode: 'labels' }],
      import_quality: 'High'
    }
  };

  function clearNode(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function setError(message) {
    if (!errorBox) return;
    errorBox.textContent = message || '';
  }

  function safeText(value) {
    if (value === null || value === undefined || value === '') return 'Unknown';
    if (typeof value === 'number') return String(value);
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    return String(value);
  }

  function getPath(obj, path) {
    var current = obj;
    for (var i = 0; i < path.length; i++) {
      if (!current || typeof current !== 'object') return undefined;
      current = current[path[i]];
    }
    return current;
  }

  function firstValue(obj, paths) {
    for (var i = 0; i < paths.length; i++) {
      var value = getPath(obj, paths[i]);
      if (value !== undefined && value !== null && value !== '') return value;
    }
    return undefined;
  }

  function toNumber(value) {
    if (typeof value === 'number' && isFinite(value)) return value;
    if (typeof value === 'string' && value.trim() !== '') {
      var parsed = Number(value);
      if (isFinite(parsed)) return parsed;
    }
    return null;
  }

  function objectValue(obj, names) {
    if (!obj || typeof obj !== 'object') return undefined;
    for (var i = 0; i < names.length; i++) {
      var value = obj[names[i]];
      if (value !== undefined && value !== null && value !== '') return value;
    }
    return undefined;
  }

  function formatMs(value) {
    var n = toNumber(value);
    if (n === null) return 'Unknown';
    if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 1 : 2) + ' s';
    return Math.round(n) + ' ms';
  }

  function metric(label, value) {
    var card = document.createElement('div');
    card.className = 'doctor-metric bg-gray-800/50 border border-gray-700 rounded-xl';
    var small = document.createElement('p');
    small.className = 'text-xs text-gray-400 uppercase tracking-widest';
    small.textContent = label;
    var strong = document.createElement('p');
    strong.className = 'text-xl font-bold text-gray-100';
    strong.textContent = safeText(value);
    card.appendChild(small);
    card.appendChild(strong);
    metrics.appendChild(card);
  }

  function addListItem(list, text) {
    var li = document.createElement('li');
    li.textContent = text;
    list.appendChild(li);
  }

  function detectBuildStamp(report) {
    return firstValue(report, [
      ['report_meta', 'build_stamp'],
      ['extra', 'report_meta', 'build_stamp'],
      ['metadata', 'build_stamp']
    ]);
  }

  function detectHost(report) {
    var raw = firstValue(report, [
      ['app', 'name'],
      ['application', 'name'],
      ['tool'],
      ['host'],
      ['extra', 'host'],
      ['extra', 'target_app'],
      ['metadata', 'host']
    ]);
    var text = safeText(raw);
    var lower = text.toLowerCase();
    if (lower.indexOf('sketchup') >= 0) return 'SketchUp';
    if (lower.indexOf('freecad') >= 0) return 'FreeCAD';
    if (lower.indexOf('librecad') >= 0 || lower.indexOf('dxf') >= 0) return 'LibreCAD';
    if (lower.indexOf('blender') >= 0) return 'Blender';
    return text === 'Unknown' ? 'Unknown host' : text;
  }

  function detectVersion(report) {
    return firstValue(report, [
      ['app', 'version'],
      ['application', 'version'],
      ['version'],
      ['extra', 'version'],
      ['metadata', 'version']
    ]);
  }

  function detectTextMode(report) {
    return firstValue(report, [
      ['extra', 'text_mode'],
      ['text_mode'],
      ['options', 'text_mode'],
      ['config', 'text_mode']
    ]);
  }

  function detectRequestedMode(report) {
    return firstValue(report, [
      ['extra', 'requested_mode'],
      ['extra', 'import_mode'],
      ['extra', 'mode'],
      ['options', 'import_mode'],
      ['options', 'mode'],
      ['config', 'import_mode'],
      ['config', 'mode'],
      ['mode']
    ]);
  }

  function detectResolvedMode(report) {
    return firstValue(report, [
      ['extra', 'resolved_mode'],
      ['extra', 'auto_resolved_mode'],
      ['result', 'resolved_mode'],
      ['resolved_mode'],
      ['summary', 'resolved_mode']
    ]);
  }

  function detectTotalMs(report) {
    return firstValue(report, [
      ['performance', 'total_ms'],
      ['performance', 'phases', 'total_ms'],
      ['extra', 'total_ms']
    ]);
  }

  function resultNumber(report, keyNames) {
    for (var i = 0; i < keyNames.length; i++) {
      var key = keyNames[i];
      var value = firstValue(report, [
        ['result', key],
        ['summary', key],
        [key]
      ]);
      var number = toNumber(value);
      if (number !== null) return number;
    }
    return null;
  }

  function collectTextBreakdown(report) {
    var actual = firstValue(report, [
      ['extra', 'actual_text_breakdown'],
      ['extra', 'text_breakdown'],
      ['result', 'text_breakdown'],
      ['summary', 'text_breakdown'],
      ['text_breakdown']
    ]);
    var breakdown = {
      labels: resultNumber(report, ['labels', 'text_labels', 'editable_text']),
      text3d: resultNumber(report, ['text3d', 'text_3d', '3d_text']),
      outlines: resultNumber(report, ['glyphs', 'text_glyphs', 'outlines', 'text_geometry']),
      total: resultNumber(report, ['text', 'texts', 'text_items'])
    };
    if (actual && typeof actual === 'object') {
      if (breakdown.labels === null) breakdown.labels = toNumber(objectValue(actual, ['labels', 'text_labels', 'editable_text']));
      if (breakdown.text3d === null) breakdown.text3d = toNumber(objectValue(actual, ['text3d', 'text_3d', '3d_text']));
      if (breakdown.outlines === null) breakdown.outlines = toNumber(objectValue(actual, ['outlines', 'glyphs', 'text_glyphs', 'text_geometry']));
      if (breakdown.total === null) breakdown.total = toNumber(objectValue(actual, ['total', 'text', 'text_items']));
    }
    var extra = report.extra || {};
    if (typeof extra === 'object') {
      if (breakdown.outlines === null) breakdown.outlines = toNumber(extra.text_glyph_estimate);
      if (breakdown.total === null) breakdown.total = toNumber(extra.text_source_spans);
    }
    return breakdown;
  }

  function fallbackUsed(report) {
    var value = firstValue(report, [
      ['fallback', 'used'],
      ['extra', 'fallback_used'],
      ['fallback_used']
    ]);
    return value === true || value === 'true' || value === 1 || value === '1';
  }

  function fallbackReason(report) {
    return firstValue(report, [
      ['fallback', 'reason'],
      ['extra', 'fallback_reason'],
      ['fallback_reason']
    ]);
  }

  function rendererSummary(report) {
    var renderers = firstValue(report, [
      ['extra', 'text_renderers'],
      ['text_renderers']
    ]);
    if (!Array.isArray(renderers) || renderers.length === 0) return 'Unknown';
    var names = {};
    renderers.forEach(function(item) {
      if (!item || typeof item !== 'object') return;
      var name = item.renderer || item.engine || item.source || item.mode;
      if (name) names[String(name)] = true;
    });
    var keys = Object.keys(names);
    return keys.length ? keys.join(', ') : String(renderers.length) + ' renderer entries';
  }

  function normalizeModeName(value) {
    var mode = String(value || '').toLowerCase().replace(/[\s-]+/g, '_');
    if (mode === '3dtext' || mode === 'text_3d') return '3d_text';
    if (mode === 'outline' || mode === 'outlines') return 'glyphs';
    return mode;
  }

  function collectEntityVerification(report) {
    var raw = firstValue(report, [
      ['extra', 'actual_text_entity_types'],
      ['extra', 'text_entity_verification'],
      ['actual_text_entity_types']
    ]);
    if (!raw || typeof raw !== 'object') return null;
    var requested = null;
    var observed = raw;
    if (raw.observed && typeof raw.observed === 'object') {
      observed = raw.observed;
      requested = raw.requested || null;
    }
    if (observed.entity_type !== undefined) {
      // Backward-compatible TextEntityVerification shape:
      // { entity_type, count, font_rendered, examples, native_label?, ... }
      var single = {};
      single[normalizeModeName(observed.entity_type)] = toNumber(observed.count) || 0;
      var observedKeys = Object.keys(observed);
      for (var oi = 0; oi < observedKeys.length; oi++) {
        var key = observedKeys[oi];
        if (key === 'count' || key === 'font_rendered' || key === 'examples' || key === 'entity_type') continue;
        var observedCount = toNumber(observed[key]);
        if (observedCount !== null) single[key] = observedCount;
      }
      return {
        requested: requested,
        counts: single,
        fontRendered: observed.font_rendered === true,
        examples: Array.isArray(observed.examples) ? observed.examples : []
      };
    }
    // Schema map shape: { native_label: n, outline_curve_or_mesh: n, ... }
    var counts = {};
    var keys = Object.keys(observed);
    for (var i = 0; i < keys.length; i++) {
      var n = toNumber(observed[keys[i]]);
      if (n !== null) counts[keys[i]] = n;
    }
    if (!Object.keys(counts).length) return null;
    return { requested: requested, counts: counts, fontRendered: null, examples: [] };
  }

  var MODE_ENTITY_KEYS = {
    labels: ['label', 'labels', 'native_label', 'dxf_text'],
    '3d_text': ['3d_text', 'native_3d_text'],
    glyphs: ['glyphs', 'outline_curve_or_mesh', 'outlines'],
    geometry: ['geometry', 'raw_geometry_edges', 'fallback_geometry']
  };

  function verificationMatchesMode(verification, mode) {
    var wanted = MODE_ENTITY_KEYS[mode];
    if (!wanted) return null;
    var matched = 0;
    var total = 0;
    var keys = Object.keys(verification.counts);
    for (var i = 0; i < keys.length; i++) {
      var count = verification.counts[keys[i]];
      total += count;
      if (wanted.indexOf(keys[i]) >= 0) matched += count;
    }
    if (total === 0) return null;
    return { matched: matched, total: total, clean: matched === total };
  }

  function isReadyCheck(report) {
    return String((report && report.schema) || '').indexOf('bcs.ready_check/') === 0;
  }

  function analyzeReadyCheck(report) {
    clearNode(metrics);
    clearNode(findings);
    clearNode(actions);
    var checks = Array.isArray(report.checks) ? report.checks : [];
    var counts = { pass: 0, warn: 0, fail: 0, skip: 0 };
    checks.forEach(function(check) {
      var state = String((check && check.status) || '').toLowerCase();
      if (counts[state] !== undefined) counts[state]++;
    });
    metric('Product', report.product);
    metric('Version', report.version);
    metric('Host', getPath(report, ['host', 'name']));
    metric('Status', report.status);
    metric('Checks passed', counts.pass + '/' + checks.length);
    if (counts.warn) metric('Warnings', counts.warn);
    if (counts.fail) metric('Failures', counts.fail);
    checks.forEach(function(check) {
      if (!check || check.status === 'pass') return;
      addListItem(findings, '[' + String(check.status).toUpperCase() + '] ' + safeText(check.id) + ': ' + safeText(check.message));
    });
    if (!findings.childNodes.length) addListItem(findings, 'All ready checks passed.');
    var hints = Array.isArray(report.repair_hints) ? report.repair_hints : [];
    hints.forEach(function(hint) {
      if (hint) addListItem(actions, safeText(hint.summary) + ' — ' + safeText(hint.action));
    });
    if (!actions.childNodes.length) addListItem(actions, 'No repair actions needed. Attach this Ready Check to human confirmation test runs.');
    var level = report.status === 'pass' ? 'ok' : (report.status === 'warn' ? 'warn' : 'risk');
    setStatus(level, report.status === 'pass' ? 'Ready' : (report.status === 'warn' ? 'Review' : 'Not Ready'));
    title.textContent = 'Ready Check — ' + safeText(report.product);
    var lines = [
      'BlueCollar Ready Check Summary',
      'Product: ' + safeText(report.product),
      'Version: ' + safeText(report.version),
      'Host: ' + safeText(getPath(report, ['host', 'name'])),
      'Status: ' + safeText(report.status),
      'Checks: ' + counts.pass + ' pass / ' + counts.warn + ' warn / ' + counts.fail + ' fail / ' + counts.skip + ' skip'
    ];
    support.textContent = lines.join('\n');
    emailLink.href = 'mailto:support@bluecollar-systems.com?subject=' +
      encodeURIComponent('Ready Check review') +
      '&body=' + encodeURIComponent(support.textContent);
    output.classList.remove('hidden');
  }

  function setStatus(level, label) {
    status.className = 'doctor-pill doctor-pill-' + level;
    status.textContent = label;
  }

  function analyze(report) {
    if (isReadyCheck(report)) {
      analyzeReadyCheck(report);
      return;
    }
    var host = detectHost(report);
    var version = detectVersion(report);
    var buildStamp = detectBuildStamp(report);
    var requestedMode = detectRequestedMode(report);
    var resolvedMode = detectResolvedMode(report);
    var textMode = detectTextMode(report);
    var pages = resultNumber(report, ['pages', 'page_count']);
    var geometry = resultNumber(report, ['geometry', 'entities', 'primitives', 'edges']);
    var images = resultNumber(report, ['images', 'image_count']);
    var layers = resultNumber(report, ['layers', 'layer_count']);
    var totalMs = detectTotalMs(report);
    var text = collectTextBreakdown(report);
    var usedFallback = fallbackUsed(report);
    var reason = fallbackReason(report);
    var renderer = rendererSummary(report);
    var normalizedTextMode = normalizeModeName(textMode);

    clearNode(metrics);
    clearNode(findings);
    clearNode(actions);

    metric('Host', host);
    metric('Version', version);
    if (buildStamp) metric('Build stamp', buildStamp);
    metric('Requested mode', requestedMode);
    metric('Resolved mode', resolvedMode || requestedMode);
    metric('Text mode', textMode);
    metric('Pages', pages);
    metric('Geometry', geometry);
    metric('Text items', text.total);
    if (text.labels !== null) metric('Labels', text.labels);
    if (text.text3d !== null) metric('3D text', text.text3d);
    if (text.outlines !== null) metric('Text outlines', text.outlines);
    metric('Images', images);
    metric('Layers', layers);
    metric('Time', formatMs(totalMs));

    var severity = 'ok';
    var heading = 'Import Looks Healthy';

    if (usedFallback) {
      severity = 'warn';
      heading = 'Fallback Was Used';
      addListItem(findings, 'The importer reported a fallback: ' + safeText(reason) + '.');
      addListItem(actions, 'Review the affected page visually. Fallbacks are often correct for scans or image-heavy drawings, but they reduce editability.');
    } else {
      addListItem(findings, 'No fallback was reported.');
    }

    if (String(resolvedMode || requestedMode || '').toLowerCase().indexOf('raster') >= 0) {
      severity = usedFallback ? 'risk' : 'warn';
      heading = 'Raster Output Needs Review';
      addListItem(findings, 'The resolved strategy appears to be Raster. Text and linework may be image pixels instead of editable CAD entities.');
      addListItem(actions, 'If the source PDF is vector-based, retry with Auto or Vector and check whether the report still resolves to Raster.');
    }

    if (normalizedTextMode === 'geometry' || normalizedTextMode === 'glyphs') {
      addListItem(findings, 'Text was requested as visual geometry/outlines, not editable labels.');
      addListItem(actions, 'Use Labels or 3D Text if the downstream workflow needs editable text.');
    } else if (normalizedTextMode === 'labels') {
      addListItem(findings, 'Text was requested as editable labels where the host can support it.');
      if (text.outlines !== null && text.outlines > 0) {
        severity = severity === 'ok' ? 'warn' : severity;
        addListItem(findings, 'Some text appears to have landed as outlines/glyph geometry even though Labels mode was requested.');
        addListItem(actions, 'Compare the affected text against the PDF. Rotated, warped, clipped, or font-dependent spans may need outlines for visual accuracy.');
      }
    } else if (normalizedTextMode === '3d_text' || normalizedTextMode === 'text3d') {
      addListItem(findings, 'Text was requested as 3D/extruded text where the host can support it.');
      if (text.labels !== null && text.labels > 0) {
        addListItem(findings, 'The report shows editable labels alongside 3D text. This can happen when a host preserves simple text differently from complex spans.');
      }
      addListItem(actions, 'If table text or dimensions look misaligned, compare against Labels mode on the same page.');
    } else if (textMode === undefined) {
      addListItem(findings, 'No text mode was recorded. This may be an older report or a host adapter gap.');
      addListItem(actions, 'Update to the latest importer and include the full import report if you contact support.');
    }

    if (text.outlines !== null && text.outlines > 5000) {
      severity = severity === 'ok' ? 'warn' : severity;
      addListItem(findings, 'The report suggests a large amount of text/glyph geometry. Dense glyph pages can be slow and hard to edit.');
      addListItem(actions, 'Try Labels for editable text, or Raster/Hybrid when exact appearance matters more than editability.');
    }

    if (geometry !== null && geometry > 100000) {
      severity = 'warn';
      addListItem(findings, 'Very high geometry count detected. Older PCs may slow down during import or viewport navigation.');
      addListItem(actions, 'Import fewer pages at a time and check whether hatches/text outlines are driving the geometry count.');
    }

    if (layers !== null && layers === 0) {
      addListItem(findings, 'No layer/tag/group count was recorded.');
      addListItem(actions, 'If the PDF has layers, enable layer matching or use the latest importer so layer telemetry is captured.');
    }

    if (renderer !== 'Unknown') {
      addListItem(findings, 'Text renderer evidence: ' + renderer + '.');
    }

    var verification = collectEntityVerification(report);
    var verificationParts = [];
    if (verification) {
      var typeKeys = Object.keys(verification.counts);
      for (var vi = 0; vi < typeKeys.length; vi++) {
        verificationParts.push(typeKeys[vi] + ': ' + verification.counts[typeKeys[vi]]);
      }
      metric('Verified text entities', verificationParts.join(', '));
      var match = verificationMatchesMode(verification, normalizeModeName(verification.requested || textMode));
      if (match === null) {
        addListItem(findings, 'Host reported actual text entity types: ' + verificationParts.join(', ') + '.');
      } else if (match.clean) {
        addListItem(findings, 'Verified: actual text entities match the requested ' + safeText(verification.requested || textMode) + ' mode (' + verificationParts.join(', ') + ').');
      } else {
        severity = severity === 'ok' ? 'warn' : severity;
        addListItem(findings, 'Text entity mismatch: requested ' + safeText(verification.requested || textMode) + ' but the host reports ' + verificationParts.join(', ') + '.');
        addListItem(actions, 'Compare the mismatched text against the PDF, and attach this report to any support request so the mismatch is machine-readable.');
      }
      if (verification.examples.length) {
        addListItem(findings, 'Verified entity examples: ' + verification.examples.slice(0, 3).join(' | '));
      }
    }

    var perfHint = firstValue(report, [['extra', 'performance_hint']]);
    if (perfHint) {
      addListItem(findings, 'Importer performance hint: ' + safeText(perfHint));
    }

    if (String(host).toLowerCase().indexOf('librecad') >= 0 && normalizedTextMode === '3d_text') {
      addListItem(findings, 'LibreCAD is 2D-only; 3D Text maps to editable DXF TEXT rather than true 3D geometry.');
      addListItem(actions, 'Use Labels for editable DXF text or Outlines/Geometry for visual linework.');
    }

    if (!actions.childNodes.length) {
      addListItem(actions, 'Spot-check scale, layers, text placement, and a few known dimensions against the source PDF.');
      addListItem(actions, 'If the visual result is wrong, retry the same page with a different text mode and include this report with screenshots.');
    }

    if (buildStamp) {
      addListItem(findings, 'Import build stamp: ' + safeText(buildStamp) + '.');
    }

    if (severity === 'ok') setStatus('ok', 'Healthy');
    if (severity === 'warn') setStatus('warn', 'Review');
    if (severity === 'risk') setStatus('risk', 'High Review');
    title.textContent = buildStamp ? (heading + ' — ' + buildStamp) : heading;

    var supportLines = [
      'BlueCollar Import Report Summary',
      'Host: ' + safeText(host),
      'Version: ' + safeText(version),
      'Build stamp: ' + safeText(buildStamp),
      'Requested mode: ' + safeText(requestedMode),
      'Resolved mode: ' + safeText(resolvedMode || requestedMode),
      'Text mode: ' + safeText(textMode),
      'Pages: ' + safeText(pages),
      'Geometry: ' + safeText(geometry),
      'Text items: ' + safeText(text.total),
      'Labels: ' + safeText(text.labels),
      '3D text: ' + safeText(text.text3d),
      'Text outlines/glyphs: ' + safeText(text.outlines),
      'Images: ' + safeText(images),
      'Layers: ' + safeText(layers),
      'Fallback: ' + (usedFallback ? 'Yes - ' + safeText(reason) : 'No'),
      'Text renderer: ' + renderer,
      'Verified text entities: ' + (verificationParts.length ? verificationParts.join(', ') : 'Not reported'),
      'Performance hint: ' + safeText(perfHint),
      'Total time: ' + formatMs(totalMs),
      '',
      'Notes:',
      '- Attach screenshots of the source PDF and imported result.',
      '- Do not send confidential PDFs unless you are comfortable sharing them.'
    ];
    support.textContent = supportLines.join('\n');
    emailLink.href = 'mailto:support@bluecollar-systems.com?subject=' +
      encodeURIComponent('PDF importer report review') +
      '&body=' + encodeURIComponent(support.textContent);
    output.classList.remove('hidden');
  }

  function parseAndAnalyze() {
    setError('');
    var text = jsonInput.value.trim();
    if (!text) {
      setError('Paste report JSON or choose a report file first.');
      return;
    }
    try {
      analyze(JSON.parse(text));
    } catch (err) {
      setError('Could not parse JSON: ' + err.message);
    }
  }

  if (fileInput) {
    fileInput.addEventListener('change', function() {
      var file = fileInput.files && fileInput.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function() {
        jsonInput.value = String(reader.result || '');
        parseAndAnalyze();
      };
      reader.onerror = function() {
        setError('Could not read the selected file.');
      };
      reader.readAsText(file);
    });
  }

  analyzeButton.addEventListener('click', parseAndAnalyze);

  if (sampleButton) {
    sampleButton.addEventListener('click', function() {
      jsonInput.value = JSON.stringify(SAMPLE_REPORT, null, 2);
      parseAndAnalyze();
    });
  }

  if (clearButton) {
    clearButton.addEventListener('click', function() {
      jsonInput.value = '';
      if (fileInput) fileInput.value = '';
      setError('');
      if (output) output.classList.add('hidden');
    });
  }

  if (copyButton) {
    copyButton.addEventListener('click', function() {
      var text = support ? support.textContent : '';
      if (!text) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function() {
          copyButton.textContent = 'Copied';
          setTimeout(function() { copyButton.textContent = 'Copy Summary'; }, 1600);
        }).catch(function() {
          setError('Copy failed. Select the support summary text and copy it manually.');
        });
      } else {
        setError('Clipboard API unavailable. Select the support summary text and copy it manually.');
      }
    });
  }
})();
