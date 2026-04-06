"""Tests for cart API routes."""

import json

import pytest


@pytest.fixture()
def product_ids(seeded_product):
    """Return (product_id, price_id) from the seeded product."""
    return seeded_product["id"], seeded_product["prices"][0]["id"]


class TestAddCartAPI:
    def test_add_item(self, client, product_ids):
        pid, price_id = product_ids
        resp = client.post("/api/cart/add", json={
            "product_id": pid,
            "price_id": price_id,
            "quantity": 1,
            "options": {},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["cart_count"] == 1

    def test_add_missing_product_id(self, client):
        resp = client.post("/api/cart/add", json={"price_id": 1})
        assert resp.status_code == 400

    def test_add_missing_price_id(self, client, product_ids):
        pid, _ = product_ids
        resp = client.post("/api/cart/add", json={"product_id": pid})
        assert resp.status_code == 400

    def test_add_invalid_product(self, client):
        resp = client.post("/api/cart/add", json={
            "product_id": "nonexistent",
            "price_id": 9999,
        })
        assert resp.status_code == 400

    def test_add_increments_quantity(self, client, product_ids):
        pid, price_id = product_ids
        payload = {"product_id": pid, "price_id": price_id, "quantity": 1, "options": {}}
        client.post("/api/cart/add", json=payload)
        resp = client.post("/api/cart/add", json=payload)
        assert resp.get_json()["cart_count"] == 2


class TestGetCartAPI:
    def test_empty_cart(self, client):
        resp = client.get("/api/cart")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["items"] == []
        assert data["total_sats"] == 0
        assert data["count"] == 0

    def test_cart_with_items(self, client, product_ids):
        pid, price_id = product_ids
        client.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 2, "options": {},
        })
        resp = client.get("/api/cart")
        data = resp.get_json()
        assert data["count"] == 2
        assert data["total_sats"] == 20000
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == pid


class TestUpdateCartAPI:
    def test_update_quantity(self, client, product_ids):
        pid, price_id = product_ids
        client.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 1, "options": {},
        })
        items = client.get("/api/cart").get_json()["items"]
        item_id = items[0]["id"]

        resp = client.put(f"/api/cart/{item_id}", json={"quantity": 5})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

        updated = client.get("/api/cart").get_json()
        assert updated["count"] == 5

    def test_update_missing_quantity(self, client, product_ids):
        pid, price_id = product_ids
        client.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 1, "options": {},
        })
        items = client.get("/api/cart").get_json()["items"]
        item_id = items[0]["id"]
        resp = client.put(f"/api/cart/{item_id}", json={})
        assert resp.status_code == 400

    def test_update_item_not_owned(self, client, product_ids):
        resp = client.put("/api/cart/99999", json={"quantity": 5})
        assert resp.status_code == 404


class TestRemoveCartAPI:
    def test_remove_item(self, client, product_ids):
        pid, price_id = product_ids
        client.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 1, "options": {},
        })
        items = client.get("/api/cart").get_json()["items"]
        item_id = items[0]["id"]

        resp = client.delete(f"/api/cart/{item_id}")
        assert resp.status_code == 200
        assert client.get("/api/cart").get_json()["count"] == 0

    def test_remove_item_not_owned(self, client):
        resp = client.delete("/api/cart/99999")
        assert resp.status_code == 404


class TestClearCartAPI:
    def test_clear_all(self, client, product_ids):
        pid, price_id = product_ids
        client.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 1, "options": {},
        })
        resp = client.delete("/api/cart")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        assert client.get("/api/cart").get_json()["count"] == 0

    def test_clear_empty_cart(self, client):
        resp = client.delete("/api/cart")
        assert resp.status_code == 200


class TestCartPage:
    def test_cart_page_renders(self, client):
        resp = client.get("/carrinho")
        assert resp.status_code == 200

    def test_cart_page_shows_items(self, client, product_ids):
        pid, price_id = product_ids
        client.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 2, "options": {},
        })
        resp = client.get("/carrinho")
        html = resp.data.decode()
        assert "Test Product" in html


class TestCartSessionIsolation:
    """Different clients (sessions) have independent carts."""

    def test_separate_sessions(self, app, product_ids):
        pid, price_id = product_ids
        c1 = app.test_client()
        c2 = app.test_client()

        c1.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 3, "options": {},
        })
        c2.post("/api/cart/add", json={
            "product_id": pid, "price_id": price_id, "quantity": 1, "options": {},
        })

        assert c1.get("/api/cart").get_json()["count"] == 3
        assert c2.get("/api/cart").get_json()["count"] == 1
