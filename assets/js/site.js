// Keep Bootstrap's mobile dropdown dismissible without moving page content.
const menuPanel = document.querySelector('#primary-nav');
const menuToggle = document.querySelector('.navbar-toggler');
const navbar = document.querySelector('.site-navbar');

if (menuPanel && menuToggle && navbar && window.bootstrap) {
  const mobile = window.matchMedia('(max-width: 991.98px)');
  const collapse = bootstrap.Collapse.getOrCreateInstance(menuPanel, { toggle: false });
  let dismissWhenShown = false;

  const isMenuOpen = () => menuPanel.classList.contains('show') ||
    menuPanel.classList.contains('collapsing');

  const dismissMenu = (restoreFocus = false) => {
    if (!mobile.matches || !isMenuOpen()) return;
    // Bootstrap ignores hide() while opening; finish dismissal after that transition.
    dismissWhenShown = menuPanel.classList.contains('collapsing') &&
      menuToggle.getAttribute('aria-expanded') === 'true';
    collapse.hide();
    if (restoreFocus) menuToggle.focus();
  };

  menuPanel.addEventListener('shown.bs.collapse', () => {
    if (dismissWhenShown) {
      dismissWhenShown = false;
      collapse.hide();
    }
  });
  menuPanel.addEventListener('hide.bs.collapse', () => { dismissWhenShown = false; });

  document.addEventListener('click', event => {
    if (!navbar.contains(event.target) ||
        (menuPanel.contains(event.target) && event.target.closest('a'))) {
      dismissMenu();
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobile.matches && isMenuOpen()) {
      event.preventDefault();
      dismissMenu(true);
    }
  });
  mobile.addEventListener('change', event => {
    if (!event.matches) collapse.hide();
  });
}

// Preserve links shared before the site was split into separate pages.
if (document.body.dataset.page === 'home') {
  const legacyRoutes = {
    '#about': 'about/', '#dates': 'dates/', '#program': 'program/',
    '#cfp': 'cfp/', '#tasks': 'tasks/', '#organizers': 'organizers/',
    '#contact': 'contact/', '#shared-task-dates': 'dates/#shared-task-dates',
    '#paper-types': 'cfp/#paper-types'
  };
  const redirectLegacyHash = () => {
    const route = legacyRoutes[window.location.hash];
    if (route) window.location.replace(new URL(route, window.location.href));
  };
  window.addEventListener('hashchange', redirectLegacyHash);
  redirectLegacyHash();
}

// Use a neutral avatar when an optional profile photo is unavailable.
document.querySelectorAll('img[data-fallback]').forEach(photo => {
  const showPlaceholder = () => {
    const fallback = photo.dataset.fallback;
    if (!fallback) return;
    delete photo.dataset.fallback;
    photo.src = fallback;
  };
  photo.addEventListener('error', showPlaceholder, { once: true });
  if (photo.complete && photo.naturalWidth === 0) showPlaceholder();
});

// Count only this page, then sum read-only statistics for every current route.
const visitCounters = document.querySelector('[data-visit-counters]');
const visitBeacon = document.querySelector('#visit-beacon');
if (visitCounters && visitBeacon) {
  const readVisits = async identifier => {
    const url = new URL('https://img.shields.io/badge/dynamic/json');
    url.search = new URLSearchParams({
      url: 'https://hits.sh/api/urns/' + identifier,
      query: '$.total', label: 'visits', cacheSeconds: '300'
    }).toString();
    const response = await fetch(url, {
      credentials: 'omit', referrerPolicy: 'no-referrer',
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) throw new Error('Counter unavailable');
    const svg = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
    const title = svg.querySelector('title')?.textContent || '';
    // The statistics API returns 404 until a page receives its first visit.
    if (title === 'visits: resource not found') return 0;
    const match = /^visits: (\d+)$/.exec(title);
    if (!match || !Number.isSafeInteger(Number(match[1]))) throw new Error('Invalid count');
    return Number(match[1]);
  };
  const showVisits = async () => {
    const total = visitCounters.querySelector('[data-visit-total]');
    const current = visitCounters.querySelector('[data-visit-current]');
    try {
      const identifiers = JSON.parse(visitCounters.dataset.visitCounters);
      const entries = Object.entries(identifiers);
      const results = await Promise.allSettled(entries.map(async ([route, identifier]) =>
        [route, await readVisits(identifier)]));
      const counts = Object.fromEntries(results.filter(result => result.status === 'fulfilled')
        .map(result => result.value));
      const pageCount = counts[visitCounters.dataset.visitPage];
      current.textContent = pageCount === undefined ? '—' : pageCount.toLocaleString('en');
      if (results.some(result => result.status === 'rejected')) throw new Error('Incomplete totals');
      const siteCount = Object.values(counts).reduce((sum, count) => sum + count, 0);
      total.textContent = siteCount.toLocaleString('en');
    } catch {
      total.textContent = '—';
      visitCounters.title = 'Visit totals temporarily unavailable; please try again later';
    }
  };
  if (visitBeacon.complete) {
    showVisits();
  } else {
    visitBeacon.addEventListener('load', showVisits, { once: true });
    visitBeacon.addEventListener('error', showVisits, { once: true });
  }
}
