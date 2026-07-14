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
  var optionsBox = document.getElementById('checkout-shipping-options');
  var carrierInput = document.getElementById('shipping_carrier');
  var serviceInput = document.getElementById('shipping_service');

  // Coupon elements
  var couponBox = document.getElementById('checkout-coupon');
  var couponInput = document.getElementById('coupon-code');
  var couponApply = document.getElementById('coupon-apply');
  var couponFeedback = document.getElementById('coupon-feedback');
  var discountRow = document.getElementById('checkout-discount-row');
  var discountSatsEl = document.getElementById('checkout-discount-sats');

  var state = {
    shippingSats: Number(shippingSats ? shippingSats.textContent : 0) || 0,
    discountSats: 0
  };

  function recomputeTotal() {
    var discounted = Math.max(0, productsTotal - state.discountSats);
    grandTotal.textContent = String(discounted + state.shippingSats);
    if (discountRow) {
      discountRow.hidden = state.discountSats <= 0;
      if (discountSatsEl) discountSatsEl.textContent = String(state.discountSats);
    }
  }

  function applyOption(sats, chf, carrier, service) {
    state.shippingSats = Number(sats || 0);
    shippingSats.textContent = String(state.shippingSats);
    shippingChf.textContent = Number(chf || 0).toFixed(2);
    if (carrierInput) carrierInput.value = carrier || '';
    if (serviceInput) serviceInput.value = service || '';
    recomputeTotal();
  }

  function renderOptions(options) {
    if (!optionsBox) return;
    optionsBox.querySelectorAll('.shipping-option').forEach(function (el) { el.remove(); });
    options.forEach(function (opt, i) {
      var label = document.createElement('label');
      label.className = 'shipping-option';
      var radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = 'shipping_choice';
      radio.dataset.carrier = opt.carrier;
      radio.dataset.service = opt.service;
      radio.dataset.sats = opt.price_sats;
      radio.dataset.chf = Number(opt.price_chf).toFixed(2);
      if (i === 0) radio.checked = true;
      radio.addEventListener('change', function () {
        applyOption(opt.price_sats, opt.price_chf, opt.carrier, opt.service);
      });
      var span = document.createElement('span');
      span.textContent = (opt.carrier || '').toUpperCase() + ' · ' + opt.service +
        ' — ' + opt.price_sats + ' sats (' + Number(opt.price_chf).toFixed(2) + ' CHF)';
      label.appendChild(radio);
      label.appendChild(span);
      optionsBox.appendChild(label);
    });
    optionsBox.hidden = options.length <= 1;
  }

  async function updateShipping() {
    var country = (countryInput.value || '').trim().toUpperCase();
    if (!country || country.length < 2) return;

    var response = await fetch(shippingUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN || ''
      },
      body: JSON.stringify({ country: country, weight_grams: weightGrams })
    });

    var data = await response.json().catch(function () { return {}; });
    if (!response.ok || !data.ok) return;

    zoneLabel.textContent = data.zone || '';
    var options = data.options || [];
    if (options.length) {
      renderOptions(options);
      var first = options[0];
      applyOption(first.price_sats, first.price_chf, first.carrier, first.service);
    } else {
      applyOption(data.shipping_sats, data.shipping_chf, '', '');
    }
  }

  function showCouponFeedback(message, ok) {
    if (!couponFeedback) return;
    couponFeedback.textContent = message || '';
    couponFeedback.hidden = !message;
    couponFeedback.classList.toggle('is-error', !ok);
    couponFeedback.classList.toggle('is-ok', !!ok && !!message);
  }

  async function applyCoupon() {
    if (!couponBox || !couponInput) return;
    var code = (couponInput.value || '').trim();
    if (!code) {
      state.discountSats = 0;
      showCouponFeedback('', true);
      recomputeTotal();
      return;
    }
    var response = await fetch(couponBox.dataset.applyUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN || ''
      },
      body: JSON.stringify({ code: code })
    });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok || !data.ok) {
      state.discountSats = 0;
      showCouponFeedback((data && data.error) || 'Invalid coupon.', false);
      recomputeTotal();
      return;
    }
    state.discountSats = Number(data.discount_sats || 0);
    showCouponFeedback(window.t ? window.t('commerce.checkout.coupon.applied', 'Coupon applied') : 'Coupon applied', true);
    recomputeTotal();
  }

  if (couponApply) couponApply.addEventListener('click', applyCoupon);

  if (optionsBox) {
    optionsBox.addEventListener('change', function (e) {
      var r = e.target;
      if (r && r.name === 'shipping_choice') {
        applyOption(r.dataset.sats, r.dataset.chf, r.dataset.carrier, r.dataset.service);
      }
    });
  }

  countryInput.addEventListener('change', updateShipping);
  countryInput.addEventListener('blur', updateShipping);
  if ((countryInput.value || '').trim().length >= 2) {
    updateShipping();
  }

  // A coupon may already be present (filled from localStorage by cupom.js).
  if (couponInput && (couponInput.value || '').trim()) {
    applyCoupon();
  }
})();
