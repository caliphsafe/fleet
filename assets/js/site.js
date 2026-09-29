(() => {
  'use strict';

  const menuToggle = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('#primary-nav');
  const closeNav = () => {
    if (!menuToggle || !nav) return;
    menuToggle.setAttribute('aria-expanded', 'false');
    nav.classList.remove('is-open');
    document.querySelectorAll('[data-nav-trigger]').forEach((button) => {
      button.setAttribute('aria-expanded', 'false');
      const panel = document.getElementById(button.getAttribute('aria-controls'));
      if (panel) panel.hidden = true;
    });
  };

  menuToggle?.addEventListener('click', () => {
    const open = menuToggle.getAttribute('aria-expanded') !== 'true';
    menuToggle.setAttribute('aria-expanded', String(open));
    nav?.classList.toggle('is-open', open);
    if (!open) closeNav();
  });

  document.querySelectorAll('[data-nav-trigger]').forEach((button) => {
    button.addEventListener('click', () => {
      const panel = document.getElementById(button.getAttribute('aria-controls'));
      const open = button.getAttribute('aria-expanded') !== 'true';
      document.querySelectorAll('[data-nav-trigger]').forEach((other) => {
        const otherPanel = document.getElementById(other.getAttribute('aria-controls'));
        other.setAttribute('aria-expanded', 'false');
        if (otherPanel) otherPanel.hidden = true;
      });
      button.setAttribute('aria-expanded', String(open));
      if (panel) panel.hidden = !open;
    });
  });

  document.addEventListener('click', (event) => {
    if (nav && !nav.contains(event.target) && !menuToggle?.contains(event.target)) closeNav();
    const searchBox = document.querySelector('.nav-search');
    if (searchBox && !searchBox.contains(event.target)) hideSearchResults();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeNav();
      hideSearchResults();
      document.querySelector('[data-lightbox-dialog]')?.close();
    }
  });

  const searchInput = document.querySelector('#site-search');
  const searchResults = document.querySelector('#search-results');
  let searchIndex;
  async function loadSearchIndex() {
    if (!searchIndex) {
      const response = await fetch('/assets/data/search-index.json');
      if (!response.ok) throw new Error('Search index unavailable');
      searchIndex = await response.json();
    }
    return searchIndex;
  }
  function hideSearchResults() {
    if (!searchResults || !searchInput) return;
    searchResults.hidden = true;
    searchInput.setAttribute('aria-expanded', 'false');
  }
  function showSearchResults() {
    if (!searchResults || !searchInput) return;
    searchResults.hidden = false;
    searchInput.setAttribute('aria-expanded', 'true');
  }
  searchInput?.addEventListener('input', async () => {
    const query = searchInput.value.trim().toLowerCase();
    if (query.length < 2) {
      hideSearchResults();
      return;
    }
    showSearchResults();
    searchResults.innerHTML = '<p class="search-empty">Searching…</p>';
    try {
      const pages = await loadSearchIndex();
      const matches = pages.map((page) => {
        const haystack = `${page.title} ${page.description} ${page.text}`.toLowerCase();
        const title = page.title.toLowerCase();
        const score = (title.includes(query) ? 4 : 0) + (haystack.includes(query) ? 1 : 0);
        return { ...page, score };
      }).filter((page) => page.score).sort((a, b) => b.score - a.score).slice(0, 6);
      searchResults.innerHTML = matches.length
        ? matches.map((page) => `<a class="search-result" role="option" href="${escapeAttribute(page.path)}"><strong>${escapeHTML(page.title)}</strong><span>${escapeHTML(page.description)}</span></a>`).join('')
        : '<p class="search-empty">No matching pages. Try a different word.</p>';
    } catch {
      searchResults.innerHTML = '<p class="search-empty">Search is temporarily unavailable.</p>';
    }
  });
  searchInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      const first = searchResults?.querySelector('a');
      if (first) window.location.href = first.href;
    }
    if (event.key === 'ArrowDown') searchResults?.querySelector('a')?.focus();
  });
  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  }
  function escapeAttribute(value) {
    return escapeHTML(value).replace(/`/g, '&#96;');
  }

  const carousel = document.querySelector('.home-hero');
  if (carousel) {
    const slides = [...carousel.querySelectorAll('[data-slide]')];
    const dots = [...carousel.querySelectorAll('[data-slide-to]')];
    const pause = carousel.querySelector('[data-slide-pause]');
    let current = 0;
    let timer;
    let manuallyPaused = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function selectSlide(index) {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => {
        const active = i === current;
        slide.classList.toggle('is-active', active);
        slide.setAttribute('aria-hidden', String(!active));
        slide.inert = !active;
      });
      dots.forEach((dot, i) => dot.setAttribute('aria-current', String(i === current)));
    }
    function stopTimer() { window.clearInterval(timer); }
    function startTimer() {
      stopTimer();
      if (!manuallyPaused) timer = window.setInterval(() => selectSlide(current + 1), 7200);
    }
    carousel.querySelector('[data-slide-prev]')?.addEventListener('click', () => { selectSlide(current - 1); startTimer(); });
    carousel.querySelector('[data-slide-next]')?.addEventListener('click', () => { selectSlide(current + 1); startTimer(); });
    dots.forEach((dot) => dot.addEventListener('click', () => {
      selectSlide(Number(dot.getAttribute('data-slide-to')));
      startTimer();
    }));
    pause?.addEventListener('click', () => {
      manuallyPaused = !manuallyPaused;
      pause.setAttribute('aria-label', manuallyPaused ? 'Play slideshow' : 'Pause slideshow');
      pause.textContent = manuallyPaused ? '▶' : 'Ⅱ';
      startTimer();
    });
    carousel.addEventListener('mouseenter', stopTimer);
    carousel.addEventListener('mouseleave', startTimer);
    carousel.addEventListener('focusin', stopTimer);
    carousel.addEventListener('focusout', (event) => {
      if (!carousel.contains(event.relatedTarget)) startTimer();
    });
    selectSlide(0);
    startTimer();
  }

  document.querySelectorAll('img[data-fallback]').forEach((image) => {
    image.addEventListener('error', () => {
      const fallback = image.dataset.fallback;
      if (fallback && !image.dataset.fallbackUsed) {
        image.dataset.fallbackUsed = 'true';
        image.src = fallback;
      } else {
        image.classList.add('image-unavailable');
      }
    });
  });

  const lightbox = document.querySelector('[data-lightbox-dialog]');
  const lightboxImage = lightbox?.querySelector('[data-lightbox-image]');
  const lightboxCaption = lightbox?.querySelector('[data-lightbox-caption]');
  const photoLinks = [...document.querySelectorAll('a[data-lightbox]')];
  let photoIndex = 0;
  function showPhoto(index) {
    if (!photoLinks.length || !lightboxImage) return;
    photoIndex = (index + photoLinks.length) % photoLinks.length;
    const link = photoLinks[photoIndex];
    const thumb = link.querySelector('img');
    lightboxImage.alt = thumb?.alt || '';
    lightboxImage.src = thumb?.currentSrc || link.href;
    if (thumb?.dataset.fallbackUsed && link.dataset.fallbackHref) lightboxImage.src = link.dataset.fallbackHref;
    lightboxCaption.textContent = thumb?.alt || '';
  }
  photoLinks.forEach((link, index) => link.addEventListener('click', (event) => {
    event.preventDefault();
    photoIndex = index;
    showPhoto(photoIndex);
    lightbox?.showModal();
  }));
  lightbox?.querySelector('[data-lightbox-close]')?.addEventListener('click', () => lightbox.close());
  lightbox?.querySelector('[data-lightbox-prev]')?.addEventListener('click', () => showPhoto(photoIndex - 1));
  lightbox?.querySelector('[data-lightbox-next]')?.addEventListener('click', () => showPhoto(photoIndex + 1));
  lightbox?.addEventListener('click', (event) => {
    if (event.target === lightbox) lightbox.close();
  });

  document.querySelectorAll('[data-current-year]').forEach((element) => {
    element.textContent = String(new Date().getFullYear());
  });

  document.querySelectorAll('[data-site-form]').forEach((form) => {
    const status = form.querySelector('.form-status');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const values = Object.fromEntries(new FormData(form).entries());
      values.kind = form.dataset.siteForm;
      if (status) {
        status.textContent = 'Sending your message…';
        status.dataset.state = 'pending';
      }
      const submit = form.querySelector('[type=submit]');
      if (submit) submit.disabled = true;
      form.setAttribute('aria-busy', 'true');
      let delivered = false;
      let deliveryIssue = 'unavailable';
      try {
        const response = await fetch('/api/forms', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(values),
        });
        const result = await response.json().catch(() => ({}));
        delivered = response.ok && result.ok === true;
        if (!response.ok) deliveryIssue = response.status === 503 ? 'not-configured' : 'failed';
      } catch {
        delivered = false;
        deliveryIssue = 'unavailable';
      }
      if (delivered) {
        if (status) {
          status.textContent = form.dataset.siteForm === 'crew-application'
            ? 'Your application was sent. Thank you for your interest.'
            : 'Your message was sent. Thank you for contacting Fleet Fisheries.';
          status.dataset.state = 'success';
        }
        form.reset();
      } else {
        const isCrew = form.dataset.siteForm === 'crew-application';
        const subject = isCrew ? 'Fleet Fisheries vessel crew application' : 'Fleet Fisheries website inquiry';
        const body = Object.entries(values)
          .filter(([key, value]) => !['kind', 'companyWebsite'].includes(key) && String(value).trim())
          .map(([key, value]) => `${key.replace(/[A-Z]/g, (letter) => ` ${letter.toLowerCase()}`)}: ${value}`)
          .join('\n');
        if (status) {
          status.textContent = deliveryIssue === 'not-configured'
            ? 'Direct form delivery is not configured. You can send this message by email instead: '
            : 'The message was not sent online. You can send it by email instead: ';
          const emailLink = document.createElement('a');
          emailLink.href = `mailto:sales@fleetfisheries.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
          emailLink.textContent = 'open a prefilled email';
          status.append(emailLink);
          status.dataset.state = deliveryIssue === 'failed' ? 'error' : 'fallback';
        }
      }
      if (submit) submit.disabled = false;
      form.removeAttribute('aria-busy');
    });
  });
})();
