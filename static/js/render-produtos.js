// /js/render-produtos.js — grade de produtos (cada card abre /produtos/<id>)
(function(){
  function t(key, fallback) {
    if (typeof window.t === 'function') return window.t(key, fallback);
    return fallback || key;
  }

  function el(tag, attrs = {}, html) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') e.className = v;
      else if (k === 'onclick') e.addEventListener('click', v);
      else e.setAttribute(k, v);
    });
    if (html != null) e.innerHTML = html;
    return e;
  }

  function displayPrice(price) {
    if (window.CurrencyDisplay && typeof window.CurrencyDisplay.formatPrice === 'function') {
      return window.CurrencyDisplay.formatPrice(price);
    }
    return price && price.valor ? price.valor : '';
  }

  function toThumbSrc(src) {
    const value = String(src || '');
    const suffixAt = value.search(/[?#]/);
    const path = suffixAt === -1 ? value : value.slice(0, suffixAt);
    const suffix = suffixAt === -1 ? '' : value.slice(suffixAt);
    const match = path.match(/^(\/?images\/)(?!thumb\/)(.+)\.[^./]+$/i);
    return match ? `${match[1]}thumb/${match[2]}.webp${suffix}` : value;
  }

  function productUrl(prod) {
    return '/produtos/' + encodeURIComponent(prod.id);
  }

  /* Card compacto de produto (grid) — leva à página do produto */
  function buildProductCard(prod) {
    const card = el('article', { class:'card product-card hover-lift' });
    if (prod.badge && prod.badge.text) {
      card.appendChild(el('span', { class:'card-badge ' + (prod.badge.variant || 'neutral') }, prod.badge.text));
    }
    const media = el('div', { class:'card-media' });
    const firstImg = (Array.isArray(prod.imagens) && prod.imagens[0]) || '';
    const img = el('img', {
      src: toThumbSrc(firstImg), alt: prod.nome,
      loading:'lazy', decoding:'async'
    });
    img.addEventListener('error', () => {
      if (firstImg && img.getAttribute('src') !== firstImg) img.setAttribute('src', firstImg);
    });
    media.appendChild(img);
    card.appendChild(media);

    const body = el('div', { class:'card-body' });
    body.appendChild(el('h3', { class:'card-title' }, prod.nome));
    if (prod.resumo) body.appendChild(el('p', { class:'card-text' }, prod.resumo));
    const price = Array.isArray(prod.preco) ? prod.preco[0] : null;
    if (price) {
      const pl = el('div', { class:'price-line' });
      pl.appendChild(el('span', {}, price.label));
      pl.appendChild(el('strong', {}, displayPrice(price)));
      body.appendChild(pl);
    }
    const btn = el('button', { type:'button', class:'btn btn-accent product-card-btn' },
      prod.buyButtonText || t('public.products.buy_product', 'Buy {name}').replace('{name}', prod.nome));
    btn.addEventListener('click', () => { window.location.href = productUrl(prod); });
    body.appendChild(btn);
    card.appendChild(body);

    media.style.cursor = 'pointer';
    media.addEventListener('click', () => { window.location.href = productUrl(prod); });
    return card;
  }

  function renderProductList() {
    const cont = document.getElementById('produtos-container');
    if (!cont) return;
    cont.innerHTML = '';
    (window.PRODUTOS || []).forEach(prod => {
      cont.appendChild(buildProductCard(prod));
    });
  }

  window.addEventListener('DOMContentLoaded', () => {
    renderProductList();
    if (window.CurrencyDisplay && typeof window.CurrencyDisplay.loadRates === 'function') {
      window.CurrencyDisplay.loadRates().then(renderProductList);
    }
  });
  window.addEventListener('displaycurrencychange', renderProductList);
})();
