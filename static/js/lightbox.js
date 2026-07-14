// Product image lightbox with desktop magnifier and mobile pinch-to-zoom.
(function(){
  const LENS_ZOOM = 2.5;
  const MAX_TOUCH_ZOOM = 4;

  function t(key, fallback) {
    if (typeof window.t === 'function') return window.t(key, fallback);
    return fallback || key;
  }

  let images = [];
  let index = 0;
  let mounted = false;
  let lastFocused = null;
  let touchScale = 1;
  let initialTouchScale = 1;
  let initialTouchDistance = 0;
  let touchPanX = 0;
  let touchPanY = 0;
  let initialTouchPanX = 0;
  let initialTouchPanY = 0;
  let initialTouchMidpoint = null;
  const touchPointers = new Map();

  function elements() {
    const lightbox = document.getElementById('lightbox');
    return {
      lightbox,
      figure: lightbox && lightbox.querySelector('.lightbox-zoom'),
      image: lightbox && lightbox.querySelector('.lightbox-highres'),
      lens: lightbox && lightbox.querySelector('.zoom-lens')
    };
  }

  function originalSource(item) {
    if (typeof item === 'string') return item;
    if (!item || typeof item !== 'object') return '';
    return item.original || item.full || item.src || '';
  }

  function desktopLensEnabled() {
    return typeof window.matchMedia !== 'function'
      || window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  }

  function hideLens() {
    const { lens } = elements();
    if (lens) lens.classList.remove('is-active');
  }

  function syncLensImage() {
    const { image, lens } = elements();
    if (!image || !lens) return;
    const source = image.currentSrc || image.src;
    lens.style.backgroundImage = source ? `url(${JSON.stringify(source)})` : '';
    hideLens();
  }

  function resetZoom() {
    const { figure, image, lens } = elements();
    touchPointers.clear();
    touchScale = 1;
    initialTouchScale = 1;
    initialTouchDistance = 0;
    touchPanX = 0;
    touchPanY = 0;
    initialTouchPanX = 0;
    initialTouchPanY = 0;
    initialTouchMidpoint = null;

    if (figure) figure.classList.remove('is-touch-zoomed');
    if (image) {
      image.style.removeProperty('transform');
      image.style.removeProperty('transform-origin');
    }
    if (lens) {
      lens.classList.remove('is-active');
      lens.style.removeProperty('background-position');
      lens.style.removeProperty('background-size');
    }
  }

  function moveLens(event) {
    if (!desktopLensEnabled() || touchScale > 1) return;

    const { figure, image, lens } = elements();
    if (!figure || !image || !lens || !image.complete) return;

    const imageRect = image.getBoundingClientRect();
    const figureRect = figure.getBoundingClientRect();
    const x = event.clientX - imageRect.left;
    const y = event.clientY - imageRect.top;
    if (x < 0 || y < 0 || x > imageRect.width || y > imageRect.height) {
      hideLens();
      return;
    }

    const lensWidth = lens.offsetWidth;
    const lensHeight = lens.offsetHeight;
    const imageLeft = imageRect.left - figureRect.left;
    const imageTop = imageRect.top - figureRect.top;
    const lensLeft = Math.max(
      imageLeft,
      Math.min(imageLeft + imageRect.width - lensWidth, imageLeft + x - lensWidth / 2)
    );
    const lensTop = Math.max(
      imageTop,
      Math.min(imageTop + imageRect.height - lensHeight, imageTop + y - lensHeight / 2)
    );

    lens.style.left = `${lensLeft}px`;
    lens.style.top = `${lensTop}px`;
    lens.style.backgroundSize = `${imageRect.width * LENS_ZOOM}px ${imageRect.height * LENS_ZOOM}px`;
    lens.style.backgroundPosition = `${-(x * LENS_ZOOM - lensWidth / 2)}px ${-(y * LENS_ZOOM - lensHeight / 2)}px`;
    lens.classList.add('is-active');
  }

  function pointerDistance(points) {
    const dx = points[0].clientX - points[1].clientX;
    const dy = points[0].clientY - points[1].clientY;
    return Math.hypot(dx, dy);
  }

  function pointerMidpoint(points) {
    return {
      x: (points[0].clientX + points[1].clientX) / 2,
      y: (points[0].clientY + points[1].clientY) / 2
    };
  }

  function clampTouchPan(figure) {
    const maxX = figure.clientWidth * (touchScale - 1) / 2;
    const maxY = figure.clientHeight * (touchScale - 1) / 2;
    touchPanX = Math.max(-maxX, Math.min(maxX, touchPanX));
    touchPanY = Math.max(-maxY, Math.min(maxY, touchPanY));
  }

  function applyTouchTransform(figure, image) {
    if (touchScale <= 1.01) {
      touchScale = 1;
      touchPanX = 0;
      touchPanY = 0;
      image.style.removeProperty('transform');
      image.style.removeProperty('transform-origin');
      figure.classList.remove('is-touch-zoomed');
      return;
    }

    clampTouchPan(figure);
    image.style.transformOrigin = '50% 50%';
    image.style.transform = `translate(${touchPanX}px, ${touchPanY}px) scale(${touchScale})`;
    figure.classList.add('is-touch-zoomed');
    hideLens();
  }

  function startTouchGesture() {
    const points = Array.from(touchPointers.values());
    initialTouchScale = touchScale;
    initialTouchPanX = touchPanX;
    initialTouchPanY = touchPanY;
    if (points.length >= 2) {
      initialTouchDistance = pointerDistance(points);
      initialTouchMidpoint = pointerMidpoint(points);
    } else {
      initialTouchDistance = 0;
      initialTouchMidpoint = points[0] ? { x: points[0].clientX, y: points[0].clientY } : null;
    }
  }

  function rememberTouchPointer(event) {
    if (event.pointerType !== 'touch') return;
    touchPointers.set(event.pointerId, { clientX: event.clientX, clientY: event.clientY });
  }

  function onTouchPointerDown(event) {
    if (event.pointerType !== 'touch') return;
    rememberTouchPointer(event);
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch (_error) {
      // Pointer capture is optional on older mobile browsers.
    }

    if (touchPointers.size <= 2) {
      startTouchGesture();
    }
    if (touchPointers.size === 2) {
      event.preventDefault();
    }
  }

  function onTouchPointerMove(event) {
    if (event.pointerType !== 'touch' || !touchPointers.has(event.pointerId)) return;
    rememberTouchPointer(event);
    const { figure, image } = elements();
    if (!figure || !image) return;

    const points = Array.from(touchPointers.values()).slice(0, 2);
    if (points.length === 1 && touchScale > 1.01 && initialTouchMidpoint) {
      event.preventDefault();
      touchPanX = initialTouchPanX + points[0].clientX - initialTouchMidpoint.x;
      touchPanY = initialTouchPanY + points[0].clientY - initialTouchMidpoint.y;
      applyTouchTransform(figure, image);
      return;
    }
    if (points.length < 2 || !initialTouchDistance || !initialTouchMidpoint) return;

    event.preventDefault();
    const distance = pointerDistance(points);
    const midpoint = pointerMidpoint(points);
    const scaleRatio = Math.max(1, Math.min(MAX_TOUCH_ZOOM, initialTouchScale * distance / initialTouchDistance)) / initialTouchScale;
    const figureRect = figure.getBoundingClientRect();
    const centerX = figureRect.left + figureRect.width / 2;
    const centerY = figureRect.top + figureRect.height / 2;
    touchScale = initialTouchScale * scaleRatio;
    touchPanX = scaleRatio * initialTouchPanX
      + midpoint.x - centerX
      - scaleRatio * (initialTouchMidpoint.x - centerX);
    touchPanY = scaleRatio * initialTouchPanY
      + midpoint.y - centerY
      - scaleRatio * (initialTouchMidpoint.y - centerY);
    applyTouchTransform(figure, image);
  }

  function onTouchPointerEnd(event) {
    if (event.pointerType !== 'touch') return;
    touchPointers.delete(event.pointerId);
    startTouchGesture();
  }

  function trapFocus(event) {
    if (event.key !== 'Tab') return;
    const { lightbox } = elements();
    if (!lightbox) return;
    const controls = Array.from(lightbox.querySelectorAll('button:not([disabled])'));
    if (!controls.length) return;

    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function mountLightbox(){
    if (mounted) return;
    let lightbox = document.getElementById('lightbox');
    if (!lightbox) {
      lightbox = document.createElement('div');
      lightbox.id = 'lightbox';
      lightbox.className = 'lightbox';
      document.body.appendChild(lightbox);
    }
    lightbox.setAttribute('aria-hidden', 'true');
    lightbox.innerHTML = `
      <div class="lightbox-inner" role="dialog" aria-modal="true" aria-label="${t('public.products.lightbox.image_alt', 'Expanded image')}">
        <button class="close-btn" data-action="close" aria-label="${t('public.products.lightbox.close', 'Close')}">×</button>
        <figure class="lightbox-figure lightbox-zoom">
          <img id="imagemModal" class="lightbox-highres" alt="${t('public.products.lightbox.image_alt', 'Expanded image')}" decoding="async" loading="eager" draggable="false"/>
          <span class="zoom-lens" aria-hidden="true"></span>
        </figure>
        <button class="nav-btn prev-btn" data-action="prev" aria-label="${t('public.products.lightbox.previous', 'Previous')}">&#10094;</button>
        <button class="nav-btn next-btn" data-action="next" aria-label="${t('public.products.lightbox.next', 'Next')}">&#10095;</button>
      </div>
    `;

    lightbox.addEventListener('click', function(event){
      const button = event.target.closest('[data-action]');
      if (button) {
        const action = button.getAttribute('data-action');
        if (action === 'close') closeLightbox();
        if (action === 'prev') previousImage();
        if (action === 'next') nextImage();
        return;
      }
      if (event.target === lightbox) closeLightbox();
    });

    window.addEventListener('keydown', function(event){
      if (lightbox.getAttribute('aria-hidden') !== 'false') return;
      if (event.key === 'Escape') closeLightbox();
      else if (event.key === 'ArrowLeft') previousImage();
      else if (event.key === 'ArrowRight') nextImage();
      else trapFocus(event);
    });

    const { figure, image } = elements();
    figure.addEventListener('mousemove', moveLens);
    figure.addEventListener('mouseleave', hideLens);
    figure.addEventListener('pointerdown', onTouchPointerDown);
    figure.addEventListener('pointermove', onTouchPointerMove);
    figure.addEventListener('pointerup', onTouchPointerEnd);
    figure.addEventListener('pointercancel', onTouchPointerEnd);
    figure.addEventListener('lostpointercapture', onTouchPointerEnd);
    image.addEventListener('load', syncLensImage);

    mounted = true;
  }

  function showCurrentImage() {
    const { image } = elements();
    if (!image || !images.length) return;
    resetZoom();
    image.alt = `${t('public.products.lightbox.image_alt', 'Expanded image')} ${index + 1}/${images.length}`;
    image.src = images[index];
    if (image.complete) syncLensImage();
  }

  function openLightbox(items, startIndex){
    mountLightbox();
    const normalizedImages = Array.isArray(items)
      ? items.map((item, originalIndex) => ({ source: originalSource(item), originalIndex })).filter(item => item.source)
      : [];
    images = normalizedImages.map(item => item.source);
    if (!images.length) return;

    const selectedEntry = normalizedImages.find(item => item.originalIndex === startIndex);
    index = selectedEntry ? normalizedImages.indexOf(selectedEntry) : 0;
    const { lightbox } = elements();
    lastFocused = document.activeElement;
    lightbox.style.display = 'flex';
    lightbox.setAttribute('aria-hidden', 'false');
    document.documentElement.classList.add('modal-open');
    document.body.classList.add('modal-open');
    showCurrentImage();

    window.requestAnimationFrame(function(){
      syncLensImage();
      const closeButton = lightbox.querySelector('[data-action="close"]');
      if (closeButton) closeButton.focus();
    });
  }

  function closeLightbox(){
    const { lightbox } = elements();
    if (!lightbox) return;
    resetZoom();
    lightbox.style.display = 'none';
    lightbox.setAttribute('aria-hidden', 'true');
    document.documentElement.classList.remove('modal-open');
    document.body.classList.remove('modal-open');
    if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
    lastFocused = null;
  }

  function previousImage(){
    if (!images.length) return;
    index = (index - 1 + images.length) % images.length;
    showCurrentImage();
  }

  function nextImage(){
    if (!images.length) return;
    index = (index + 1) % images.length;
    showCurrentImage();
  }

  window.lightbox = {
    open: openLightbox,
    close: closeLightbox,
    prev: previousImage,
    next: nextImage,
    mount: mountLightbox
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountLightbox);
  } else {
    mountLightbox();
  }
})();
