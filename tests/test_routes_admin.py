"""Tests for admin panel routes (Phase 7)."""

import json
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _form(admin_client, csrf_headers, url, data):
    """POST form data with CSRF header."""
    return admin_client.post(url, data=data, headers=csrf_headers,
                             follow_redirects=False)


# ── Setup ─────────────────────────────────────────────────────────────────────

class TestAdminSetup:
    def test_setup_page_accessible_when_no_admin(self, client):
        resp = client.get("/admin/setup")
        assert resp.status_code == 200
        assert b"setup" in resp.data.lower()

    def test_setup_redirects_when_admin_exists(self, client, admin_user):
        resp = client.get("/admin/setup")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_setup_creates_admin(self, client, csrf_headers, tmp_db):
        resp = _form(client, csrf_headers, "/admin/setup", {
            "name": "Admin",
            "email": "setup@test.com",
            "password": "securepass1",
            "confirm": "securepass1",
        })
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/")

        import db as db_mod
        conn = db_mod.get_db()
        try:
            user = conn.execute(
                "SELECT * FROM users WHERE email='setup@test.com'"
            ).fetchone()
        finally:
            conn.close()
        assert user is not None
        assert user["is_admin"] == 1
        with client.session_transaction() as sess:
            assert sess["user_id"] == user["id"]
            assert sess["is_admin"] is True

    def test_setup_can_store_coinos_config(self, client, csrf_headers, tmp_db):
        resp = _form(client, csrf_headers, "/admin/setup", {
            "name": "Admin",
            "email": "setup@test.com",
            "password": "securepass1",
            "confirm": "securepass1",
            "coinos_api_key": "coinos-key",
            "coinos_enabled": "1",
        })
        assert resp.status_code == 302

        import db as db_mod
        conn = db_mod.get_db()
        try:
            rows = conn.execute(
                "SELECT key, value FROM config WHERE key IN ('coinos_api_key', 'coinos_enabled', 'coinos_webhook_secret')"
            ).fetchall()
        finally:
            conn.close()
        cfg = {row["key"]: row["value"] for row in rows}
        assert cfg["coinos_api_key"] == "coinos-key"
        assert cfg["coinos_enabled"] == "1"
        assert cfg["coinos_webhook_secret"]

    def test_setup_password_mismatch_returns_error(self, client, csrf_headers, tmp_db):
        resp = _form(client, csrf_headers, "/admin/setup", {
            "email": "x@test.com",
            "password": "pass1234",
            "confirm": "different",
        })
        assert resp.status_code == 200
        assert b"coincidem" in resp.data.lower() or b"senha" in resp.data.lower()

    def test_setup_short_password_returns_error(self, client, csrf_headers, tmp_db):
        resp = _form(client, csrf_headers, "/admin/setup", {
            "email": "x@test.com",
            "password": "short",
            "confirm": "short",
        })
        assert resp.status_code == 200


# ── Auth / access control ─────────────────────────────────────────────────────

class TestAdminAccessControl:
    def test_admin_routes_redirect_to_setup_before_first_admin(self, client):
        resp = client.get("/admin/")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/setup")

    def test_dashboard_requires_auth(self, client, admin_user):
        resp = client.get("/admin/")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_products_requires_auth(self, client, admin_user):
        resp = client.get("/admin/products")
        assert resp.status_code == 302

    def test_orders_requires_auth(self, client, admin_user):
        resp = client.get("/admin/orders")
        assert resp.status_code == 302

    def test_settings_requires_auth(self, client, admin_user):
        resp = client.get("/admin/settings")
        assert resp.status_code == 302

    def test_non_admin_gets_403(self, client, test_user, admin_user):
        """A logged-in non-admin user should get 403."""
        with client.session_transaction() as sess:
            sess["user_id"] = test_user
            sess["is_admin"] = False
        resp = client.get("/admin/")
        assert resp.status_code == 403


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TestAdminDashboard:
    def test_dashboard_renders(self, admin_client):
        resp = admin_client.get("/admin/")
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data

    def test_dashboard_shows_zero_stats_when_empty(self, admin_client):
        resp = admin_client.get("/admin/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "0" in html  # at least the zero stats

    def test_dashboard_shows_product_count(self, admin_client, seeded_product):
        resp = admin_client.get("/admin/")
        html = resp.data.decode()
        assert "1" in html  # 1 product


# ── Products ──────────────────────────────────────────────────────────────────

class TestAdminProducts:
    def test_products_list_renders(self, admin_client):
        resp = admin_client.get("/admin/products")
        assert resp.status_code == 200
        assert b"Produtos" in resp.data

    def test_products_shows_seeded_product(self, admin_client, seeded_product):
        resp = admin_client.get("/admin/products")
        html = resp.data.decode()
        assert "Test Product" in html
        assert "test-product" in html

    def test_products_shows_inactive_products(self, admin_client, tmp_db):
        from models.model_products import create_product
        create_product({
            "id": "inactive-prod",
            "name": "Inactive Product",
            "summary": "test",
            "active": False,
            "prices": [],
            "images": [],
            "options": [],
        })
        resp = admin_client.get("/admin/products")
        assert b"Inactive Product" in resp.data

    def test_new_product_form_renders(self, admin_client):
        resp = admin_client.get("/admin/products/new")
        assert resp.status_code == 200
        assert b"Novo produto" in resp.data

    def test_create_product_via_form(self, admin_client, csrf_headers):
        resp = _form(admin_client, csrf_headers, "/admin/products/new", {
            "id": "new-test-prod",
            "name": "Form Product",
            "summary": "Created via form",
            "details_html": "<p>Test</p>",
            "weight_grams": "100",
            "buy_button_text": "Comprar",
            "sort_order": "0",
            "active": "on",
            "prices_json": json.dumps([
                {"label": "Base", "amount_sats": 5000, "display_text": "5 000 sats"}
            ]),
            "options_json": "[]",
            "existing_images_json": "[]",
        })
        assert resp.status_code == 302
        assert "/admin/products" in resp.headers["Location"]

        from models.model_products import get_product_by_id
        p = get_product_by_id("new-test-prod")
        assert p is not None
        assert p["name"] == "Form Product"
        assert len(p["prices"]) == 1
        assert p["prices"][0]["amount_sats"] == 5000

    def test_create_fiat_product_via_form(self, admin_client, csrf_headers, monkeypatch):
        monkeypatch.setattr("services.service_pricing.fiat_to_sats", lambda amount, currency: 14900)
        resp = _form(admin_client, csrf_headers, "/admin/products/new", {
            "id": "new-chf-prod",
            "name": "CHF Product",
            "summary": "Created via form",
            "details_html": "<p>Test</p>",
            "weight_grams": "100",
            "buy_button_text": "Comprar",
            "sort_order": "0",
            "active": "on",
            "prices_json": json.dumps([
                {
                    "label": "Base",
                    "pricing_mode": "fiat",
                    "currency_code": "CHF",
                    "amount_fiat": "149.00",
                }
            ]),
            "options_json": "[]",
            "existing_images_json": "[]",
        })
        assert resp.status_code == 302

        from models.model_products import get_product_by_id, products_to_js_format
        p = get_product_by_id("new-chf-prod")
        assert p is not None
        assert p["prices"][0]["currency_code"] == "CHF"
        assert p["prices"][0]["amount_fiat"] == "149.00"
        js_price = products_to_js_format([p])[0]["preco"][0]
        assert js_price["amountSats"] == 14900

    def test_create_product_missing_id_shows_error(self, admin_client, csrf_headers):
        resp = _form(admin_client, csrf_headers, "/admin/products/new", {
            "name": "No ID Product",
            "summary": "test",
            "prices_json": "[]",
            "options_json": "[]",
            "existing_images_json": "[]",
        })
        assert resp.status_code == 200
        assert b"obrigat" in resp.data.lower()

    def test_edit_product_form_renders(self, admin_client, seeded_product):
        resp = admin_client.get(f"/admin/products/{seeded_product['id']}/edit")
        assert resp.status_code == 200
        assert b"Test Product" in resp.data

    def test_edit_product_redirects_if_not_found(self, admin_client):
        resp = admin_client.get("/admin/products/nonexistent/edit")
        assert resp.status_code == 302

    def test_update_product_via_form(self, admin_client, csrf_headers, seeded_product):
        resp = _form(admin_client, csrf_headers,
                     f"/admin/products/{seeded_product['id']}/edit", {
            "name": "Updated Name",
            "summary": "Updated summary",
            "details_html": "",
            "weight_grams": "200",
            "buy_button_text": "Comprar",
            "sort_order": "0",
            "active": "on",
            "prices_json": json.dumps([
                {"label": "New Price", "amount_sats": 99000, "display_text": "99 000 sats"}
            ]),
            "options_json": "[]",
            "existing_images_json": "[]",
        })
        assert resp.status_code == 302

        from models.model_products import get_product_by_id
        p = get_product_by_id(seeded_product["id"])
        assert p["name"] == "Updated Name"
        assert p["prices"][0]["amount_sats"] == 99000

    def test_delete_product(self, admin_client, csrf_headers, seeded_product):
        resp = _form(admin_client, csrf_headers,
                     f"/admin/products/{seeded_product['id']}/delete", {})
        assert resp.status_code == 302

        from models.model_products import get_product_by_id
        assert get_product_by_id(seeded_product["id"]) is None

    def test_delete_nonexistent_product(self, admin_client, csrf_headers):
        resp = _form(admin_client, csrf_headers,
                     "/admin/products/ghost/delete", {})
        assert resp.status_code == 302


# ── Orders ────────────────────────────────────────────────────────────────────

class TestAdminOrders:
    def test_orders_page_renders(self, admin_client):
        resp = admin_client.get("/admin/orders")
        assert resp.status_code == 200
        assert b"Pedidos" in resp.data

    def test_orders_empty_state(self, admin_client):
        resp = admin_client.get("/admin/orders")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Nenhum pedido" in html

    def test_orders_filter_by_status(self, admin_client):
        resp = admin_client.get("/admin/orders?status=pending")
        assert resp.status_code == 200

    def test_order_detail_404_redirects(self, admin_client):
        resp = admin_client.get("/admin/orders/99999")
        assert resp.status_code == 302

    def test_update_order_status_with_tracking(self, admin_client, csrf_headers, seeded_product, db_conn):
        cursor = db_conn.execute(
            """
            INSERT INTO orders (
                user_id, session_id, status, total_sats, shipping_sats,
                shipping_name, shipping_address, shipping_postal_code, shipping_country
            ) VALUES (1, 'admin-session', 'paid', 10000, 0, 'Buyer', 'Street 1', '8000', 'CH')
            """
        )
        order_id = cursor.lastrowid
        db_conn.execute(
            """
            INSERT INTO order_items (order_id, product_id, price_id, quantity, unit_sats, options_json)
            VALUES (?, ?, ?, 1, ?, '{}')
            """,
            (order_id, seeded_product["id"], seeded_product["prices"][0]["id"], seeded_product["prices"][0]["amount_sats"]),
        )
        db_conn.commit()

        resp = _form(admin_client, csrf_headers, f"/admin/orders/{order_id}/status", {
            "status": "shipped",
            "tracking": "CH123456789CH",
        })
        assert resp.status_code == 302

        row = db_conn.execute(
            "SELECT status, shipping_tracking FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["status"] == "shipped"
        assert row["shipping_tracking"] == "CH123456789CH"


# ── Settings ──────────────────────────────────────────────────────────────────

class TestAdminSettings:
    def test_settings_page_renders(self, admin_client):
        resp = admin_client.get("/admin/settings")
        assert resp.status_code == 200
        assert b"Configura" in resp.data

    def test_settings_shows_default_shipping_rates(self, admin_client):
        resp = admin_client.get("/admin/settings")
        assert b"CH" in resp.data
        assert b"EU" in resp.data

    def test_save_whatsapp_contact(self, admin_client, csrf_headers):
        resp = _form(admin_client, csrf_headers, "/admin/settings", {
            "whatsapp": "5541999990000",
            "telegram": "",
            "coinos_enabled": "",
            "shipping_rates": '{"CH":{"2":7},"EU":{"2":20},"WORLD":{"2":30}}',
        })
        assert resp.status_code == 302

        import db as db_mod
        conn = db_mod.get_db()
        try:
            row = conn.execute("SELECT value FROM config WHERE key='whatsapp'").fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row["value"] == "5541999990000"

    def test_invalid_shipping_json_shows_error(self, admin_client, csrf_headers):
        resp = _form(admin_client, csrf_headers, "/admin/settings", {
            "shipping_rates": "NOT VALID JSON",
            "whatsapp": "",
            "telegram": "",
            "coinos_enabled": "",
        })
        assert resp.status_code == 302  # redirects back with flash error

    def test_coinos_enabled_toggle(self, admin_client, csrf_headers):
        resp = _form(admin_client, csrf_headers, "/admin/settings", {
            "coinos_api_key": "db-key",
            "coinos_enabled": "on",
            "shipping_rates": '{"CH":{"2":7},"EU":{"2":20},"WORLD":{"2":30}}',
        })
        assert resp.status_code == 302

        import db as db_mod
        conn = db_mod.get_db()
        try:
            row = conn.execute("SELECT value FROM config WHERE key='coinos_enabled'").fetchone()
        finally:
            conn.close()
        assert row["value"] == "1"

    def test_coinos_is_not_enabled_without_api_key(self, admin_client, csrf_headers):
        resp = _form(admin_client, csrf_headers, "/admin/settings", {
            "coinos_enabled": "on",
            "shipping_rates": '{"CH":{"2":7},"EU":{"2":20},"WORLD":{"2":30}}',
        })
        assert resp.status_code == 302

        import db as db_mod
        conn = db_mod.get_db()
        try:
            row = conn.execute("SELECT value FROM config WHERE key='coinos_enabled'").fetchone()
        finally:
            conn.close()
        assert row["value"] == "0"
