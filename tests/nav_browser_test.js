// Real-browser regression for the top menu on every page that has one.
// Computers and tablets (768 px and wider) must show every menu link on one
// line with no sideways scroll; phones (375 px) get a 44 px menu button that
// opens a vertical list of 44 px rows, closes after a tap or Escape, and
// in-page jumps land below the sticky top bar.
'use strict';

var fs = require('fs');
var path = require('path');
var harness = require('./browser_harness');

var PAGES = ['index.html', 'shapes.html', 'feedback.html', 'report-doctor.html', 'privacy.html', 'terms.html'];

var NAV_TEST = String.raw`
(function() {
  __HELPERS__
  var CONFIG = __CONFIG__;

  function visible(el) {
    return getComputedStyle(el).display !== 'none';
  }
  function px(value, fallback) {
    var n = parseFloat(value);
    return Number.isFinite(n) ? n : fallback;
  }
  function wait(ms) {
    return new Promise(function(resolve) { setTimeout(resolve, ms); });
  }

  bcsRun(CONFIG.page + ' @' + innerWidth + 'x' + innerHeight, async function() {
    document.documentElement.style.scrollBehavior = 'auto';
    await wait(50);
    check(innerWidth === CONFIG.width, 'viewport width ' + innerWidth + ' is not ' + CONFIG.width);
    var menu = document.getElementById('nav-menu');
    var toggle = document.getElementById('nav-toggle');
    var nav = document.querySelector('nav');
    check(menu && toggle && nav, 'page must have nav, #nav-menu and #nav-toggle');
    var links = Array.from(menu.querySelectorAll('a'));
    check(links.length >= 7, 'menu must have at least 7 links, found ' + links.length);
    var notes = [];

    if (CONFIG.width >= 768) {
      var menuDisplay = getComputedStyle(menu).display;
      check(menuDisplay === 'flex', '#nav-menu display ' + menuDisplay + ' at ' + innerWidth + ' px (menu links are hidden on computers)');
      check(!visible(toggle), '#nav-toggle must be hidden at ' + innerWidth + ' px');
      links.forEach(function(a) {
        var r = a.getBoundingClientRect();
        var cs = getComputedStyle(a);
        var lineHeight = px(cs.lineHeight, px(cs.fontSize, 14) * 1.2);
        check(r.width > 0 && r.height > 0, 'menu link "' + a.textContent.trim() + '" is not shown');
        check(r.height < lineHeight * 2, 'menu link "' + a.textContent.trim() + '" breaks onto two lines (' + r.height + ' px tall)');
        check(r.right <= innerWidth + 0.5, 'menu link "' + a.textContent.trim() + '" runs off the right edge');
      });
      check(document.documentElement.scrollWidth <= innerWidth,
        'page scrolls sideways: scrollWidth ' + document.documentElement.scrollWidth + ' > ' + innerWidth);
      notes.push(links.length + ' links shown');

      if (CONFIG.contrast) {
        // Text people must read in bright shop light: the orange Android Beta
        // button, the grey version/help lines and the footer version line.
        var targets = [];
        document.querySelectorAll('.btn-safety').forEach(function(el) { targets.push(['Android Beta button', el]); });
        document.querySelectorAll('.text-gray-500').forEach(function(el) { targets.push(['grey line "' + el.textContent.trim().slice(0, 40) + '"', el]); });
        document.querySelectorAll('.footer-version').forEach(function(el) { targets.push(['footer version', el]); });
        check(targets.length >= 3, 'contrast check found only ' + targets.length + ' elements');
        var worst = 99;
        targets.forEach(function(target) {
          var ratio = textContrast(target[1]);
          worst = Math.min(worst, ratio);
          check(ratio >= 4.5, target[0] + ' contrast ' + ratio.toFixed(2) + ':1 is below 4.5:1');
        });
        notes.push('contrast >= 4.5 on ' + targets.length + ' elements (lowest ' + worst.toFixed(2) + ':1)');
      }

      if (CONFIG.clickToolkit) {
        var deskLink = menu.querySelector('a[href="#toolkit"]');
        check(deskLink, 'index menu must link to #toolkit');
        deskLink.click();
        await wait(100);
        check(getComputedStyle(menu).display === 'flex', 'menu must stay shown on a computer after clicking Toolkit');
        notes.push('menu stays after Toolkit click');
      }
      return notes.join('; ');
    }

    // Phone width.
    check(getComputedStyle(menu).display === 'none', 'phone menu must start closed');
    check(visible(toggle), 'phone menu button must be shown');
    var tr = toggle.getBoundingClientRect();
    check(tr.width >= 44 && tr.height >= 44, 'menu button is ' + tr.width + 'x' + tr.height + ', needs 44x44');
    var tbg = parseRgba(getComputedStyle(toggle).backgroundColor);
    check(tbg && tbg.a === 0, 'menu button background must be transparent, got ' + getComputedStyle(toggle).backgroundColor);
    check(document.documentElement.scrollWidth <= innerWidth,
      'page scrolls sideways: scrollWidth ' + document.documentElement.scrollWidth + ' > ' + innerWidth);

    toggle.click();
    await wait(50);
    check(getComputedStyle(menu).display === 'flex', 'open phone menu display ' + getComputedStyle(menu).display + ', expected flex');
    check(toggle.getAttribute('aria-expanded') === 'true', 'open menu must set aria-expanded true');
    var tops = {};
    links.forEach(function(a) {
      var top = Math.round(a.getBoundingClientRect().top);
      check(!tops[top], 'menu links "' + tops[top] + '" and "' + a.textContent.trim() + '" share one line');
      tops[top] = a.textContent.trim();
      check(a.offsetHeight >= 44, 'menu link "' + a.textContent.trim() + '" is ' + a.offsetHeight + ' px tall, needs 44');
    });
    var mr = menu.getBoundingClientRect();
    check(mr.bottom <= innerHeight + 0.5 || menu.scrollHeight > menu.clientHeight,
      'open menu runs past the bottom of the screen without scrolling');
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await wait(20);
    check(menu.classList.contains('hidden'), 'Escape must close the phone menu');
    check(toggle.getAttribute('aria-expanded') === 'false', 'Escape must set aria-expanded false');
    notes.push('vertical 44 px rows, Escape closes');

    if (CONFIG.jumps) {
      var navBottom = function() { return nav.getBoundingClientRect().bottom; };
      toggle.click();
      await wait(50);
      var toolkitLink = menu.querySelector('a[href="#toolkit"]');
      check(toolkitLink, 'index menu must link to #toolkit');
      toolkitLink.click();
      await wait(150);
      check(menu.classList.contains('hidden'), 'tapping Toolkit must close the phone menu');
      check(toggle.getAttribute('aria-expanded') === 'false', 'tapping Toolkit must set aria-expanded false');
      var heading = document.querySelector('#toolkit h2');
      check(heading.getBoundingClientRect().top >= navBottom() - 0.5,
        'Toolkit heading top ' + heading.getBoundingClientRect().top + ' is hidden under the top bar (bottom ' + navBottom() + ')');

      window.scrollTo(0, 0);
      await wait(50);
      var betaLink = document.querySelector('a[href="#android-beta"]');
      check(betaLink, 'index must link to #android-beta');
      betaLink.click();
      await wait(150);
      var beta = document.getElementById('android-beta');
      check(beta.getBoundingClientRect().top >= navBottom() - 0.5,
        'Android Beta box top ' + beta.getBoundingClientRect().top + ' is hidden under the top bar (bottom ' + navBottom() + ')');
      notes.push('Toolkit and Android Beta land below the bar');
    }
    return notes.join('; ');
  });
})();
`;

function testSource(config) {
  return NAV_TEST
    .replace('__HELPERS__', function() { return harness.PAGE_HELPERS; })
    .replace('__CONFIG__', function() { return JSON.stringify(config); });
}

var SIZES = [
  { width: 1280, height: 900 },
  { width: 768, height: 1024 },
  { width: 375, height: 812 }
];

var browser = harness.findBrowser();
var tempRoot = harness.makeTempRoot('bcs-website-nav-test-');
var failures = [];
var passes = [];

// (e) Keyboard users must see where focus is on the menu button and links.
var css = fs.readFileSync(path.join(harness.ROOT, 'styles.css'), 'utf8');
if (!css.includes('#nav-toggle:focus-visible')) {
  failures.push('styles.css must give #nav-toggle a :focus-visible outline');
}

try {
  PAGES.forEach(function(page) {
    var html = harness.readPage(page);
    SIZES.forEach(function(size) {
      var config = {
        page: page,
        width: size.width,
        clickToolkit: page === 'index.html' && size.width === 1280,
        contrast: page === 'index.html' && size.width === 1280,
        jumps: page === 'index.html' && size.width < 768
      };
      var name = page.replace('.html', '') + '-' + size.width;
      try {
        passes.push(harness.runBrowserPage(browser, tempRoot, name, harness.injectTest(html, testSource(config)), size));
      } catch (error) {
        failures.push(error.message);
      }
    });
  });
} finally {
  harness.removeTempRoot(tempRoot);
}

passes.forEach(function(line) { console.log(line); });
if (failures.length) {
  console.error(failures.join('\n\n'));
  console.error('FAIL nav_browser_test: ' + failures.length + ' problem(s) found');
  process.exit(1);
}
console.log('PASS nav_browser_test: menu works at 1280, 768 and 375 px on ' + PAGES.length + ' pages');
