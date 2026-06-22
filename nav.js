(function() {
  var btn = document.getElementById('nav-toggle');
  var menu = document.getElementById('nav-menu');
  if (!btn || !menu) return;
  btn.addEventListener('click', function() {
    menu.classList.toggle('hidden');
    var isNowOpen = !menu.classList.contains('hidden');
    btn.setAttribute('aria-expanded', String(isNowOpen));
    if (isNowOpen) { var first = menu.querySelector('a'); if (first) first.focus(); }
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && !menu.classList.contains('hidden')) {
      menu.classList.add('hidden');
      btn.setAttribute('aria-expanded', 'false');
      btn.focus();
    }
  });
  document.addEventListener('click', function(e) {
    if (!menu.classList.contains('hidden') &&
        !menu.contains(e.target) &&
        e.target !== btn &&
        !btn.contains(e.target)) {
      menu.classList.add('hidden');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
})();

document.addEventListener('DOMContentLoaded', function() {
  var el = document.getElementById('copyright-year');
  if (el) el.textContent = new Date().getFullYear();

  function parseDate(value) {
    if (!value) return null;
    var d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function isPrimaryPdfImporterAsset(name) {
    return /^(SketchUp|FreeCAD|LibreCAD|Blender)-PDF-Importer_v\d+(?:\.\d+){2}\.(rbz|zip)$/i.test(name) ||
      /^FreeCAD-PDF-Importer-Setup_v\d+(?:\.\d+){2}\.exe$/i.test(name) ||
      /^LibreCAD-PDF-Importer-Setup_v\d+(?:\.\d+){2}\.exe$/i.test(name) ||
      /^LibreCAD-PDF-Importer-Windows-Portable_v\d+(?:\.\d+){2}\.zip$/i.test(name);
  }

  function releaseFor(repo, channel) {
    if (!repo) return null;
    if (channel === 'steel') return repo.steel_release || null;
    return repo.latest_release || null;
  }

  function findDownloadAsset(assets, preferredName) {
    if (!Array.isArray(assets)) return null;
    if (preferredName) {
      for (var i = 0; i < assets.length; i++) {
        if (assets[i] && assets[i].name === preferredName) return assets[i];
      }
      return null;
    }
    for (var p = 0; p < assets.length; p++) {
      var primary = assets[p];
      if (primary && isPrimaryPdfImporterAsset(primary.name)) return primary;
    }
    var extensions = ['.rbz', '.zip', '.aab', '.apk'];
    for (var j = 0; j < assets.length; j++) {
      var a = assets[j];
      if (!a || typeof a.name !== 'string') continue;
      var lowerName = a.name.toLowerCase();
      for (var k = 0; k < extensions.length; k++) {
        if (lowerName.endsWith(extensions[k])) return a;
      }
    }
    return null;
  }

  fetch('/repo-metadata.json', { cache: 'no-store' })
    .then(function(res) {
      if (!res.ok) throw new Error('metadata fetch failed');
      return res.json();
    })
    .then(function(payload) {
      var repos = (payload && payload.repos) || {};

      document.querySelectorAll('[data-repo-version]').forEach(function(el) {
        var repoKey = el.getAttribute('data-repo-version');
        var repo = repos[repoKey];
        if (!repo) return;

        var release = releaseFor(repo, el.getAttribute('data-release-channel'));
        var isInlineBadge = el.tagName === 'SPAN';
        if (release && release.tag) {
          el.textContent = isInlineBadge ? release.tag : ('Latest: ' + release.tag);
          return;
        }

        var pushedAt = parseDate(repo.pushed_at);
        if (pushedAt) {
          var dateStr = pushedAt.toISOString().slice(0, 10);
          el.textContent = isInlineBadge ? dateStr : ('Updated: ' + dateStr);
        }
      });

      document.querySelectorAll('[data-repo-release-link]').forEach(function(el) {
        var repoKey = el.getAttribute('data-repo-release-link');
        var repo = repos[repoKey];
        if (!repo) return;
        var release = releaseFor(repo, el.getAttribute('data-release-channel'));
        if (release && release.url) {
          el.href = release.url;
        } else if (repo.repo_url) {
          el.href = repo.repo_url;
        }
      });

      document.querySelectorAll('[data-repo-asset-link]').forEach(function(el) {
        var repoKey = el.getAttribute('data-repo-asset-link');
        var preferredName = el.getAttribute('data-asset-name');
        var repo = repos[repoKey];
        var release = releaseFor(repo, el.getAttribute('data-release-channel'));
        if (!repo || !release) return;
        var asset = findDownloadAsset(release.assets, preferredName);
        if (asset && asset.url) {
          el.href = asset.url;
        } else if (!preferredName && release.url) {
          el.href = release.url;
        }
      });
    })
    .catch(function() {
      // Metadata is progressive enhancement; keep static fallback content.
    });
});
