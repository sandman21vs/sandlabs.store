"""Tests for checkout routes — Phase 6: shipping calculation endpoint."""

from db import get_db
from models.model_cart import add_to_cart, get_cart_count
from unittest.mock import patch


def _login_session(client, user_id=1, display_name="Test User", is_admin=False):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["display_name"] = display_name
        sess["is_admin"] = is_admin
        sess["cart_session"] = sess.get("cart_session", "test-session")


def _insert_order(user_id, price_id, amount_sats, invoice_hash="invoice123", bolt11="lnbc1testinvoice"):
    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO orders (
                user_id, session_id, status, total_sats, shipping_sats,
                invoice_hash, bolt11, shipping_name, shipping_address,
                shipping_postal_code, shipping_country, created_at, updated_at
            ) VALUES (?, 'test-session', 'pending', ?, 0, ?, ?, 'Buyer', 'Street 1', '8000', 'CH', datetime('now'), datetime('now'))
            """,
            (user_id, amount_sats, invoice_hash, bolt11),
        )
        order_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO order_items (order_id, product_id, price_id, quantity, unit_sats, options_json)
            VALUES (?, 'test-product', ?, 1, ?, '{}')
            """,
            (order_id, price_id, amount_sats),
        )
        conn.commit()
        return order_id
    finally:
        conn.close()


class TestShippingCalculateAPI:
    """POST /api/shipping/calculate"""

    def _post(self, client, payload, csrf_headers):
        return client.post("/api/shipping/calculate", json=payload, headers=csrf_headers)

    def test_ch_returns_correct_zone_and_chf(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = self._post(client, {"country": "CH", "weight_grams": 500}, csrf_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["zone"] == "CH"
        assert data["shipping_chf"] == 7.00
        assert data["shipping_sats"] == 8500

    def test_eu_country_returns_eu_zone(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=24000):
            resp = self._post(client, {"country": "DE", "weight_grams": 1000}, csrf_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["zone"] == "EU"
        assert data["shipping_chf"] == 20.00

    def test_world_country_returns_world_zone(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=35000):
            resp = self._post(client, {"country": "BR", "weight_grams": 200}, csrf_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["zone"] == "WORLD"
        assert data["shipping_chf"] == 30.00

    def test_missing_country_returns_400(self, client, csrf_headers):
        resp = self._post(client, {"weight_grams": 500}, csrf_headers)
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_missing_weight_returns_400(self, client, csrf_headers):
        resp = self._post(client, {"country": "CH"}, csrf_headers)
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_empty_body_returns_400(self, client, csrf_headers):
        resp = self._post(client, {}, csrf_headers)
        assert resp.status_code == 400

    def test_negative_weight_returns_400(self, client, csrf_headers):
        resp = self._post(client, {"country": "CH", "weight_grams": -100}, csrf_headers)
        assert resp.status_code == 400

    def test_invalid_weight_type_returns_400(self, client, csrf_headers):
        resp = self._post(client, {"country": "CH", "weight_grams": "heavy"}, csrf_headers)
        assert resp.status_code == 400

    def test_weight_as_string_number_is_accepted(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = self._post(client, {"country": "CH", "weight_grams": "500"}, csrf_headers)
        assert resp.status_code == 200

    def test_lowercase_country_code_works(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = self._post(client, {"country": "ch", "weight_grams": 500}, csrf_headers)
        assert resp.status_code == 200
        assert resp.get_json()["zone"] == "CH"

    def test_zero_weight_is_valid(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = self._post(client, {"country": "CH", "weight_grams": 0}, csrf_headers)
        assert resp.status_code == 200

    def test_sats_zero_when_rate_unavailable(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=0):
            resp = self._post(client, {"country": "CH", "weight_grams": 500}, csrf_headers)
        assert resp.status_code == 200
        assert resp.get_json()["shipping_sats"] == 0

    def test_heavy_package_ch(self, client, csrf_headers):
        with patch("routes.routes_checkout.chf_to_sats", return_value=20000):
            resp = self._post(client, {"country": "CH", "weight_grams": 15000}, csrf_headers)
        assert resp.status_code == 200
        assert resp.get_json()["shipping_chf"] == 16.00


class TestCheckoutFlow:
    def test_checkout_requires_auth(self, client):
        resp = client.get("/checkout")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_checkout_redirects_to_cart_when_empty(self, client, test_user):
        _login_session(client, user_id=test_user)
        resp = client.get("/checkout")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/carrinho")

    def test_checkout_renders_with_cart_items(self, client, test_user, seeded_product):
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 2, {}, user_id=test_user)
        with patch("routes.routes_checkout.calculate_shipping_chf", return_value=7.0), \
             patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = client.get("/checkout")
        html = resp.data.decode()
        assert resp.status_code == 200
        assert "Checkout" in html
        assert "Test Product" in html

    def test_create_order_creates_invoice_and_clears_cart(self, client, test_user, seeded_product, csrf_headers):
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 1, {}, user_id=test_user)

        with patch("routes.routes_checkout.calculate_shipping_chf", return_value=7.0), \
             patch("routes.routes_checkout.chf_to_sats", return_value=8500), \
             patch("routes.routes_checkout.create_invoice", return_value={"hash": "hash123", "text": "lnbc1paid"}):
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer",
                    "address": "Street 1",
                    "postal_code": "8000",
                    "country": "CH",
                },
                headers=csrf_headers,
                follow_redirects=False,
            )

        assert resp.status_code == 302
        assert "/checkout/payment/" in resp.headers["Location"]

        conn = get_db()
        try:
            order = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (test_user,)).fetchone()
            items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],)).fetchall()
        finally:
            conn.close()

        assert order is not None
        assert order["invoice_hash"] == "hash123"
        assert order["bolt11"] == "lnbc1paid"
        assert int(order["shipping_sats"]) == 8500
        assert len(items) == 1
        assert get_cart_count("test-session", test_user) == 0

    def test_create_order_rejects_items_without_sats_price(self, client, test_user, csrf_headers, tmp_db):
        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO products (id, name, summary, details_html, weight_grams, buy_button_text, active)
                VALUES ('zero-prod', 'Zero Product', 'test', '', 100, 'Comprar', 1)
                """
            )
            conn.execute(
                """
                INSERT INTO product_prices (product_id, label, amount_sats, display_text, sort_order)
                VALUES ('zero-prod', 'Base', 0, 'R$ 10', 0)
                """
            )
            conn.commit()
            price = conn.execute("SELECT id FROM product_prices WHERE product_id='zero-prod'").fetchone()
        finally:
            conn.close()

        _login_session(client, user_id=test_user)
        add_to_cart("test-session", "zero-prod", price["id"], 1, {}, user_id=test_user)

        with patch("routes.routes_checkout.calculate_shipping_chf", return_value=7.0), \
             patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer",
                    "address": "Street 1",
                    "postal_code": "8000",
                    "country": "CH",
                },
                headers=csrf_headers,
            )
        assert resp.status_code == 400
        assert b"sem preco em sats" in resp.data.lower()

    def test_payment_page_renders_for_owner(self, client, test_user, seeded_product):
        _login_session(client, user_id=test_user)
        order_id = _insert_order(
            test_user,
            seeded_product["prices"][0]["id"],
            seeded_product["prices"][0]["amount_sats"],
        )
        resp = client.get(f"/checkout/payment/{order_id}")
        assert resp.status_code == 200
        assert b"BOLT11" in resp.data

    def test_check_payment_confirms_order(self, client, test_user, seeded_product):
        _login_session(client, user_id=test_user)
        order_id = _insert_order(
            test_user,
            seeded_product["prices"][0]["id"],
            seeded_product["prices"][0]["amount_sats"],
            invoice_hash="hash-to-check",
        )
        with patch("routes.routes_checkout.check_invoice", return_value={"received": 1000}):
            resp = client.get(f"/api/checkout/check-payment/{order_id}")
        assert resp.status_code == 200
        assert resp.get_json()["paid"] is True

        conn = get_db()
        try:
            row = conn.execute("SELECT status, payment_confirmed_at FROM orders WHERE id = ?", (order_id,)).fetchone()
        finally:
            conn.close()
        assert row["status"] == "paid"
        assert row["payment_confirmed_at"] is not None

    def test_invoice_qr_returns_png(self, client, test_user, seeded_product):
        _login_session(client, user_id=test_user)
        order_id = _insert_order(
            test_user,
            seeded_product["prices"][0]["id"],
            seeded_product["prices"][0]["amount_sats"],
        )
        resp = client.get(f"/checkout/payment/{order_id}")
        assert resp.status_code == 200

        qr_resp = client.get("/checkout/invoice-qr?bolt11=lnbc1testinvoice")
        assert qr_resp.status_code == 200
        assert qr_resp.headers["Content-Type"] == "image/png"

    def test_coinos_webhook_confirms_order_without_csrf(self, client, seeded_product, monkeypatch):
        monkeypatch.setattr("routes.routes_checkout.config.COINOS_WEBHOOK_SECRET", "secret", raising=False)
        order_id = _insert_order(
            None,
            seeded_product["prices"][0]["id"],
            seeded_product["prices"][0]["amount_sats"],
            invoice_hash="webhookhash",
        )
        resp = client.post(
            "/checkout/webhook/coinos",
            json={"secret": "secret", "hash": "webhookhash", "received": 500},
        )
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

        conn = get_db()
        try:
            row = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        finally:
            conn.close()
        assert row["status"] == "paid"
