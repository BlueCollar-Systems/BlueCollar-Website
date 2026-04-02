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
})();
