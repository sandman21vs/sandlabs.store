"""Tests for checkout routes — Phase 6: shipping calculation endpoint."""

import json

from db import get_db
from models.model_cart import add_to_cart, get_cart_count
from models.model_config import set_config
from models.model_orders import get_order
from services.service_security import encrypt_value
from unittest.mock import patch


def _login_session(client, user_id=1, display_name="Test User", is_admin=False):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["display_name"] = display_name
        sess["is_admin"] = is_admin
        sess["cart_session"] = sess.get("cart_session", "test-session")


def _insert_order(
    user_id,
    price_id,
    amount_sats,
    invoice_hash="invoice123",
    bolt11="lnbc1testinvoice",
    access_token=None,
    session_id="test-session",
):
    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO orders (
                user_id, session_id, status, total_sats, shipping_sats,
                invoice_hash, bolt11, access_token, created_at, updated_at
            ) VALUES (?, ?, 'pending', ?, 0, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                user_id,
                session_id,
                amount_sats,
                invoice_hash,
                bolt11,
                encrypt_value(access_token),
            ),
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
        assert data["shipping_chf"] == 9.00
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
        assert resp.get_json()["shipping_chf"] == 21.00


class TestCheckoutFlow:
    def test_checkout_allows_guest_with_cart(self, client, seeded_product):
        with client.session_transaction() as sess:
            sess["cart_session"] = "guest-session"
        add_to_cart(
            "guest-session",
            seeded_product["id"],
            seeded_product["prices"][0]["id"],
            1,
            {},
            user_id=None,
        )
        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = client.get("/checkout")

        assert resp.status_code == 200
        assert b"token de acesso" in resp.data.lower()
        assert resp.headers["Cache-Control"] == "private, no-store"

    def test_empty_guest_checkout_redirects_to_cart(self, client):
        resp = client.get("/checkout")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/carrinho")

    def test_checkout_redirects_to_cart_when_empty(self, client, test_user):
        _login_session(client, user_id=test_user)
        resp = client.get("/checkout")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/carrinho")

    def test_checkout_renders_with_cart_items(self, client, test_user, seeded_product):
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 2, {}, user_id=test_user)
        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = client.get("/checkout")
        html = resp.data.decode()
        assert resp.status_code == 200
        assert "Checkout" in html
        assert "Test Product" in html

    def test_create_order_creates_invoice_and_clears_cart(self, client, test_user, seeded_product, csrf_headers):
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 1, {}, user_id=test_user)

        with patch("routes.routes_checkout.chf_to_sats", return_value=8500), \
             patch("routes.routes_checkout.create_invoice", return_value={"hash": "hash123", "text": "lnbc1paid"}):
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer",
                    "street": "Bahnhofstrasse",
                    "house_number": "12A",
                    "address_extra": "Campainha azul",
                    "city": "Zurich",
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
        assert order["shipping_name_enc"]
        assert order["shipping_street_enc"]
        assert order["shipping_house_number_enc"]
        assert order["shipping_address_extra_enc"]
        assert order["shipping_city_enc"]
        assert order["shipping_postal_code_enc"]
        assert order["shipping_country_enc"]
        assert "Bahnhofstrasse" not in order["shipping_street_enc"]
        assert "Campainha azul" not in order["shipping_address_extra_enc"]
        assert len(items) == 1
        assert get_cart_count("test-session", test_user) == 0
        assert order["access_token"] is None

    def test_guest_create_order_sets_token_and_keeps_session_access(
        self, client, seeded_product, csrf_headers
    ):
        with client.session_transaction() as sess:
            sess["cart_session"] = "guest-session"
        add_to_cart(
            "guest-session",
            seeded_product["id"],
            seeded_product["prices"][0]["id"],
            1,
            {},
            user_id=None,
        )

        with patch("routes.routes_checkout.chf_to_sats", return_value=8500), patch(
            "routes.routes_checkout.create_invoice",
            return_value={"hash": "guest-hash", "text": "lnbc1guest"},
        ):
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Guest Buyer",
                    "street": "Guest Street",
                    "house_number": "1",
                    "city": "Zurich",
                    "postal_code": "8000",
                    "country": "CH",
                },
                headers=csrf_headers,
                follow_redirects=False,
            )

        assert resp.status_code == 302
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE invoice_hash = 'guest-hash'"
            ).fetchone()
        finally:
            conn.close()

        assert order["user_id"] is None
        assert order["session_id"] == "guest-session"
        assert order["access_token"].startswith("gAAAA")
        normalized_order = get_order(order["id"])
        assert len(normalized_order["access_token"]) >= 40
        assert get_cart_count("guest-session", None) == 0

        payment = client.get(resp.headers["Location"])
        assert payment.status_code == 200
        assert normalized_order["access_token"].encode() in payment.data
        assert payment.headers["Cache-Control"] == "private, no-store"

    def test_create_order_onchain_stores_address_and_method(self, client, test_user, seeded_product, csrf_headers):
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 1, {}, user_id=test_user)
        set_config("coinos_enabled", "1")
        set_config("coinos_onchain", "1")

        with patch("routes.routes_checkout.chf_to_sats", return_value=0), \
             patch("routes.routes_checkout.create_invoice", return_value={"hash": "onchainhash", "text": "bc1qaddress"}) as mock_inv:
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer", "street": "Street", "house_number": "1",
                    "city": "Zurich", "postal_code": "8000", "country": "CH",
                    "payment_method": "onchain",
                },
                headers=csrf_headers,
                follow_redirects=False,
            )

        assert resp.status_code == 302
        # create_invoice called with the onchain method.
        assert mock_inv.call_args.kwargs.get("invoice_type") == "onchain"

        conn = get_db()
        try:
            order = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (test_user,)).fetchone()
        finally:
            conn.close()
        assert order["payment_method"] == "onchain"
        assert order["invoice_type"] == "bitcoin"
        assert order["btc_address"] == "bc1qaddress"
        assert order["bolt11"] is None
        assert order["invoice_hash"] == "onchainhash"

    def test_create_order_rejects_items_without_available_sats_conversion(self, client, test_user, csrf_headers, tmp_db, monkeypatch):
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
                INSERT INTO product_prices (
                    product_id, label, amount_sats, pricing_mode, currency_code, amount_fiat, display_text, sort_order
                )
                VALUES ('zero-prod', 'Base', 0, 'fiat', 'CHF', '10.00', 'CHF 10.00', 0)
                """
            )
            conn.commit()
            price = conn.execute("SELECT id FROM product_prices WHERE product_id='zero-prod'").fetchone()
        finally:
            conn.close()

        monkeypatch.setattr("services.service_pricing.fiat_to_sats", lambda amount, currency: 0)
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", "zero-prod", price["id"], 1, {}, user_id=test_user)

        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer",
                    "street": "Street",
                    "house_number": "1",
                    "city": "Zurich",
                    "postal_code": "8000",
                    "country": "CH",
                },
                headers=csrf_headers,
            )
        assert resp.status_code == 400
        assert b"sem conversao disponivel para sats" in resp.data.lower()

    def test_create_order_supports_dynamic_chf_pricing(self, client, test_user, csrf_headers, tmp_db):
        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO products (id, name, summary, details_html, weight_grams, buy_button_text, active)
                VALUES ('chf-prod', 'CHF Product', 'test', '', 100, 'Comprar', 1)
                """
            )
            conn.execute(
                """
                INSERT INTO product_prices (
                    product_id, label, amount_sats, pricing_mode, currency_code, amount_fiat, display_text, sort_order
                )
                VALUES ('chf-prod', 'Base', 0, 'fiat', 'CHF', '25.00', 'CHF 25.00', 0)
                """
            )
            conn.commit()
            price = conn.execute("SELECT id FROM product_prices WHERE product_id='chf-prod'").fetchone()
        finally:
            conn.close()

        _login_session(client, user_id=test_user)
        add_to_cart("test-session", "chf-prod", price["id"], 2, {}, user_id=test_user)

        with patch("services.service_pricing.fiat_to_sats", return_value=2500), \
             patch("routes.routes_checkout.chf_to_sats", return_value=8500), \
             patch("routes.routes_checkout.create_invoice", return_value={"hash": "hashchf", "text": "lnbc1chf"}):
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer",
                    "street": "Street",
                    "house_number": "1",
                    "city": "Zurich",
                    "postal_code": "8000",
                    "country": "CH",
                },
                headers=csrf_headers,
                follow_redirects=False,
            )

        assert resp.status_code == 302
        conn = get_db()
        try:
            order = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (test_user,)).fetchone()
        finally:
            conn.close()
        assert order["total_sats"] == 5000

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

    def test_account_order_routes_reject_anonymous_user(self, client, test_user, seeded_product):
        order_id = _insert_order(
            test_user,
            seeded_product["prices"][0]["id"],
            seeded_product["prices"][0]["amount_sats"],
        )

        assert client.get(f"/checkout/payment/{order_id}").status_code == 404
        assert client.get(f"/api/checkout/check-payment/{order_id}").status_code == 404
        assert client.get(f"/checkout/payment/{order_id}/qr").status_code == 404
        assert client.get(f"/orders/{order_id}").status_code == 404
        assert client.get(f"/orders/{order_id}/receipt.pdf").status_code == 404

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

        qr_resp = client.get(f"/checkout/payment/{order_id}/qr")
        assert qr_resp.status_code == 200
        assert qr_resp.headers["Content-Type"] == "image/png"
        assert qr_resp.headers["Cache-Control"] == "private, no-store"

    def test_guest_order_routes_require_session_or_valid_lookup_token(
        self, client, seeded_product, csrf_headers, monkeypatch
    ):
        monkeypatch.setattr(
            "routes.routes_checkout.config.PUBLIC_BASE_URL",
            "https://canonical.example",
        )
        token = "valid-guest-token-with-enough-entropy"
        order_id = _insert_order(
            None,
            seeded_product["prices"][0]["id"],
            seeded_product["prices"][0]["amount_sats"],
            access_token=token,
            session_id="different-session",
        )

        assert client.get(f"/checkout/payment/{order_id}").status_code == 404
        assert client.get(f"/api/checkout/check-payment/{order_id}").status_code == 404
        assert client.get(f"/checkout/payment/{order_id}/qr").status_code == 404
        assert client.get(f"/orders/{order_id}").status_code == 404
        assert client.get(f"/orders/{order_id}/receipt.pdf").status_code == 404

        invalid = client.post(
            "/orders/lookup",
            data={"order_id": order_id, "access_token": "wrong"},
            headers=csrf_headers,
        )
        assert invalid.status_code == 404
        assert token.encode() not in invalid.data

        valid = client.post(
            "/orders/lookup",
            data={"order_id": order_id, "access_token": token},
            headers=csrf_headers,
            follow_redirects=False,
        )
        assert valid.status_code == 302
        assert valid.headers["Location"].endswith(f"/orders/{order_id}")
        assert token not in valid.headers["Location"]
        assert valid.headers["Cache-Control"] == "private, no-store"

        detail = client.get(valid.headers["Location"])
        assert detail.status_code == 200
        assert token.encode() in detail.data
        assert detail.headers["Cache-Control"] == "private, no-store"

        qr_resp = client.get(f"/checkout/payment/{order_id}/qr")
        assert qr_resp.status_code == 200
        assert qr_resp.headers["Content-Type"] == "image/png"

        pdf_resp = client.get(f"/orders/{order_id}/receipt.pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.data.startswith(b"%PDF")
        assert b"https://canonical.example/orders/lookup" in pdf_resp.data
        assert b"localhost" not in pdf_resp.data
        assert pdf_resp.headers["Cache-Control"] == "private, no-store"

    def test_guest_order_lookup_requires_csrf(self, client):
        response = client.post(
            "/orders/lookup",
            data={"order_id": "1", "access_token": "not-a-real-token"},
        )

        assert response.status_code == 403

    def test_guest_order_lookup_rejects_oversized_order_id(self, client, csrf_headers):
        response = client.post(
            "/orders/lookup",
            data={"order_id": str(2**80), "access_token": "not-a-real-token"},
            headers=csrf_headers,
        )

        assert response.status_code == 404

    def test_coinos_webhook_confirms_order_without_csrf(self, client, seeded_product, monkeypatch):
        set_config("coinos_webhook_secret", "secret")
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


class TestCoinosRuntimeConfig:
    def test_create_invoice_uses_db_backed_config(self, tmp_db, monkeypatch):
        from services import service_coinos

        set_config("coinos_api_key", "db-api-key")
        set_config("coinos_webhook_secret", "db-webhook-secret")
        set_config("coinos_enabled", "1")

        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"hash":"invoice123","text":"lnbc1invoice"}'

        def fake_urlopen(req, timeout=10):
            captured["headers"] = dict(req.header_items())
            captured["payload"] = json.loads(req.data.decode())
            captured["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setattr(service_coinos.urllib.request, "urlopen", fake_urlopen)

        invoice = service_coinos.create_invoice(
            1234,
            webhook_url="https://example.com/checkout/webhook/coinos",
        )

        assert invoice["hash"] == "invoice123"
        assert captured["headers"]["Authorization"] == "Bearer db-api-key"
        assert captured["payload"]["invoice"]["secret"] == "db-webhook-secret"
        assert captured["payload"]["invoice"]["webhook"] == "https://example.com/checkout/webhook/coinos"


class TestCheckoutCoupons:
    def test_apply_coupon_returns_discount(self, client, test_user, seeded_product, csrf_headers):
        from models.model_coupons import create_coupon
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 1, {}, user_id=test_user)
        create_coupon(code="SAVE20", discount_type="percent", discount_value=20)

        resp = client.post("/api/checkout/apply-coupon", json={"code": "save20"}, headers=csrf_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["code"] == "SAVE20"
        # subtotal 10000 sats * 20% = 2000
        assert data["discount_sats"] == 2000
        assert data["subtotal_sats"] == 10000

    def test_apply_invalid_coupon_returns_400(self, client, test_user, seeded_product, csrf_headers):
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 1, {}, user_id=test_user)

        resp = client.post("/api/checkout/apply-coupon", json={"code": "NOPE"}, headers=csrf_headers)
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_create_order_applies_discount_to_invoice(self, client, test_user, seeded_product, csrf_headers):
        from models.model_coupons import create_coupon, get_coupon
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 1, {}, user_id=test_user)
        create_coupon(code="HALF", discount_type="percent", discount_value=50)

        with patch("routes.routes_checkout.chf_to_sats", return_value=8500), \
             patch("routes.routes_checkout.create_invoice", return_value={"hash": "h", "text": "lnbc1"}) as mock_inv:
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer", "street": "Bahnhofstrasse", "house_number": "1",
                    "city": "Zurich", "postal_code": "8000", "country": "CH",
                    "cupom": "half",
                },
                headers=csrf_headers,
                follow_redirects=False,
            )

        assert resp.status_code == 302
        # subtotal 10000, 50% off => 5000 products + 8500 shipping = 13500
        assert mock_inv.call_args[0][0] == 5000 + 8500

        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (test_user,)
            ).fetchone()
        finally:
            conn.close()
        assert order["coupon_code"] == "HALF"
        assert int(order["discount_sats"]) == 5000
        assert get_coupon("HALF")["used_count"] == 1

    def test_create_order_ignores_invalid_coupon(self, client, test_user, seeded_product, csrf_headers):
        _login_session(client, user_id=test_user)
        add_to_cart("test-session", seeded_product["id"], seeded_product["prices"][0]["id"], 1, {}, user_id=test_user)

        with patch("routes.routes_checkout.chf_to_sats", return_value=8500), \
             patch("routes.routes_checkout.create_invoice", return_value={"hash": "h", "text": "lnbc1"}) as mock_inv:
            resp = client.post(
                "/checkout/create-order",
                data={
                    "name": "Buyer", "street": "Bahnhofstrasse", "house_number": "1",
                    "city": "Zurich", "postal_code": "8000", "country": "CH",
                    "cupom": "GARBAGE",
                },
                headers=csrf_headers,
                follow_redirects=False,
            )

        assert resp.status_code == 302
        # No discount applied: full 10000 + 8500
        assert mock_inv.call_args[0][0] == 10000 + 8500
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (test_user,)
            ).fetchone()
        finally:
            conn.close()
        assert order["coupon_code"] is None
        assert int(order["discount_sats"]) == 0
