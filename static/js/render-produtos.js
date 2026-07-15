// /js/render-produtos.js — ARQUIVO COMPLETO
(function(){
  function t(key, fallback) {
    if (typeof window.t === 'function') return window.t(key, fallback);
    return fallback || key;
  }

  /* Utilitário para criar elementos */
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
    if (index === 0) return prices[0];
    return prices[0];
  }

  function selectionPayload(option, inputs) {
    return {
      title: option.title || '',
      inputs
    };
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
          extraItems.push({
            productId: prod.id,
            priceId: matchedPrice.id,
            quantity: 1,
            options: { selections: [payload] }
          });
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
          extraItems.push({
            productId: prod.id,
            priceId: matchedPrice.id,
            quantity: 1,
            options: { selections: [payload] }
          });
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
        items.push({
          productId: seedProduct.id,
          priceId: seedPrice.id,
          quantity: 1,
          options: { mode: 'kit' }
        });
      }
    }

    return { error: '', items };
  }

  /* Lista de preços HTML */
  function priceListHTML(precos) {
    if (!Array.isArray(precos)) return '';
    return precos.map((p) => {
      const displayed = displayPrice(p);
      const sats = p.satsDisplay && !/sats/i.test(displayed) ? ` <span class="muted">${p.satsDisplay}</span>` : '';
      return `<p><strong>${p.label}:</strong> ${displayed}${sats}</p>`;
    }).join('');
  }

  /* Galeria por produto */
function buildGallery(prod) {
  const g = el('div', { class:'galeria' });
  const fullPaths = prod.imagens.map(src => src);
  prod.imagens.forEach((src, i) => {
    const thumbSrc = toThumbSrc(src);
    const img = el('img', {
      src: thumbSrc,
      alt: `${prod.nome} ${i + 1}`,
      loading: 'lazy',
      decoding: 'async',
      /* ajuda o browser a escolher o tamanho ideal da imagem em cada breakpoint */
      sizes: '(min-width:1200px) 300px, (min-width:768px) 33vw, 50vw'
    });
    img.addEventListener('error', () => {
      if (img.getAttribute('src') !== src) {
        img.setAttribute('src', src);
      }
    });
    img.addEventListener('click', () => {
      if (window.lightbox && typeof lightbox.open === 'function') {
        lightbox.open(fullPaths, i);
      }
    });
    g.appendChild(img);
  });
  return g;
}


  /* Card compacto de produto (grid) — abre o detalhe/compra no modal */
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
    btn.addEventListener('click', () => openPurchaseModal(prod));
    body.appendChild(btn);
    card.appendChild(body);

    media.style.cursor = 'pointer';
    media.addEventListener('click', () => openPurchaseModal(prod));
    return card;
  }

  /* ===== Modal de Compra (Genérico) ===================================== */
  function ensureModal() {
    let modal = document.getElementById('modal-compra');
    if (modal) return modal;

    modal = el('div', { id:'modal-compra', class:'modal', role:'dialog', 'aria-modal':'true' });
    modal.innerHTML = `
      <div class="modal-content">
        <button class="close" data-close aria-label="${t('public.products.lightbox.close', 'Close')}">&times;</button>
        <h3 id="mc-title"></h3>
        <div id="mc-detail" class="mc-detail"></div>
        <form id="mc-form"></form>
      </div>
    `;
    document.body.appendChild(modal);

    /* Fechar clicando fora da caixa ou no X */
    modal.addEventListener('click', (e) => {
      const content = modal.querySelector('.modal-content');
      const clickedOutside = !content.contains(e.target);
      if (e.target.hasAttribute('data-close') || clickedOutside) {
        closePurchaseModal();
      }
    });

    return modal;
  }

  function closePurchaseModal() {
    const modal = document.getElementById('modal-compra');
    if (modal) modal.style.display = 'none';

    // Libera rolagem do fundo
    document.documentElement.classList.remove('modal-open');
    document.body.classList.remove('modal-open');

    // Remove handler de ESC
    window.removeEventListener('keydown', onEscClose);
  }

  function onEscClose(e){
    if (e.key === 'Escape') closePurchaseModal();
  }

  function buildDetail(prod) {
    const detail = el('div', { class:'mc-detail-inner' });
    if (Array.isArray(prod.imagens) && prod.imagens.length) {
      detail.appendChild(buildGallery(prod));
    }
    const info = el('div', { class:'mc-info' });
    if (prod.resumo) info.appendChild(el('p', { class:'mc-summary' }, prod.resumo));
    info.insertAdjacentHTML('beforeend', priceListHTML(prod.preco));
    if (prod.detalhesHTML) {
      const infoBtn = el('button', { type:'button', class:'info-btn' }, t('public.products.info_button', '+ Details'));
      const infoArea = el('div', { class:'mc-details', style:'display:none;margin-top:1rem' }, prod.detalhesHTML);
      infoBtn.addEventListener('click', () => {
        infoArea.style.display = (infoArea.style.display === 'none') ? 'block' : 'none';
      });
      info.appendChild(infoBtn);
      info.appendChild(infoArea);
    }
    detail.appendChild(info);
    return detail;
  }

  function openPurchaseModal(prod) {
    const modal = ensureModal();
    const title = modal.querySelector('#mc-title');
    const detailBox = modal.querySelector('#mc-detail');
    const form  = modal.querySelector('#mc-form');
    title.textContent = prod.nome;
    detailBox.innerHTML = '';
    detailBox.appendChild(buildDetail(prod));
    form.innerHTML = '';

    /* Monta os grupos de opções conforme definição do produto */
    (prod.options || []).forEach(opt => {
      if (opt.type === 'colorPair') {
        const group = el('div', { class:'group' });
        group.appendChild(el('p', {}, `<strong>${opt.title}</strong>`));
        opt.inputs.forEach(inp => {
          group.appendChild(el('p', {}, inp.label + ':'));
          const grid = el('div', { class:'option-grid' });
          if (typeof buildColorSelector === 'function') {
            buildColorSelector(grid, inp.name);
          }
          group.appendChild(grid);
        });
        form.appendChild(group);
      }

      if (opt.type === 'colorSingle') {
        const group = el('div', { class:'group' });
        group.appendChild(el('p', {}, `<strong>${opt.title}</strong>`));
        const grid = el('div', { class:'option-grid' });
        if (typeof buildColorSelector === 'function') {
          buildColorSelector(grid, opt.input.name);
        }
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

    /* Add-on SandSeed */
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

    /* CEP */
    const cepGroup = el('div', { class:'group' });
    cepGroup.appendChild(el('p', {}, t('public.products.shipping_code_label', 'Postal code:')));
    cepGroup.appendChild(el('input', { type:'text', name:'cep', placeholder:t('public.products.shipping_code_placeholder', 'Your postal code'), required:true }));
    form.appendChild(cepGroup);

    /* Cupom */
    const cupomGroup = el('div', { class:'group' });
    cupomGroup.appendChild(el('p', { style:'font-style:italic;color:#ccc' }, t('public.products.coupon_label', 'Coupon (optional):')));
    cupomGroup.appendChild(el('input', { type:'text', name:'cupom', placeholder:t('public.products.coupon_placeholder', 'Coupon') }));
    form.appendChild(cupomGroup);

    /* Ações finais */
    const actions = el('div', { class:'final-actions' });
    const bCart   = el('button', { type:'button', class:'final-btn final-btn-accent' }, t('public.products.actions.add_to_cart', 'Add to cart'));
    const bWhats  = el('button', { type:'button', class:'final-btn' }, t('public.products.actions.whatsapp', 'WhatsApp'));
    const bTele   = el('button',  { type:'button', class:'final-btn' }, t('public.products.actions.telegram', 'Telegram'));
    bCart.addEventListener('click', async () => {
      try {
        const { error, items } = buildCartItems(prod, form);
        if (error) {
          alert(error);
          return;
        }
        if (typeof addCartBatch !== 'function') {
          alert(t('public.products.errors.cart_unavailable', 'Cart unavailable right now.'));
          return;
        }
        await addCartBatch(items);
        closePurchaseModal();
        if (typeof showCartToast === 'function') {
          showCartToast(t('public.products.toast.added_to_cart', 'Product added to cart.'));
        }
      } catch (error) {
        alert(error.message || t('public.products.errors.add_to_cart_failed', 'Could not add the product to the cart.'));
      }
    });
    bWhats.addEventListener('click', () => {
      if (typeof finalizeCompra === 'function') finalizeCompra(form, prod.id, 'whats');
    });
    bTele .addEventListener('click', () => {
      if (typeof finalizeCompra === 'function') finalizeCompra(form, prod.id, 'tele');
    });
    actions.appendChild(bCart);
    actions.appendChild(bWhats);
    actions.appendChild(bTele);
    form.appendChild(actions);

    /* Exibe o modal e bloqueia rolagem do fundo */
    modal.style.display = 'block';
    document.documentElement.classList.add('modal-open');
    document.body.classList.add('modal-open');

    /* Fecha com ESC */
    window.addEventListener('keydown', onEscClose);

    /* Preenche cupom salvo, se houver */
    const saved = localStorage.getItem('cupom');
    if (saved) {
      const cupomInput = form.querySelector('input[name="cupom"]');
      if (cupomInput && !cupomInput.value) cupomInput.value = saved;
    }
  }

  /* ===== Renderização da página de produtos =============================== */
  function renderProductList() {
    const cont = document.getElementById('produtos-container');
    if (cont) {
      cont.innerHTML = '';
      (window.PRODUTOS || []).forEach(prod => {
        cont.appendChild(buildProductCard(prod));
      });
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    if (window.lightbox && typeof lightbox.mount === 'function') {
      lightbox.mount();
    }
    renderProductList();
    if (window.CurrencyDisplay && typeof window.CurrencyDisplay.loadRates === 'function') {
      window.CurrencyDisplay.loadRates().then(renderProductList);
    }
  });
  window.addEventListener('displaycurrencychange', renderProductList);
})();
