// /js/config-page.js
// UI da página config.html para editar contatos e produtos via navegador.

(function(){
  const productList = document.getElementById('product-list');
  const statusEl    = document.getElementById('config-status');
  const whatsInput  = document.getElementById('cfg-whats');
  const teleInput   = document.getElementById('cfg-tele');

  function setStatus(msg, tone='info'){
    if (!statusEl) return;
    statusEl.textContent = msg;
    const color = tone === 'error' ? '#ff6b6b' : '#8cffc2';
    statusEl.style.color = color;
  }

  function createProductEditor(prod){
    const card = document.createElement('article');
    card.className = 'card soft-shadow product-editor';
    card.style.padding = 'var(--space-4)';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.gap = '.75rem';

    const header = document.createElement('div');
    header.style.display = 'flex';
    header.style.alignItems = 'center';
    header.style.justifyContent = 'space-between';
    header.style.gap = '1rem';

    const title = document.createElement('div');
    title.innerHTML = `<strong>${prod.nome || 'Novo produto'}</strong>
      <div class="muted" style="font-size:.85rem;">${prod.id || 'id-obrigatório'}</div>`;

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-ghost';
    removeBtn.textContent = 'Remover';
    removeBtn.addEventListener('click', () => card.remove());

    header.appendChild(title);
    header.appendChild(removeBtn);

    const textarea = document.createElement('textarea');
    textarea.value = JSON.stringify(prod, null, 2);
    textarea.style.width = '100%';
    textarea.style.minHeight = '320px';
    textarea.style.background = '#0f0f0f';
    textarea.style.color = '#f5f5f5';
    textarea.style.border = '1px solid #333';
    textarea.style.borderRadius = '10px';
    textarea.style.padding = '1rem';
    textarea.spellcheck = false;

    card.appendChild(header);
    card.appendChild(textarea);
    return card;
  }

  function renderProducts(list){
    if (!productList) return;
    productList.innerHTML = '';
    if (!Array.isArray(list) || !list.length){
      productList.innerHTML = '<p class="muted">Nenhum produto carregado. Clique em "Adicionar produto".</p>';
      return;
    }
    list.forEach(prod => productList.appendChild(createProductEditor(prod)));
  }

  function readProductsOrFail(){
    if (!productList) return [];
    const parsed = [];
    const editors = productList.querySelectorAll('textarea');
    for (const ta of editors){
      const raw = ta.value.trim();
      if (!raw) continue;
      try {
        const obj = JSON.parse(raw);
        if (!obj.id || !obj.nome){
          throw new Error('Campos obrigatórios: id e nome.');
        }
        parsed.push(obj);
      } catch(e){
        ta.focus();
        throw new Error(`Erro ao ler produto: ${e.message}`);
      }
    }
    return parsed;
  }

  function loadFromStore(){
    if (!window.ConfigStore) return;
    const cfg = ConfigStore.buildConfig();
    if (whatsInput) whatsInput.value = cfg.contacts?.whatsapp || '';
    if (teleInput)  teleInput.value  = cfg.contacts?.telegram || '';
    renderProducts(cfg.products);
  }

  function saveAll(){
    if (!window.ConfigStore) return;
    let products;
    try {
      products = readProductsOrFail();
    } catch(e){
      setStatus(e.message, 'error');
      return;
    }

    const contacts = {
      whatsapp: (whatsInput?.value || '').trim(),
      telegram: (teleInput?.value  || '').trim()
    };

    const colors = ConfigStore.buildConfig().colors || ConfigStore.defaults.colors();
    ConfigStore.save({ contacts, products, colors });
    ConfigStore.applyOverrides();
    setStatus('Config salva no navegador (localStorage).', 'ok');
  }

  function exportProdutos(){
    let products;
    try {
      products = readProductsOrFail();
    } catch(e){
      setStatus(e.message, 'error');
      return;
    }
    const content = ConfigStore.exportProdutosJS(products);
    const blob = new Blob([content], { type:'application/javascript' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'produtos-data.js';
    a.click();
    URL.revokeObjectURL(url);
    setStatus('Arquivo produtos-data.js exportado (baixe e substitua no servidor/docker).', 'ok');
  }

  function resetAll(){
    if (!window.ConfigStore) return;
    if (!confirm('Remover overrides salvos e voltar ao arquivo original?')) return;
    ConfigStore.reset();
    ConfigStore.applyOverrides();
    loadFromStore();
    setStatus('Overrides apagados. Dados originais do arquivo foram recarregados.', 'ok');
  }

  function addTemplate(){
    if (!productList) return;
    const template = {
      id: `produto-${Date.now()}`,
      nome: 'Novo produto',
      imagens: ['images/produto.png'],
      resumo: 'Descrição curta do produto.',
      preco: [{ label: 'Item', valor: 'R$ 0,00' }],
      detalhesHTML: '<p>Detalhes completos do produto.</p>',
      options: [],
      allowAddOnSeed: false,
      buyButtonText: 'Comprar agora',
      badge: null
    };
    const editor = createProductEditor(template);
    productList.prepend(editor);
    editor.querySelector('textarea')?.focus();
  }

  function reloadFromFile(){
    renderProducts(ConfigStore.defaults.products());
    setStatus('Produtos recarregados a partir do arquivo original.', 'ok');
  }

  function bindEvents(){
    document.getElementById('btn-save')?.addEventListener('click', saveAll);
    document.getElementById('btn-export')?.addEventListener('click', exportProdutos);
    document.getElementById('btn-reset')?.addEventListener('click', resetAll);
    document.getElementById('btn-add')?.addEventListener('click', addTemplate);
    document.getElementById('btn-refresh')?.addEventListener('click', reloadFromFile);
  }

  document.addEventListener('DOMContentLoaded', () => {
    loadFromStore();
    bindEvents();
  });
})();
