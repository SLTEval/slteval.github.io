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
