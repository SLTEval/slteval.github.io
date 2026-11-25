/* Navigation is enhanced progressively; all page content and links are static. */
const header = document.querySelector('.site-header');
const toggle = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#primary-nav');
if (header && toggle && navigation) {
  header.classList.add('menu-ready');
  toggle.hidden = false;
  const closeMenu = () => {
    toggle.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('is-open');
  };
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(expanded));
    navigation.classList.toggle('is-open', expanded);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      toggle.focus();
    }
  });
  const desktop = window.matchMedia('(min-width: 901px)');
  const syncMenu = () => {
    toggle.hidden = desktop.matches;
    closeMenu();
  };
  desktop.addEventListener('change', syncMenu);
  syncMenu();
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
