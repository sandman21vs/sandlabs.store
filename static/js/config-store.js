// /js/config-store.js
// Display-currency switcher (Fase G). The legacy browser store-editor that
// overrode window.PRODUTOS/CONFIG from localStorage was removed — product,
// contact and colour data now come from the backend (server-rendered).

(function(){
  const DISPLAY_CURRENCY_KEY = 'sandlabs-display-currency';
  const DISPLAY_CURRENCIES = ['CHF', 'EUR', 'BRL', 'USD'];
  let displayRates = {};
  let displayRatesPromise = null;

  function safeGet(key){
    try { return localStorage.getItem(key); }
    catch(e){ return null; }
  }

  function safeSet(key, val){
    try { localStorage.setItem(key, val); }
    catch(e){ console.warn('Não foi possível salvar no localStorage.', e); }
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

  window.CurrencyDisplay = {
    currencies: DISPLAY_CURRENCIES.slice(),
    getCurrency: getDisplayCurrency,
    setCurrency: setDisplayCurrency,
    loadRates: loadDisplayRates,
    formatPrice
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindDisplayCurrencySwitcher);
  } else {
    bindDisplayCurrencySwitcher();
  }
})();
