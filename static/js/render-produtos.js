// /js/render-produtos.js — ARQUIVO COMPLETO
(function(){
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

  /* Lista de preços HTML */
  function priceListHTML(precos) {
    if (!Array.isArray(precos)) return '';
    return precos.map(p => `<p><strong>${p.label}:</strong> ${p.valor}</p>`).join('');
  }

  /* Galeria por produto */
function buildGallery(prod) {
  const g = el('div', { class:'galeria' });
  const fullPaths = prod.imagens.map(src => src);
  prod.imagens.forEach((src, i) => {
    const img = el('img', {
      src,
      alt: `${prod.nome} ${i + 1}`,
      loading: 'lazy',
      decoding: 'async',
      /* ajuda o browser a escolher o tamanho ideal da imagem em cada breakpoint */
      sizes: '(min-width:1200px) 300px, (min-width:768px) 33vw, 50vw'
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

  /* Caixa de descrição + botão comprar */
  function buildDescBox(prod) {
    const box = el('div', { class:'desc-box' });
    box.appendChild(el('h3', {}, `Informações sobre ${prod.nome}`));
    box.appendChild(el('p', {}, prod.resumo));
    box.insertAdjacentHTML('beforeend', priceListHTML(prod.preco));

    const infoBtn = el('button', { class:'info-btn' }, '+ Informações');
    const infoArea = el('div', { style:'display:none;margin-top:1rem' }, prod.detalhesHTML || '');
    infoBtn.addEventListener('click', () => {
      infoArea.style.display = (infoArea.style.display === 'none') ? 'block' : 'none';
    });

    const buyBtn = el('button', { class:'buy-btn' }, prod.buyButtonText || `Comprar ${prod.nome}`);
    buyBtn.addEventListener('click', () => openPurchaseModal(prod));

    box.appendChild(infoBtn);
    box.appendChild(infoArea);
    box.appendChild(buyBtn);
    return box;
  }

  /* Seção completa do produto */
  function sectionProduto(prod) {
    const sec = el('section', { class:'produto-section' });
    sec.appendChild(el('h3', {}, prod.nome));
    sec.appendChild(buildGallery(prod));
    sec.appendChild(buildDescBox(prod));
    return sec;
  }

  /* ===== Modal de Compra (Genérico) ===================================== */
  function ensureModal() {
    let modal = document.getElementById('modal-compra');
    if (modal) return modal;

    modal = el('div', { id:'modal-compra', class:'modal', role:'dialog', 'aria-modal':'true' });
    modal.innerHTML = `
      <div class="modal-content">
        <button class="close" data-close aria-label="Fechar">&times;</button>
        <img src="images/cor_exemplo.png" class="demo" alt="Demonstração">
        <h3 id="mc-title"></h3>
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

  function openPurchaseModal(prod) {
    const modal = ensureModal();
    const title = modal.querySelector('#mc-title');
    const form  = modal.querySelector('#mc-form');
    title.textContent = `Opções para ${prod.nome}`;
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
        group.appendChild(el('p', {}, `<strong>Selecione:</strong>`));

        const labelKit = el('label', {}, `
          <input type="radio" name="seedPack" value="kit" checked> Kit 5 un – 5 000 sats
        `);
        const labelSingle = el('label', {}, `
          <input type="radio" name="seedPack" value="single"> Placa avulsa – 2 000 sats
        `);
        group.appendChild(labelKit);
        group.appendChild(el('br'));
        group.appendChild(labelSingle);

        const qtyBox = el('div', { id:'seedQtyBox', style:'display:none;margin-top:8px' });
        qtyBox.innerHTML = `
          <p>Quantidade de placas:</p>
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
          Adicionar <strong>Kit SandSeed (5 placas)</strong>
        </label>
      `;
      form.appendChild(groupAddon);
    }

    /* CEP */
    const cepGroup = el('div', { class:'group' });
    cepGroup.appendChild(el('p', {}, 'CEP:'));
    cepGroup.appendChild(el('input', { type:'text', name:'cep', placeholder:'Seu CEP', required:true }));
    form.appendChild(cepGroup);

    /* Cupom */
    const cupomGroup = el('div', { class:'group' });
    cupomGroup.appendChild(el('p', { style:'font-style:italic;color:#ccc' }, 'Cupom (opcional):'));
    cupomGroup.appendChild(el('input', { type:'text', name:'cupom', placeholder:'Cupom' }));
    form.appendChild(cupomGroup);

    /* Ações finais */
    const actions = el('div', { class:'final-actions' });
    const bWhats  = el('button', { type:'button', class:'final-btn' }, 'WhatsApp');
    const bTele   = el('button',  { type:'button', class:'final-btn' }, 'Telegram');
    bWhats.addEventListener('click', () => {
      if (typeof finalizeCompra === 'function') finalizeCompra(form, prod.id, 'whats');
    });
    bTele .addEventListener('click', () => {
      if (typeof finalizeCompra === 'function') finalizeCompra(form, prod.id, 'tele');
    });
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
  window.addEventListener('DOMContentLoaded', () => {
    if (window.lightbox && typeof lightbox.mount === 'function') {
      lightbox.mount();
    }

    const cont = document.getElementById('produtos-container');
    if (cont) {
      cont.innerHTML = '';
      (window.PRODUTOS || []).forEach(prod => {
        cont.appendChild(sectionProduto(prod));
      });
    }
  });
})();
