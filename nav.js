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

(function() {
  var el = document.getElementById('copyright-year');
  if (el) el.textContent = new Date().getFullYear();
})();

(function() {
  function parseDate(value) {
    if (!value) return null;
    var d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function findZipAsset(assets, preferredName) {
    if (!Array.isArray(assets)) return null;
    if (preferredName) {
      for (var i = 0; i < assets.length; i++) {
        if (assets[i] && assets[i].name === preferredName) return assets[i];
      }
    }
    for (var j = 0; j < assets.length; j++) {
      var a = assets[j];
      if (a && typeof a.name === 'string' && a.name.toLowerCase().endsWith('.zip')) return a;
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

        var release = repo.latest_release;
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
        var release = repo.latest_release;
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
        if (!repo || !repo.latest_release) return;
        var asset = findZipAsset(repo.latest_release.assets, preferredName);
        if (asset && asset.url) {
          el.href = asset.url;
        } else if (repo.latest_release.url) {
          el.href = repo.latest_release.url;
        }
      });
    })
    .catch(function() {
      // Metadata is progressive enhancement; keep static fallback content.
    });
})();
