// /js/config-store.js
// Camada de configuração/editável via navegador.
// - Lê/salva overrides no localStorage (`sandlabs-config`)
// - Expõe ConfigStore e aplica overrides em window.CONFIG, window.CONTACTS e window.PRODUTOS

(function(){
  const STORAGE_KEY = 'sandlabs-config';

  function safeParse(str){
    try { return JSON.parse(str); }
    catch(e){ return null; }
  }

  function safeGet(key){
    try { return localStorage.getItem(key); }
    catch(e){ return null; }
  }

  function safeSet(key, val){
    try { localStorage.setItem(key, val); }
    catch(e){ console.warn('Não foi possível salvar no localStorage.', e); }
  }

  function safeRemove(key){
    try { localStorage.removeItem(key); }
    catch(e){ console.warn('Não foi possível limpar o localStorage.', e); }
  }

  const BASE_CONFIG = JSON.parse(JSON.stringify(window.CONFIG || {}));
  const BASE_PRODUCTS = Array.isArray(window.PRODUTOS)
    ? JSON.parse(JSON.stringify(window.PRODUTOS))
    : [];

  function getDefaultContacts(){
    const cfg = BASE_CONFIG || {};
    const contacts = cfg.contacts || {};
    return {
      whatsapp: contacts.whatsapp || cfg.whatsappNumber || '41779786651',
      telegram: contacts.telegram  || cfg.telegramUsername || 'SandLabs_21'
    };
  }

  function getDefaultColors(){
    const cfg = BASE_CONFIG || {};
    const colors = Array.isArray(cfg.colors) ? cfg.colors : [];
    return JSON.parse(JSON.stringify(colors));
  }

  function getDefaultProducts(){
    return JSON.parse(JSON.stringify(BASE_PRODUCTS));
  }

  function loadRaw(){
    return safeParse(safeGet(STORAGE_KEY)) || {};
  }

  function buildConfig(){
    const stored = loadRaw();
    const contacts = stored.contacts || getDefaultContacts();
    const products = Array.isArray(stored.products) ? stored.products : getDefaultProducts();
    const colors   = Array.isArray(stored.colors)   ? stored.colors   : getDefaultColors();
    return {
      contacts: JSON.parse(JSON.stringify(contacts)),
      products: JSON.parse(JSON.stringify(products)),
      colors:   JSON.parse(JSON.stringify(colors))
    };
  }

  function applyOverrides(){
    const cfg = buildConfig();

    // Contatos e cores
    const base = window.CONFIG || {};
    window.CONFIG = {
      ...base,
      contacts: {
        whatsapp: cfg.contacts.whatsapp || (base.contacts && base.contacts.whatsapp),
        telegram: cfg.contacts.telegram || (base.contacts && base.contacts.telegram)
      },
      whatsappNumber: cfg.contacts.whatsapp || base.whatsappNumber,
      telegramUsername: cfg.contacts.telegram || base.telegramUsername,
      colors: Array.isArray(cfg.colors) && cfg.colors.length ? cfg.colors : getDefaultColors()
    };

    // Exposição direta
    window.CONTACTS = window.CONFIG.contacts;
    window.PRODUTOS = cfg.products;

    return cfg;
  }

  function save(cfg){
    safeSet(STORAGE_KEY, JSON.stringify(cfg));
    return cfg;
  }

  function reset(){
    safeRemove(STORAGE_KEY);
  }

  function exportProdutosJS(products){
    const arr = JSON.stringify(products, null, 2);
    return `// Gerado via config.html\nwindow.PRODUTOS = ${arr};\n`;
  }

  window.ConfigStore = {
    key: STORAGE_KEY,
    loadRaw,
    buildConfig,
    applyOverrides,
    save,
    reset,
    exportProdutosJS,
    defaults: {
      contacts: getDefaultContacts,
      colors: getDefaultColors,
      products: getDefaultProducts
    }
  };

  // Aplica overrides automaticamente na carga dos scripts
  try { applyOverrides(); }
  catch(e){ console.warn('Falha ao aplicar configurações salvas.', e); }
})();
