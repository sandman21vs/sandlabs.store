// /js/product-card.js — shared product card for the home and catalog grids
(function(){
  function t(key, fallback) {
    if (typeof window.t === 'function') return window.t(key, fallback);
    return fallback || key;
  }

  function el(tag, attrs = {}, text) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') e.className = v;
      else e.setAttribute(k, v);
    });
    if (text != null) e.textContent = text;
    return e;
  }

  function toThumbSrc(src) {
    const value = String(src || '');
    const suffixAt = value.search(/[?#]/);
    const path = suffixAt === -1 ? value : value.slice(0, suffixAt);
    const suffix = suffixAt === -1 ? '' : value.slice(suffixAt);
    const match = path.match(/^(\/?images\/)(?!thumb\/)(.+)\.[^./]+$/i);
    return match ? `${match[1]}thumb/${match[2]}.webp${suffix}` : value;
  }

  function displayPrice(price) {
    if (window.CurrencyDisplay && typeof window.CurrencyDisplay.formatPrice === 'function') {
      return window.CurrencyDisplay.formatPrice(price);
    }
    return price && price.valor ? price.valor : '';
  }

  function productUrl(prod) {
    return '/produtos/' + encodeURIComponent(prod.id);
  }

  /* The title link is stretched over the whole card, so the card has one
     focusable target and stays keyboard- and screen-reader-friendly. */
  function build(prod) {
    const card = el('article', { class:'card product-card hover-lift' });
    if (prod.badge && prod.badge.text) {
      card.appendChild(el('span', { class:'card-badge ' + (prod.badge.variant || 'neutral') }, prod.badge.text));
    }

    const media = el('div', { class:'card-media' });
    const fullSrc = (Array.isArray(prod.imagens) && prod.imagens[0]) || '';
    const img = el('img', {
      src: toThumbSrc(fullSrc), alt: '',
      loading:'lazy', decoding:'async'
    });
    img.addEventListener('error', () => {
      if (fullSrc && img.getAttribute('src') !== fullSrc) img.setAttribute('src', fullSrc);
    });
    media.appendChild(img);
    card.appendChild(media);

    const body = el('div', { class:'card-body' });
    const title = el('h3', { class:'card-title' });
    title.appendChild(el('a', { class:'card-link', href: productUrl(prod) }, prod.nome));
    body.appendChild(title);
    if (prod.resumo) body.appendChild(el('p', { class:'card-text' }, prod.resumo));

    const price = Array.isArray(prod.preco) ? prod.preco[0] : null;
    if (price) {
      const shown = displayPrice(price);
      const line = el('div', { class:'price-line' });
      line.appendChild(el('strong', {}, shown));
      if (price.satsDisplay && !/sats/i.test(shown || '')) {
        line.appendChild(el('span', { class:'muted' }, price.satsDisplay));
      }
      body.appendChild(line);
    }
    body.appendChild(el('span', { class:'btn btn-accent product-card-btn', 'aria-hidden':'true' },
      t('public.products.view_product', 'View product')));
    card.appendChild(body);
    return card;
  }

  function renderInto(containerId, limit) {
    function render() {
      const wrap = document.getElementById(containerId);
      if (!wrap) return;
      wrap.innerHTML = '';
      const products = window.PRODUTOS || [];
      (limit ? products.slice(0, limit) : products).forEach((prod) => wrap.appendChild(build(prod)));
    }
    window.addEventListener('DOMContentLoaded', () => {
      render();
      if (window.CurrencyDisplay && typeof window.CurrencyDisplay.loadRates === 'function') {
        window.CurrencyDisplay.loadRates().then(render);
      }
    });
    window.addEventListener('displaycurrencychange', render);
  }

  window.ProductCard = { build, renderInto };
})();
