"""Tests for models/model_cart.py — cart operations."""

import json

import pytest


@pytest.fixture()
def product_with_price(seeded_product):
    """Return (product_id, price_id) for a seeded product."""
    return seeded_product["id"], seeded_product["prices"][0]["id"]


class TestAddToCart:
    def test_add_single_item(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        items = get_cart("sess1")
        assert len(items) == 1
        assert items[0]["product_id"] == pid
        assert items[0]["quantity"] == 1

    def test_add_increments_existing(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        add_to_cart("sess1", pid, price_id, 2, {})
        items = get_cart("sess1")
        assert len(items) == 1
        assert items[0]["quantity"] == 3

    def test_different_options_create_separate_items(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {"color": "red"})
        add_to_cart("sess1", pid, price_id, 1, {"color": "blue"})
        items = get_cart("sess1")
        assert len(items) == 2

    def test_different_sessions_isolated(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        add_to_cart("sess2", pid, price_id, 1, {})
        assert len(get_cart("sess1")) == 1
        assert len(get_cart("sess2")) == 1

    def test_options_json_normalized(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        # Different key order, same content
        add_to_cart("sess1", pid, price_id, 1, {"b": 2, "a": 1})
        add_to_cart("sess1", pid, price_id, 1, {"a": 1, "b": 2})
        items = get_cart("sess1")
        assert len(items) == 1
        assert items[0]["quantity"] == 2


class TestGetCart:
    def test_empty_cart(self, tmp_db):
        from models.model_cart import get_cart
        assert get_cart("nonexistent") == []

    def test_includes_product_details(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 2, {})
        items = get_cart("sess1")
        item = items[0]
        assert item["product_name"] == "Test Product"
        assert item["price_label"] == "Base"
        assert item["display_text"] == "10 000 sats"
        assert item["amount_sats"] == 10000

    def test_line_total_calculated(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 3, {})
        items = get_cart("sess1")
        assert items[0]["line_total_sats"] == 30000

    def test_user_id_scope(self, product_with_price, test_user):
        from models.model_cart import add_to_cart, get_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {}, user_id=test_user)
        assert get_cart("sess1", user_id=None) == []
        assert len(get_cart("sess1", user_id=test_user)) == 1

    def test_fiat_prices_resolve_to_dynamic_sats(self, tmp_db, monkeypatch):
        from models.model_cart import add_to_cart, get_cart
        from models.model_products import create_product

        monkeypatch.setattr("services.service_pricing.fiat_to_sats", lambda amount, currency: 2500)
        product = create_product({
            "id": "fiat-cart",
            "name": "Fiat Cart",
            "summary": "Test",
            "prices": [{
                "label": "Base",
                "pricing_mode": "fiat",
                "currency_code": "CHF",
                "amount_fiat": "25.00",
            }],
            "images": [],
            "options": [],
        })
        add_to_cart("sess1", product["id"], product["prices"][0]["id"], 2, {})
        items = get_cart("sess1")
        assert items[0]["display_text"] == "CHF 25.00"
        assert items[0]["amount_sats"] == 2500
        assert items[0]["line_total_sats"] == 5000


class TestUpdateCartItem:
    def test_update_quantity(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart, update_cart_item
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        item_id = get_cart("sess1")[0]["id"]
        update_cart_item(item_id, 5)
        assert get_cart("sess1")[0]["quantity"] == 5

    def test_update_to_zero_removes_item(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart, update_cart_item
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        item_id = get_cart("sess1")[0]["id"]
        update_cart_item(item_id, 0)
        assert get_cart("sess1") == []

    def test_update_negative_removes_item(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart, update_cart_item
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        item_id = get_cart("sess1")[0]["id"]
        update_cart_item(item_id, -1)
        assert get_cart("sess1") == []


class TestRemoveCartItem:
    def test_remove_item(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart, remove_cart_item
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        item_id = get_cart("sess1")[0]["id"]
        assert remove_cart_item(item_id) is True
        assert get_cart("sess1") == []

    def test_remove_nonexistent(self, tmp_db):
        from models.model_cart import remove_cart_item
        assert remove_cart_item(99999) is False


class TestClearCart:
    def test_clear_all_items(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart, clear_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        add_to_cart("sess1", pid, price_id, 1, {"color": "red"})
        clear_cart("sess1")
        assert get_cart("sess1") == []

    def test_clear_only_affects_target_session(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart, clear_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {})
        add_to_cart("sess2", pid, price_id, 1, {})
        clear_cart("sess1")
        assert get_cart("sess1") == []
        assert len(get_cart("sess2")) == 1


class TestMergeCart:
    def test_merge_anonymous_to_user(self, product_with_price, test_user):
        from models.model_cart import add_to_cart, get_cart, merge_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 2, {})
        merge_cart("sess1", user_id=test_user)
        assert get_cart("sess1", user_id=None) == []
        user_items = get_cart("sess1", user_id=test_user)
        assert len(user_items) == 1
        assert user_items[0]["quantity"] == 2

    def test_merge_sums_duplicates(self, product_with_price, test_user):
        from models.model_cart import add_to_cart, get_cart, merge_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 2, {}, user_id=test_user)
        add_to_cart("sess1", pid, price_id, 3, {})
        merge_cart("sess1", user_id=test_user)
        user_items = get_cart("sess1", user_id=test_user)
        assert len(user_items) == 1
        assert user_items[0]["quantity"] == 5

    def test_merge_empty_anonymous_is_noop(self, product_with_price, test_user):
        from models.model_cart import add_to_cart, get_cart, merge_cart
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 1, {}, user_id=test_user)
        merge_cart("sess1", user_id=test_user)
        assert len(get_cart("sess1", user_id=test_user)) == 1


class TestCartTotal:
    def test_total_calculation(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart_total
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 3, {})
        assert get_cart_total("sess1") == 30000

    def test_empty_cart_total_is_zero(self, tmp_db):
        from models.model_cart import get_cart_total
        assert get_cart_total("empty") == 0

    def test_total_uses_current_fiat_conversion(self, tmp_db, monkeypatch):
        from models.model_cart import add_to_cart, get_cart_total
        from models.model_products import create_product

        monkeypatch.setattr("services.service_pricing.fiat_to_sats", lambda amount, currency: 8000)
        product = create_product({
            "id": "fiat-total",
            "name": "Fiat Total",
            "summary": "Test",
            "prices": [{
                "label": "Base",
                "pricing_mode": "fiat",
                "currency_code": "CHF",
                "amount_fiat": "80.00",
            }],
            "images": [],
            "options": [],
        })
        add_to_cart("sess1", product["id"], product["prices"][0]["id"], 3, {})
        assert get_cart_total("sess1") == 24000


class TestCartCount:
    def test_count_sums_quantities(self, product_with_price):
        from models.model_cart import add_to_cart, get_cart_count
        pid, price_id = product_with_price
        add_to_cart("sess1", pid, price_id, 3, {})
        add_to_cart("sess1", pid, price_id, 2, {"color": "red"})
        assert get_cart_count("sess1") == 5

    def test_empty_cart_count_is_zero(self, tmp_db):
        from models.model_cart import get_cart_count
        assert get_cart_count("empty") == 0
