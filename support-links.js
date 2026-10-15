/* Optional public support links. Blank or invalid settings show no controls. */
(function () {
  'use strict';

  var section = document.getElementById('support-projects');
  var links = document.getElementById('support-links');
  if (!section || !links) return;

  var channels = [
    {
      key: 'ko_fi_url',
      label: 'Support on Ko-fi',
      profile: /^https:\/\/ko-fi\.com\/[A-Za-z0-9_-]+\/?$/i
    },
    {
      key: 'github_sponsors_url',
      label: 'Support on GitHub Sponsors',
      profile: /^https:\/\/github\.com\/sponsors\/[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\/?$/i
    }
  ];

  function render(config) {
    if (!config || config.schema !== 'bcs.support-links/1') return;
    channels.forEach(function (channel) {
      var value = config[channel.key];
      if (typeof value !== 'string') return;
      value = value.trim();
      // Accept only a direct HTTPS profile on the expected provider. Config
      // cannot add credentials, other hosts, query strings or markup.
      if (!channel.profile.test(value)) return;
      var link = document.createElement('a');
      link.href = value;
      link.textContent = channel.label;
      link.className = 'inline-block bg-blue-700 hover:bg-blue-600 px-5 py-3 rounded font-semibold transition text-sm';
      links.appendChild(link);
    });
    section.hidden = links.children.length === 0;
  }

  fetch('/support-config.json', { cache: 'no-store', credentials: 'omit' })
    .then(function (response) {
      if (!response.ok) throw new Error('Support configuration unavailable');
      return response.json();
    })
    .then(render)
    .catch(function () { /* Optional support links remain hidden. */ });
})();
