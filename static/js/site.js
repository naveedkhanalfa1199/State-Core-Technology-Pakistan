(function () {
  /* Mobile nav: burger + slide-in panel + backdrop */
  var b = document.querySelector('.burger'), n = document.getElementById('nav');
  var backdrop = document.getElementById('nav-backdrop');
  function closeNav() {
    if (!n) return;
    n.classList.remove('is-open');
    document.body.classList.remove('nav-open');
    if (b) b.setAttribute('aria-expanded', 'false');
  }
  if (b && n) {
    b.addEventListener('click', function () {
      var open = n.classList.toggle('is-open');
      document.body.classList.toggle('nav-open', open);
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    n.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', closeNav); });
  }
  if (backdrop) backdrop.addEventListener('click', closeNav);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeNav(); });

  /* Header gets a shadow once the page scrolls */
  var top = document.querySelector('.top');
  if (top) {
    var onScroll = function () { top.classList.toggle('top--scrolled', window.scrollY > 8); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* Gentle reveal-on-scroll for section headers, cards and similar blocks.
     Progressive enhancement only: everything stays visible if JS/observer is unavailable. */
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var targets = document.querySelectorAll('.sec__head, .card, .proj, .quote, .steps li, .browser, .hero__copy');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    targets.forEach(function (el, i) {
      el.classList.add('reveal');
      el.style.setProperty('--reveal-delay', (i % 6) * 60 + 'ms');
      io.observe(el);
    });
  }
})();
