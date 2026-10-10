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
  // On a phone, tapping a menu link closes the menu so it does not cover
  // the section it jumps to. (On computers the menu always shows.)
  menu.addEventListener('click', function(e) {
    var link = e.target.closest && e.target.closest('a');
    if (!link || menu.classList.contains('hidden')) return;
    menu.classList.add('hidden');
    btn.setAttribute('aria-expanded', 'false');
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

  function primaryAssetRank(name) {
    if (!name || !isPrimaryPdfImporterAsset(name)) return 999;
    if (/-(Setup)_v\d+(?:\.\d+){2}\.exe$/i.test(name)) return 0;
    if (/^LibreCAD-PDF-Importer-Windows-Portable_v\d+(?:\.\d+){2}\.zip$/i.test(name)) return 1;
    if (/^LibreCAD-PDF-Importer_v\d+(?:\.\d+){2}\.zip$/i.test(name)) return 20;
    return 5;
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
    var bestPrimary = null;
    var bestRank = 999;
    for (var p = 0; p < assets.length; p++) {
      var primary = assets[p];
      if (!primary || !isPrimaryPdfImporterAsset(primary.name)) continue;
      var rank = primaryAssetRank(primary.name);
      if (rank < bestRank) {
        bestPrimary = primary;
        bestRank = rank;
      }
    }
    if (bestPrimary) return bestPrimary;
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

  function isWindowsPackage(name) {
    return /-Setup_v\d+(?:\.\d+){2}\.exe$/i.test(name) ||
      /-Windows-Portable_v\d+(?:\.\d+){2}\.zip$/i.test(name) ||
      /^Blender-PDF-Importer_v\d+(?:\.\d+){2}\.zip$/i.test(name) ||
      /^SketchUp-PDF-Importer_v\d+(?:\.\d+){2}\.rbz$/i.test(name);
  }

  // Under an importer's Download Latest button: file type, size, and
  // "Windows" for Windows-only packages, e.g. ".zip · 254 MB · Windows".
  // The static caption stays when the size is unknown.
  function showAssetInfo(repoKey, asset) {
    var size = Number(asset.size);
    if (!asset.name || !(size > 0)) return;
    var dot = asset.name.lastIndexOf('.');
    if (dot < 0) return;
    var text = asset.name.slice(dot).toLowerCase() + ' · ' +
      Math.max(1, Math.round(size / 1048576)) + ' MB';
    if (isWindowsPackage(asset.name)) text += ' · Windows';
    document.querySelectorAll('[data-repo-asset-info]').forEach(function(info) {
      if (info.getAttribute('data-repo-asset-info') === repoKey) info.textContent = text;
    });
  }

  // Under a shape pack's Download button: the SHA-256 to check the download.
  function showAssetDigest(asset) {
    var digest = typeof asset.digest === 'string' ? asset.digest : '';
    if (!asset.name || !/^sha256:[0-9a-f]{64}$/i.test(digest)) return;
    document.querySelectorAll('[data-asset-digest-for]').forEach(function(el) {
      if (el.getAttribute('data-asset-digest-for') === asset.name) {
        el.textContent = 'SHA-256: ' + digest.slice(7).toLowerCase();
      }
    });
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
          if (!preferredName) showAssetInfo(repoKey, asset);
          if (preferredName) showAssetDigest(asset);
        } else if (!preferredName && release.url) {
          el.href = release.url;
        }
      });
    })
    .catch(function() {
      // Metadata is progressive enhancement; keep static fallback content.
    });
});
