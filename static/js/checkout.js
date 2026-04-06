(function () {
  var page = document.getElementById('checkout-page');
  if (!page) return;

  var shippingUrl = page.dataset.shippingUrl;
  var weightGrams = Number(page.dataset.weightGrams || 0);
  var productsTotal = Number(page.dataset.productsTotal || 0);
  var countryInput = document.getElementById('shipping_country');
  var shippingSats = document.getElementById('checkout-shipping-sats');
  var shippingChf = document.getElementById('checkout-shipping-chf');
  var grandTotal = document.getElementById('checkout-grand-total');
  var zoneLabel = document.getElementById('checkout-zone');

  async function updateShipping() {
    var country = (countryInput.value || '').trim().toUpperCase();
    if (!country || country.length < 2) return;

    var response = await fetch(shippingUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN || ''
      },
      body: JSON.stringify({
        country: country,
        weight_grams: weightGrams
      })
    });

    var data = await response.json().catch(function () { return {}; });
    if (!response.ok || !data.ok) return;

    shippingSats.textContent = String(data.shipping_sats || 0);
    shippingChf.textContent = Number(data.shipping_chf || 0).toFixed(2);
    grandTotal.textContent = String(productsTotal + Number(data.shipping_sats || 0));
    zoneLabel.textContent = data.zone || '';
  }

  countryInput.addEventListener('change', updateShipping);
  countryInput.addEventListener('blur', updateShipping);
  if ((countryInput.value || '').trim().length >= 2) {
    updateShipping();
  }
})();
