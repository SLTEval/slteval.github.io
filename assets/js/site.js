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
