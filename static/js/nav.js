// /js/nav.js — mobile navigation toggle (hamburger)
(function () {
  var toggle = document.getElementById('nav-toggle');
  var nav = document.getElementById('site-nav');
  var header = document.querySelector('.site-header');
  if (!toggle || !nav || !header) return;

  function isOpen() {
    return header.classList.contains('nav-open');
  }

  function setOpen(open) {
    header.classList.toggle('nav-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  toggle.addEventListener('click', function () {
    setOpen(!isOpen());
  });

  // Close when a navigation link is chosen (mobile drawer).
  nav.addEventListener('click', function (e) {
    var link = e.target.closest('a');
    if (link && isOpen()) setOpen(false);
  });

  // Close on Escape and when resizing up to desktop.
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) {
      setOpen(false);
      toggle.focus();
    }
  });
  window.addEventListener('resize', function () {
    if (window.innerWidth > 768 && isOpen()) setOpen(false);
  });
})();
