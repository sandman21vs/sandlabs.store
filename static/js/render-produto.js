// /js/render-produto.js — página de produto dedicada (estilo marketplace)
(function(){
  function t(key, fallback) {
    if (typeof window.t === 'function') return window.t(key, fallback);
    return fallback || key;
  }

  function el(tag, attrs = {}, html) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') e.className = v;
      else if (k === 'dataset') Object.entries(v).forEach(([dk, dv]) => e.dataset[dk] = dv);
      else if (k === 'onclick') e.addEventListener('click', v);
      else e.setAttribute(k, v);
    });
    if (html != null) e.innerHTML = html;
    return e;
  }

  function findProductById(id) {
    return (window.PRODUTOS || []).find((product) => product.id === id) || null;
  }

  function displayPrice(price) {
    if (window.CurrencyDisplay && typeof window.CurrencyDisplay.formatPrice === 'function') {
      return window.CurrencyDisplay.formatPrice(price);
    }
    return price && price.valor ? price.valor : '';
  }

  function formDataToObject(form) {
    const data = {};
    const fd = new FormData(form);
    for (const [key, value] of fd.entries()) {
      data[key] = value;
    }
    form.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      data[input.name] = input.checked;
    });
    return data;
  }

  function sanitize(value) {
    return (value || '').toString().trim();
  }

  function toThumbSrc(src) {
    const value = String(src || '');
    const suffixAt = value.search(/[?#]/);
    const path = suffixAt === -1 ? value : value.slice(0, suffixAt);
    const suffix = suffixAt === -1 ? '' : value.slice(suffixAt);
    const match = path.match(/^(\/?images\/)(?!thumb\/)(.+)\.[^./]+$/i);
    return match ? `${match[1]}thumb/${match[2]}.webp${suffix}` : value;
  }

  function normalizeLabel(text) {
    return (text || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\([^)]*\)/g, ' ')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  function findMatchingPrice(prod, option, index) {
    const prices = Array.isArray(prod.preco) ? prod.preco : [];
    if (!prices.length) return null;

    const optionLabel = normalizeLabel(option.title);
    const matched = prices.find((price) => {
      const priceLabel = normalizeLabel(price.label);
      return optionLabel && priceLabel && (
        optionLabel.includes(priceLabel)
        || priceLabel.includes(optionLabel)
        || (optionLabel.includes('box') && priceLabel.includes('box'))
        || (optionLabel.includes('modcase') && priceLabel.includes('modcase'))
      );
    });

    if (matched) return matched;
    return prices[0];
  }

  function selectionPayload(option, inputs) {
    return { title: option.title || '', inputs };
  }

  function buildCartItems(prod, form) {
    const prices = Array.isArray(prod.preco) ? prod.preco : [];
    if (!prices.length || !prices[0].id) {
      return { error: t('public.products.errors.no_cart_price', 'This product does not have a cart price configured yet.'), items: [] };
    }

    const data = formDataToObject(form);

    if (prod.id === 'sandseed') {
      const mode = sanitize(data.seedPack) === 'single' ? 'single' : 'kit';
      const selectedPrice = prices.find((price) => {
        return mode === 'single' ? price.amountSats === 2000 : price.amountSats === 5000;
      }) || prices[0];

      return {
        error: '',
        items: [
          {
            productId: prod.id,
            priceId: selectedPrice.id,
            quantity: mode === 'single' ? Math.max(1, parseInt(data.seedQty || '1', 10) || 1) : 1,
            options: { mode }
          }
        ]
      };
    }

    const primaryPrice = prices[0];
    const primarySelections = [];
    const extraItems = [];

    (prod.options || []).forEach((option, index) => {
      if (option.type === 'seedPack') return;

      if (option.type === 'colorPair') {
        const first = option.inputs?.[0];
        const second = option.inputs?.[1];
        const firstValue = sanitize(data[first?.name]);
        const secondValue = sanitize(data[second?.name]);

        if ((firstValue && !secondValue) || (!firstValue && secondValue)) {
          extraItems.length = 0;
          primarySelections.length = 0;
          throw new Error(t('public.products.errors.select_both_colors', 'Select both colors for “{title}” or leave both blank.').replace('{title}', option.title || ''));
        }

        if (!firstValue && !secondValue) return;

        const payload = selectionPayload(option, [
          { name: first?.name, label: first?.label || t('public.products.color_default_1', 'Color 1'), value: firstValue },
          { name: second?.name, label: second?.label || t('public.products.color_default_2', 'Color 2'), value: secondValue }
        ]);
        const matchedPrice = findMatchingPrice(prod, option, index);
        if (matchedPrice && matchedPrice.id !== primaryPrice.id) {
          extraItems.push({ productId: prod.id, priceId: matchedPrice.id, quantity: 1, options: { selections: [payload] } });
        } else {
          primarySelections.push(payload);
        }
      }

      if (option.type === 'colorSingle') {
        const input = option.input;
        const value = sanitize(data[input?.name]);
        if (!value) return;

        const payload = selectionPayload(option, [
          { name: input?.name, label: input?.label || option.title || t('public.products.color_default', 'Color'), value }
        ]);
        const matchedPrice = findMatchingPrice(prod, option, index);
        if (matchedPrice && matchedPrice.id !== primaryPrice.id) {
          extraItems.push({ productId: prod.id, priceId: matchedPrice.id, quantity: 1, options: { selections: [payload] } });
        } else {
          primarySelections.push(payload);
        }
      }
    });

    const items = [
      {
        productId: prod.id,
        priceId: primaryPrice.id,
        quantity: 1,
        options: primarySelections.length ? { selections: primarySelections } : {}
      }
    ];

    extraItems.forEach((item) => items.push(item));

    if (data.addSeedKit && prod.allowAddOnSeed) {
      const seedProduct = findProductById('sandseed');
      const seedPrice = (seedProduct?.preco || []).find((price) => price.amountSats === 5000);
      if (seedProduct && seedPrice?.id) {
        items.push({ productId: seedProduct.id, priceId: seedPrice.id, quantity: 1, options: { mode: 'kit' } });
      }
    }

    return { error: '', items };
  }

  function priceListHTML(precos) {
    if (!Array.isArray(precos)) return '';
    return precos.map((p) => {
      const displayed = displayPrice(p);
      const sats = p.satsDisplay && !/sats/i.test(displayed) ? ` <span class="muted">${p.satsDisplay}</span>` : '';
      return `<p><strong>${p.label}:</strong> ${displayed}${sats}</p>`;
    }).join('');
  }

  /* Mídia: imagem principal grande + tira de miniaturas */
  function buildMedia(prod) {
    const media = el('div', { class:'mc-media-inner' });
    const imagens = Array.isArray(prod.imagens) ? prod.imagens : [];
    if (!imagens.length) return media;

    const fullPaths = imagens.map((src) => src);
    let currentIndex = 0;

    const hero = el('img', {
      class:'mc-hero',
      src: toThumbSrc(imagens[0]),
      alt: prod.nome,
      loading:'lazy',
      decoding:'async'
    });
    const setHero = (index) => {
      currentIndex = index;
      const src = imagens[index];
      hero.src = toThumbSrc(src);
      hero.dataset.full = src;
    };
    hero.addEventListener('error', () => {
      const full = hero.dataset.full || imagens[currentIndex];
      if (full && hero.getAttribute('src') !== full) hero.setAttribute('src', full);
    });
    hero.addEventListener('click', () => {
      if (window.lightbox && typeof lightbox.open === 'function') {
        lightbox.open(fullPaths, currentIndex);
      }
    });
    setHero(0);
    media.appendChild(hero);

    if (imagens.length > 1) {
      const strip = el('div', { class:'mc-thumbs' });
      imagens.forEach((src, i) => {
        const thumb = el('img', {
          class:'mc-thumb' + (i === 0 ? ' is-active' : ''),
          src: toThumbSrc(src),
          alt: `${prod.nome} ${i + 1}`,
          loading:'lazy',
          decoding:'async'
        });
        thumb.addEventListener('error', () => {
          if (thumb.getAttribute('src') !== src) thumb.setAttribute('src', src);
        });
        thumb.addEventListener('click', () => {
          setHero(i);
          strip.querySelectorAll('.mc-thumb').forEach((node) => node.classList.remove('is-active'));
          thumb.classList.add('is-active');
        });
        strip.appendChild(thumb);
      });
      media.appendChild(strip);
    }

    return media;
  }

  /* Monta os grupos de opções (cor / seed) + add-on dentro do form */
  function buildOptionsForm(prod) {
    const form = el('form', { id:'produto-form' });

    (prod.options || []).forEach(opt => {
      if (opt.type === 'colorPair') {
        const group = el('div', { class:'group' });
        group.appendChild(el('p', {}, `<strong>${opt.title}</strong>`));
        opt.inputs.forEach(inp => {
          group.appendChild(el('p', {}, inp.label + ':'));
          const grid = el('div', { class:'option-grid' });
          if (typeof buildColorSelector === 'function') buildColorSelector(grid, inp.name);
          group.appendChild(grid);
        });
        form.appendChild(group);
      }

      if (opt.type === 'colorSingle') {
        const group = el('div', { class:'group' });
        group.appendChild(el('p', {}, `<strong>${opt.title}</strong>`));
        const grid = el('div', { class:'option-grid' });
        if (typeof buildColorSelector === 'function') buildColorSelector(grid, opt.input.name);
        group.appendChild(grid);
        form.appendChild(group);
      }

      if (opt.type === 'seedPack') {
        const group = el('div', { class:'group' });
        group.appendChild(el('p', {}, `<strong>${t('public.products.seed.select', 'Select:')}</strong>`));
        const labelKit = el('label', {}, `
          <input type="radio" name="seedPack" value="kit" checked> ${t('public.products.seed.kit_label', '5-unit kit – 5,000 sats')}
        `);
        const labelSingle = el('label', {}, `
          <input type="radio" name="seedPack" value="single"> ${t('public.products.seed.single_label', 'Single plate – 2,000 sats')}
        `);
        group.appendChild(labelKit);
        group.appendChild(el('br'));
        group.appendChild(labelSingle);

        const qtyBox = el('div', { id:'seedQtyBox', style:'display:none;margin-top:8px' });
        qtyBox.innerHTML = `
          <p>${t('public.products.seed.qty_label', 'Number of plates:')}</p>
          <input type="number" name="seedQty" min="1" max="10" value="1">
        `;
        group.appendChild(qtyBox);

        group.addEventListener('change', (e) => {
          if (e.target.name === 'seedPack') {
            qtyBox.style.display = (e.target.value === 'single') ? 'block' : 'none';
          }
        });
        form.appendChild(group);
      }
    });

    if (prod.allowAddOnSeed && prod.id !== 'sandseed') {
      const groupAddon = el('div', { class:'group' });
      groupAddon.innerHTML = `
        <label>
          <input type="checkbox" name="addSeedKit">
          ${t('public.products.add_seed_kit', 'Add <strong>SandSeed kit (5 plates)</strong>')}
        </label>
      `;
      form.appendChild(groupAddon);
    }

    /* Cupom salvo é aplicado pelo cupom.js; sem input de CEP/contato aqui. */
    return form;
  }

  /* Seletor de quantidade (não exibido para sandseed, que tem sua própria qtd) */
  function buildQtySelector(state) {
    const wrap = el('div', { class:'pd-qty' });
    wrap.appendChild(el('span', { class:'pd-qty-label' }, t('public.products.detail.quantity', 'Quantity')));
    const minus = el('button', { type:'button', class:'pd-qty-btn', 'aria-label':'-' }, '−');
    const value = el('span', { class:'pd-qty-value' }, '1');
    const plus = el('button', { type:'button', class:'pd-qty-btn', 'aria-label':'+' }, '+');
    const sync = () => { value.textContent = String(state.qty); };
    minus.addEventListener('click', () => { state.qty = Math.max(1, state.qty - 1); sync(); });
    plus.addEventListener('click', () => { state.qty = Math.min(99, state.qty + 1); sync(); });
    wrap.appendChild(minus);
    wrap.appendChild(value);
    wrap.appendChild(plus);
    return wrap;
  }

  async function submitToCart(prod, form, state, buttons, redirectUrl) {
    let items;
    try {
      const result = buildCartItems(prod, form);
      if (result.error) { alert(result.error); return; }
      items = result.items;
    } catch (err) {
      alert(err.message || t('public.products.errors.add_to_cart_failed', 'Could not add the product to the cart.'));
      return;
    }
    if (typeof addCartBatch !== 'function') {
      alert(t('public.products.errors.cart_unavailable', 'Cart unavailable right now.'));
      return;
    }
    if (prod.id !== 'sandseed' && state.qty > 1 && items.length) {
      items[0].quantity = state.qty;
    }
    buttons.forEach((b) => { b.disabled = true; });
    try {
      await addCartBatch(items);
      if (redirectUrl) {
        window.location.href = redirectUrl;
        return;
      }
      if (typeof showCartToast === 'function') {
        showCartToast(t('public.products.toast.added_to_cart', 'Product added to cart.'));
      }
    } catch (err) {
      alert(err.message || t('public.products.errors.add_to_cart_failed', 'Could not add the product to the cart.'));
    } finally {
      buttons.forEach((b) => { b.disabled = false; });
    }
  }

  function render(prod, root) {
    const checkoutUrl = root.dataset.checkoutUrl || '/checkout';
    const state = { qty: 1 };

    root.innerHTML = '';
    const layout = el('div', { class:'mc-layout produto-detail-layout' });

    /* Coluna de mídia (sticky no desktop) */
    const media = el('div', { class:'mc-media produto-media' });
    media.appendChild(buildMedia(prod));
    layout.appendChild(media);

    /* Coluna de compra */
    const buybox = el('div', { class:'mc-buybox produto-buybox' });
    buybox.appendChild(el('h1', { class:'pd-title' }, prod.nome));
    if (prod.resumo) buybox.appendChild(el('p', { class:'mc-summary' }, prod.resumo));
    buybox.appendChild(el('div', { class:'mc-price' }, priceListHTML(prod.preco)));

    const form = buildOptionsForm(prod);
    buybox.appendChild(form);

    if (prod.id !== 'sandseed') {
      buybox.appendChild(buildQtySelector(state));
    }

    const actions = el('div', { class:'final-actions pd-actions' });
    const buyNow = el('button', { type:'button', class:'final-btn final-btn-accent final-btn-primary pd-buy-now' },
      t('public.products.detail.buy_now', 'Buy now'));
    const addCart = el('button', { type:'button', class:'final-btn pd-add-cart' },
      t('public.products.actions.add_to_cart', 'Add to cart'));
    const buttons = [buyNow, addCart];
    buyNow.addEventListener('click', () => submitToCart(prod, form, state, buttons, checkoutUrl));
    addCart.addEventListener('click', () => submitToCart(prod, form, state, buttons, null));
    actions.appendChild(buyNow);
    actions.appendChild(addCart);
    buybox.appendChild(actions);

    layout.appendChild(buybox);
    root.appendChild(layout);

    /* Descrição completa (largura total, aberta por padrão) */
    if (prod.detalhesHTML) {
      const desc = el('section', { class:'pd-desc card' });
      desc.appendChild(el('h2', { class:'pd-desc-title' }, t('public.products.detail.description', 'Description')));
      desc.appendChild(el('div', { class:'pd-desc-body' }, prod.detalhesHTML));
      root.appendChild(desc);
    }

    /* Cupom salvo preenche inputs name=cupom (se houver) via cupom.js */
  }

  function boot() {
    const root = document.getElementById('produto-detail');
    const prod = window.PRODUTO;
    if (!root || !prod) return;
    if (window.lightbox && typeof lightbox.mount === 'function') lightbox.mount();
    render(prod, root);
    if (window.CurrencyDisplay && typeof window.CurrencyDisplay.loadRates === 'function') {
      window.CurrencyDisplay.loadRates().then(() => render(prod, root));
    }
    window.addEventListener('displaycurrencychange', () => render(prod, root));
  }

  window.addEventListener('DOMContentLoaded', boot);
})();
