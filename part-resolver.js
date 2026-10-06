(function () {
  var m = location.pathname.match(/^\/p\/([^\/]+)\/?$/);
  var id = null;
  try {
    id = m ? decodeURIComponent(m[1]) : null;
  } catch (_) {
    // Damaged or manually entered URLs must still show useful feedback.
  }
  var idEl = document.getElementById('part-id');
  var link = document.getElementById('deep-link');
  var statusEl = document.getElementById('part-status');
  var detailsEl = document.getElementById('part-details');
  var unpublishedEl = document.getElementById('unpublished-panel');

  function setUnknown() {
    if (idEl) idEl.textContent = 'unknown';
    if (link) {
      link.href = 'steellogic://open';
      link.textContent = 'open the app';
    }
    if (statusEl) statusEl.textContent = 'Invalid or missing Part Tracking ID.';
  }

  function showUnpublished(partId) {
    if (statusEl) {
      statusEl.textContent = 'Part not published';
    }
    if (unpublishedEl) unpublishedEl.hidden = false;
    if (detailsEl) {
      detailsEl.hidden = true;
      detailsEl.innerHTML = '';
    }
    if (link) {
      link.href = 'steellogic://part/' + encodeURIComponent(partId);
    }
  }

  function showUnavailable(message) {
    if (statusEl) statusEl.textContent = message || 'Part lookup unavailable. Open the part in Steel Logic or try again.';
    if (unpublishedEl) unpublishedEl.hidden = true;
    if (detailsEl) {
      detailsEl.hidden = true;
      detailsEl.innerHTML = '';
    }
  }

  function showPublished(record) {
    if (unpublishedEl) unpublishedEl.hidden = true;
    if (statusEl) statusEl.textContent = 'Published part record';
    if (detailsEl) {
      detailsEl.hidden = false;
      var rows = [
        ['Piece mark', record.piece_mark],
        ['Profile', record.profile_hint],
        ['Quantity', record.quantity != null ? String(record.quantity) : null],
        ['Tag URL', record.tag_url]
      ];
      var html = '<dl class="part-dl">';
      for (var i = 0; i < rows.length; i++) {
        if (!rows[i][1]) continue;
        html += '<dt>' + escapeHtml(rows[i][0]) + '</dt><dd>' + escapeHtml(String(rows[i][1])) + '</dd>';
      }
      html += '</dl>';
      detailsEl.innerHTML = html;
    }
    if (link && record.part_id) {
      link.href = 'steellogic://part/' + encodeURIComponent(record.part_id);
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Keep the existing accepted alphabet for historical Steel Logic IDs.
  if (!id || !/^[\w .\-\/#]{1,64}$/.test(id)) {
    setUnknown();
    return;
  }

  if (idEl) idEl.textContent = id;
  if (link) link.href = 'steellogic://part/' + encodeURIComponent(id);
  document.title = 'Part Tracking ' + id + ' | BlueCollar-Systems';

  // Static JSON v1 (R5-6, moved R21-10): optional published mirror at
  // /p-records/<id>.json — outside /p/ so the /p/* rewrite cannot shadow it.
  fetch('/p-records/' + encodeURIComponent(id) + '.json', { cache: 'no-store' })
    .then(function (res) {
      if (res.status === 404) {
        showUnpublished(id);
        return undefined;
      }
      if (!res.ok) throw new Error('part fetch failed');
      return res.json();
    })
    .then(function (payload) {
      if (payload === undefined) return;
      if (payload && payload.schema === 'bcs.part/1.0' && payload.part_id === id &&
          typeof payload.piece_mark === 'string' && payload.piece_mark.trim()) {
        showPublished(payload);
      } else {
        showUnavailable('Part record does not match this tag. Open the part in Steel Logic.');
      }
    })
    .catch(function () {
      showUnavailable();
    });
})();
