(function(){
  async function fetchJSON(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = data.error || `HTTP ${response.status}`;
      throw new Error(message);
    }
    return data;
  }

  function setBadge(count) {
    const badge = document.getElementById('cart-badge');
    if (!badge) return;
    const value = Number(count || 0);
    if (value > 0) {
      badge.textContent = String(value);
      badge.style.display = 'inline-flex';
    } else {
      badge.textContent = '0';
      badge.style.display = 'none';
    }
  }

  function ensureToast() {
    let toast = document.getElementById('cart-toast');
    if (toast) return toast;

    toast = document.createElement('div');
    toast.id = 'cart-toast';
    toast.className = 'cart-toast';
    document.body.appendChild(toast);
    return toast;
  }

  function showToast(message, isError = false) {
    const toast = ensureToast();
    toast.textContent = message;
    toast.classList.toggle('is-error', !!isError);
    toast.classList.add('is-visible');

    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => {
      toast.classList.remove('is-visible');
    }, 2400);
  }

  async function updateCartBadge() {
    try {
      const data = await fetchJSON('/api/cart');
      setBadge(data.count || 0);
      return data;
    } catch (_error) {
      return null;
    }
  }

  async function addToCart(productId, priceId, quantity, options) {
    const data = await fetchJSON('/api/cart/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: productId,
        price_id: priceId,
        quantity,
        options: options || {}
      })
    });
    setBadge(data.cart_count || 0);
    return data;
  }

  async function addCartBatch(items) {
    let cartCount = 0;
    for (const item of items) {
      const data = await addToCart(item.productId, item.priceId, item.quantity || 1, item.options || {});
      cartCount = data.cart_count || cartCount;
    }
    setBadge(cartCount);
    return cartCount;
  }

  async function handleCartPageAction(button) {
    const action = button.dataset.action;
    if (!action) return;

    if (action === 'clear-cart') {
      await fetchJSON('/api/cart', { method: 'DELETE' });
      window.location.reload();
      return;
    }

    const item = button.closest('[data-item-id]');
    if (!item) return;

    const itemId = item.dataset.itemId;
    const quantity = Number(item.dataset.quantity || 0);

    if (action === 'qty') {
      const nextQuantity = quantity + Number(button.dataset.delta || 0);
      await fetchJSON(`/api/cart/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: nextQuantity })
      });
      window.location.reload();
      return;
    }

    if (action === 'remove') {
      await fetchJSON(`/api/cart/${itemId}`, { method: 'DELETE' });
      window.location.reload();
    }
  }

  function bindCartPage() {
    const page = document.getElementById('cart-page');
    if (!page) return;

    page.addEventListener('click', async (event) => {
      const button = event.target.closest('[data-action]');
      if (!button) return;

      button.disabled = true;
      try {
        await handleCartPageAction(button);
      } catch (error) {
        button.disabled = false;
        showToast(error.message || 'Não foi possível atualizar o carrinho.', true);
      }
    });
  }

  window.addToCart = addToCart;
  window.addCartBatch = addCartBatch;
  window.updateCartBadge = updateCartBadge;
  window.showCartToast = showToast;

  window.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
    bindCartPage();
  });
})();
