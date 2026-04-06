"""Tests for checkout routes — Phase 6: shipping calculation endpoint."""

from unittest.mock import patch


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
