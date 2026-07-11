(function () {
  var m = location.pathname.match(/^\/p\/([^\/]+)\/?$/);
  var id = m ? decodeURIComponent(m[1]) : null;
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

  if (!id || !/^[\w .\-\/#]{1,64}$/.test(id)) {
    setUnknown();
    return;
  }

  if (idEl) idEl.textContent = id;
  if (link) link.href = 'steellogic://part/' + encodeURIComponent(id);
  document.title = 'Part Tracking ' + id + ' | BlueCollar Systems';

  // Static JSON v1 (R5-6): optional published mirror at /p/<id>.json
  fetch('/p/' + encodeURIComponent(id) + '.json', { cache: 'no-store' })
    .then(function (res) {
      if (res.status === 404) {
        showUnpublished(id);
        return null;
      }
      if (!res.ok) throw new Error('part fetch failed');
      return res.json();
    })
    .then(function (payload) {
      if (!payload) return;
      if (payload.schema === 'bcs.part/1.0' && payload.part_id && payload.piece_mark) {
        showPublished(payload);
      } else {
        showUnpublished(id);
      }
    })
    .catch(function () {
      showUnpublished(id);
    });
})();
