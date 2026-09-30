// Attach CSRF tokens to same-origin JSON requests.
const agriFetch = window.fetch.bind(window);
window.fetch = (input, options = {}) => {
  const target = new URL(typeof input === 'string' ? input : input.url, location.href);
  if (target.origin === location.origin) {
    const headers = new Headers(options.headers || {});
    headers.set('X-CSRF-Token', document.querySelector('meta[name="csrf-token"]')?.content || '');
    options = {...options, headers};
  }
  return agriFetch(input, options);
};
document.addEventListener('DOMContentLoaded', function () {
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    if (typeof bootstrap !== 'undefined') {
      setTimeout(function () {
        bootstrap.Alert.getOrCreateInstance(alert).close();
      }, 4000);
    }
  });
});
