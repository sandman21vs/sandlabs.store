"""Tests for models/model_products.py — CRUD and JS format conversion."""

import json

import pytest


class TestGetAllProducts:
    def test_empty_database_returns_empty_list(self, tmp_db):
        from models.model_products import get_all_products
        assert get_all_products() == []

    def test_returns_active_products(self, seeded_product):
        from models.model_products import get_all_products
        products = get_all_products()
        assert len(products) == 1
        assert products[0]["id"] == "test-product"

    def test_excludes_inactive_products(self, tmp_db, sample_product_data):
        from models.model_products import create_product, get_all_products
        sample_product_data["active"] = False
        create_product(sample_product_data)
        assert get_all_products() == []

    def test_includes_prices_images_options(self, seeded_product):
        from models.model_products import get_all_products
        p = get_all_products()[0]
        assert len(p["prices"]) == 2
        assert len(p["images"]) == 2
        assert len(p["options"]) == 1

    def test_sorted_by_sort_order(self, tmp_db, sample_product_data):
        from models.model_products import create_product, get_all_products
        data_a = {**sample_product_data, "id": "aaa", "sort_order": 2}
        data_b = {**sample_product_data, "id": "bbb", "sort_order": 1}
        create_product(data_a)
        create_product(data_b)
        products = get_all_products()
        assert [p["id"] for p in products] == ["bbb", "aaa"]


class TestGetProductById:
    def test_existing_product(self, seeded_product):
        from models.model_products import get_product_by_id
        p = get_product_by_id("test-product")
        assert p is not None
        assert p["name"] == "Test Product"
        assert len(p["prices"]) == 2

    def test_nonexistent_product(self, tmp_db):
        from models.model_products import get_product_by_id
        assert get_product_by_id("nope") is None


class TestCreateProduct:
    def test_create_minimal_product(self, tmp_db):
        from models.model_products import create_product, get_product_by_id
        result = create_product({
            "id": "minimal",
            "name": "Minimal",
            "summary": "Just testing",
            "prices": [],
            "images": [],
            "options": [],
        })
        assert result["id"] == "minimal"
        fetched = get_product_by_id("minimal")
        assert fetched["name"] == "Minimal"

    def test_create_with_all_fields(self, tmp_db, sample_product_data):
        from models.model_products import create_product
        result = create_product(sample_product_data)
        assert result["id"] == "test-product"
        assert result["allow_addon_seed"] is True
        assert result["badge_text"] == "New"
        assert result["prices"][0]["label"] == "Base"
        assert result["images"][0]["filename"] == "images/test1.png"
        assert result["options"][0]["type"] == "colorPair"

    def test_duplicate_id_raises(self, seeded_product, sample_product_data):
        from models.model_products import create_product
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            create_product(sample_product_data)

    def test_images_as_strings(self, tmp_db):
        from models.model_products import create_product
        result = create_product({
            "id": "str-images",
            "name": "String Images",
            "summary": "Test",
            "images": ["images/a.png", "images/b.png"],
            "prices": [],
            "options": [],
        })
        assert result["images"][0]["filename"] == "images/a.png"
        assert result["images"][1]["filename"] == "images/b.png"


class TestUpdateProduct:
    def test_update_basic_fields(self, seeded_product):
        from models.model_products import update_product, get_product_by_id
        update_product("test-product", {
            "name": "Updated Name",
            "summary": "Updated summary",
            "prices": [],
            "images": [],
            "options": [],
        })
        p = get_product_by_id("test-product")
        assert p["name"] == "Updated Name"
        assert p["summary"] == "Updated summary"

    def test_update_replaces_prices(self, seeded_product):
        from models.model_products import update_product, get_product_by_id
        update_product("test-product", {
            "name": "Same",
            "summary": "Same",
            "prices": [{"label": "New Price", "amount_sats": 99999, "display_text": "99 999 sats"}],
            "images": [],
            "options": [],
        })
        p = get_product_by_id("test-product")
        assert len(p["prices"]) == 1
        assert p["prices"][0]["amount_sats"] == 99999

    def test_update_nonexistent_raises(self, tmp_db):
        from models.model_products import update_product
        with pytest.raises(ValueError, match="Product not found"):
            update_product("ghost", {"name": "X", "summary": "X"})


class TestDeleteProduct:
    def test_delete_existing(self, seeded_product):
        from models.model_products import delete_product, get_product_by_id
        assert delete_product("test-product") is True
        assert get_product_by_id("test-product") is None

    def test_delete_cascades_related(self, seeded_product, db_conn):
        from models.model_products import delete_product
        import db as db_mod
        delete_product("test-product")
        conn = db_mod.get_db()
        try:
            assert conn.execute("SELECT COUNT(*) FROM product_prices WHERE product_id='test-product'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM product_images WHERE product_id='test-product'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM product_options WHERE product_id='test-product'").fetchone()[0] == 0
        finally:
            conn.close()

    def test_delete_nonexistent_returns_false(self, tmp_db):
        from models.model_products import delete_product
        assert delete_product("nope") is False


class TestProductsToJsFormat:
    def test_basic_conversion(self, seeded_product):
        from models.model_products import get_all_products, products_to_js_format
        products = get_all_products()
        js = products_to_js_format(products)

        assert len(js) == 1
        p = js[0]
        assert p["id"] == "test-product"
        assert p["nome"] == "Test Product"
        assert p["resumo"] == "A test product for unit tests."
        assert p["detalhesHTML"] == "<p>Details here</p>"
        assert p["allowAddOnSeed"] is True
        assert p["buyButtonText"] == "Buy Test"

    def test_badge_conversion(self, seeded_product):
        from models.model_products import get_all_products, products_to_js_format
        js = products_to_js_format(get_all_products())
        assert js[0]["badge"] == {"text": "New", "variant": "new"}

    def test_no_badge_when_null(self, tmp_db):
        from models.model_products import create_product, get_all_products, products_to_js_format
        create_product({
            "id": "no-badge",
            "name": "No Badge",
            "summary": "Test",
            "badge_text": None,
            "prices": [],
            "images": [],
            "options": [],
        })
        js = products_to_js_format(get_all_products())
        assert js[0]["badge"] is None

    def test_images_as_flat_list(self, seeded_product):
        from models.model_products import get_all_products, products_to_js_format
        js = products_to_js_format(get_all_products())
        assert js[0]["imagens"] == ["images/test1.png", "images/test2.png"]

    def test_prices_include_amount_sats(self, seeded_product):
        from models.model_products import get_all_products, products_to_js_format
        js = products_to_js_format(get_all_products())
        prices = js[0]["preco"]
        assert prices[0]["label"] == "Base"
        assert prices[0]["valor"] == "10 000 sats"
        assert prices[0]["amountSats"] == 10000
        assert prices[0]["satsDisplay"] == "10 000 sats"

    def test_brl_prices_gain_sats_display(self, tmp_db, monkeypatch):
        from models.model_products import create_product, get_all_products, products_to_js_format

        monkeypatch.setattr("services.service_pricing.fiat_to_sats", lambda amount, currency: 4600)
        create_product({
            "id": "brl-product",
            "name": "BRL Product",
            "summary": "Test",
            "prices": [{"label": "Base", "amount_sats": 0, "display_text": "R$ 230"}],
            "images": [],
            "options": [],
        })
        js = products_to_js_format(get_all_products())
        price = js[0]["preco"][0]
        assert price["valor"] == "R$ 230"
        assert price["satsDisplay"] == "~4 600 sats"
        assert price["currencyCode"] == "BRL"
        assert price["pricingMode"] == "fiat"

    def test_chf_prices_are_resolved_to_sats_dynamically(self, tmp_db, monkeypatch):
        from models.model_products import create_product, get_all_products, products_to_js_format

        monkeypatch.setattr("services.service_pricing.fiat_to_sats", lambda amount, currency: 12345)
        create_product({
            "id": "chf-product",
            "name": "CHF Product",
            "summary": "Test",
            "prices": [{
                "label": "Base",
                "pricing_mode": "fiat",
                "currency_code": "CHF",
                "amount_fiat": "49.90",
            }],
            "images": [],
            "options": [],
        })
        js = products_to_js_format(get_all_products())
        price = js[0]["preco"][0]
        assert price["valor"] == "CHF 49.90"
        assert price["amountSats"] == 12345
        assert price["satsDisplay"] == "~12 345 sats"
        assert price["amountFiat"] == "49.90"

    def test_options_have_correct_structure(self, seeded_product):
        from models.model_products import get_all_products, products_to_js_format
        js = products_to_js_format(get_all_products())
        opts = js[0]["options"]
        assert opts[0]["type"] == "colorPair"
        assert opts[0]["title"] == "Cores"
        assert opts[0]["inputs"][0]["name"] == "bodyColor"

    def test_serializable_to_json(self, seeded_product):
        from models.model_products import get_all_products, products_to_js_format
        js = products_to_js_format(get_all_products())
        # Must not raise
        result = json.dumps(js, ensure_ascii=False)
        assert "test-product" in result

    def test_empty_list(self, tmp_db):
        from models.model_products import products_to_js_format
        assert products_to_js_format([]) == []
