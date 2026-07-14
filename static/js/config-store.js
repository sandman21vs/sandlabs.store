// /js/config-store.js
// Camada de configuração/editável via navegador.
// - Lê/salva overrides no localStorage (`sandlabs-config`)
// - Expõe ConfigStore e aplica overrides em window.CONFIG, window.CONTACTS e window.PRODUTOS

(function(){
  const STORAGE_KEY = 'sandlabs-config';
  const DISPLAY_CURRENCY_KEY = 'sandlabs-display-currency';
  const DISPLAY_CURRENCIES = ['CHF', 'EUR', 'BRL', 'USD'];
  let displayRates = {};
  let displayRatesPromise = null;

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

  function normalizeDisplayCurrency(value){
    const code = String(value || '').trim().toUpperCase();
    return DISPLAY_CURRENCIES.includes(code) ? code : 'CHF';
  }

  function getDisplayCurrency(){
    return normalizeDisplayCurrency(safeGet(DISPLAY_CURRENCY_KEY));
  }

  function setDisplayCurrency(value){
    const currency = normalizeDisplayCurrency(value);
    safeSet(DISPLAY_CURRENCY_KEY, currency);
    window.dispatchEvent(new CustomEvent('displaycurrencychange', {
      detail: { currency }
    }));
    return currency;
  }

  function formatDisplayAmount(amount, currency){
    try {
      return new Intl.NumberFormat(document.documentElement.lang || 'pt', {
        style: 'currency',
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    } catch(e) {
      return `${currency} ${Number(amount).toFixed(2)}`;
    }
  }

  function formatPrice(price){
    const fallback = price && price.valor ? String(price.valor) : '';
    const amountSats = Number(price && price.amountSats);
    const currency = getDisplayCurrency();
    const rate = Number(displayRates[currency]);
    if (!Number.isFinite(amountSats) || amountSats <= 0 || !Number.isFinite(rate) || rate <= 0) {
      return fallback;
    }
    return formatDisplayAmount((amountSats / 100000000) * rate, currency);
  }

  function loadDisplayRates(){
    if (displayRatesPromise) return displayRatesPromise;
    displayRatesPromise = fetch('/api/pricing/rates', {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    })
      .then((response) => {
        if (!response.ok) throw new Error(`Pricing rates unavailable (${response.status})`);
        return response.json();
      })
      .then((payload) => {
        const rates = payload && payload.rates && typeof payload.rates === 'object'
          ? payload.rates
          : {};
        displayRates = Object.fromEntries(
          DISPLAY_CURRENCIES
            .map((currency) => [currency, Number(rates[currency])])
            .filter((entry) => Number.isFinite(entry[1]) && entry[1] > 0)
        );
        return displayRates;
      })
      .catch(() => {
        displayRates = {};
        return displayRates;
      });
    return displayRatesPromise;
  }

  function bindDisplayCurrencySwitcher(){
    const select = document.getElementById('display-currency');
    if (!select) return;
    select.value = getDisplayCurrency();
    select.addEventListener('change', () => setDisplayCurrency(select.value));
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

  window.CurrencyDisplay = {
    currencies: DISPLAY_CURRENCIES.slice(),
    getCurrency: getDisplayCurrency,
    setCurrency: setDisplayCurrency,
    loadRates: loadDisplayRates,
    formatPrice
  };

  // Aplica overrides automaticamente na carga dos scripts
  try { applyOverrides(); }
  catch(e){ console.warn('Falha ao aplicar configurações salvas.', e); }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindDisplayCurrencySwitcher);
  } else {
    bindDisplayCurrencySwitcher();
  }
})();
