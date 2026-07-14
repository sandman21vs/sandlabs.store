"""Tests for services/service_shipping.py."""

import json
import pytest


class TestGetCountryZone:
    def test_switzerland_is_ch(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("CH") == "CH"

    def test_lowercase_ch(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("ch") == "CH"

    def test_germany_is_eu(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("DE") == "EU"

    def test_france_is_eu(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("FR") == "EU"

    def test_norway_is_eu(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("NO") == "EU"

    def test_uk_is_eu(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("GB") == "EU"

    def test_brazil_is_world(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("BR") == "WORLD"

    def test_usa_is_world(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("US") == "WORLD"

    def test_empty_string_is_world(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone("") == "WORLD"

    def test_none_is_world(self):
        from services.service_shipping import get_country_zone
        assert get_country_zone(None) == "WORLD"


class TestCalculateShippingChf:
    def test_ch_light_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 500g -> first bracket (<=2kg) -> 7.00 CHF
        assert calculate_shipping_chf(500, "CH") == 7.00

    def test_ch_medium_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 3000g (3kg) -> second bracket (<=10kg) -> 9.50 CHF
        assert calculate_shipping_chf(3000, "CH") == 9.50

    def test_ch_heavy_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 15000g (15kg) -> third bracket (<=30kg) -> 16.00 CHF
        assert calculate_shipping_chf(15000, "CH") == 16.00

    def test_ch_oversize_uses_largest_bracket(self):
        from services.service_shipping import calculate_shipping_chf
        # 35kg > all brackets -> uses 30kg bracket
        assert calculate_shipping_chf(35000, "CH") == 16.00

    def test_eu_light_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 1kg -> EU first bracket (<=2kg) -> 20.00 CHF
        assert calculate_shipping_chf(1000, "DE") == 20.00

    def test_eu_medium_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 3kg -> EU second bracket (<=5kg) -> 30.00 CHF
        assert calculate_shipping_chf(3000, "FR") == 30.00

    def test_world_light_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 500g -> WORLD first bracket -> 30.00 CHF
        assert calculate_shipping_chf(500, "BR") == 30.00

    def test_world_medium_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 3kg -> WORLD second bracket (<=5kg) -> 50.00 CHF
        assert calculate_shipping_chf(3000, "US") == 50.00

    def test_exact_bracket_boundary(self):
        from services.service_shipping import calculate_shipping_chf
        # Exactly 2kg -> CH first bracket -> 7.00 CHF
        assert calculate_shipping_chf(2000, "CH") == 7.00

    def test_zero_weight(self):
        from services.service_shipping import calculate_shipping_chf
        # 0g still falls in first bracket
        assert calculate_shipping_chf(0, "CH") == 7.00

    def test_custom_rates_from_db(self, tmp_db):
        """Rates stored in config DB override defaults."""
        import db as db_mod
        import importlib
        import services.service_shipping as ss
        importlib.reload(ss)

        custom_rates = {"CH": {"1": 5.00, "5": 8.00}, "EU": {"1": 15.00}, "WORLD": {"1": 25.00}}
        conn = db_mod.get_db()
        conn.execute(
            "INSERT INTO config (key, value) VALUES ('shipping_rates', ?)",
            (json.dumps(custom_rates),),
        )
        conn.commit()
        conn.close()

        # Should use custom rate: 500g -> CH, <=1kg -> 5.00
        assert ss.calculate_shipping_chf(500, "CH") == 5.00


class TestHybridShippingOptions:
    def test_falls_back_to_table(self, tmp_db):
        from services.service_shipping import get_shipping_options

        options = get_shipping_options(500, "CH")
        assert len(options) == 1
        assert options[0]["source"] == "table"
        assert options[0]["carrier"] == "post"
        assert options[0]["price_chf"] == 7.0

    def test_uses_provider_quotes_sorted_cheapest_first(self, tmp_db, monkeypatch):
        from services import service_shipping, service_shipping_dhl, service_shipping_post

        monkeypatch.setattr(
            service_shipping_dhl, "quote",
            lambda w, c: [{"carrier": "dhl", "service": "Express", "price_chf": 22.0, "source": "dhl"}],
        )
        monkeypatch.setattr(
            service_shipping_post, "quote",
            lambda w, c: [{"carrier": "post", "service": "Priority", "price_chf": 9.5, "source": "post"}],
        )

        options = service_shipping.get_shipping_options(500, "CH")
        assert [o["carrier"] for o in options] == ["post", "dhl"]
        assert all(o["source"] != "table" for o in options)

    def test_survives_a_failing_carrier(self, tmp_db, monkeypatch):
        from services import service_shipping, service_shipping_dhl, service_shipping_post

        def boom(w, c):
            raise RuntimeError("carrier down")

        monkeypatch.setattr(service_shipping_dhl, "quote", boom)
        monkeypatch.setattr(
            service_shipping_post, "quote",
            lambda w, c: [{"carrier": "post", "service": "Priority", "price_chf": 9.5, "source": "post"}],
        )

        options = service_shipping.get_shipping_options(500, "CH")
        assert [o["carrier"] for o in options] == ["post"]


class TestShippingProviders:
    def test_dhl_none_without_credentials(self, tmp_db):
        from services.service_shipping_dhl import quote
        assert quote(500, "CH") is None

    def test_dhl_parses_api_response(self, tmp_db, monkeypatch):
        from models.model_config import set_config
        from services import service_shipping_dhl

        set_config("dhl_enabled", "1")
        set_config("dhl_api_key", "key")
        monkeypatch.setattr(
            service_shipping_dhl, "_request",
            lambda url, key, payload: {"options": [{"service": "Express", "price_chf": 22.5}]},
        )

        assert service_shipping_dhl.quote(500, "CH") == [
            {"carrier": "dhl", "service": "Express", "price_chf": 22.5, "source": "dhl"}
        ]

    def test_dhl_none_on_error(self, tmp_db, monkeypatch):
        from models.model_config import set_config
        from services import service_shipping_dhl

        set_config("dhl_enabled", "1")
        set_config("dhl_api_key", "key")

        def boom(url, key, payload):
            raise RuntimeError("network")

        monkeypatch.setattr(service_shipping_dhl, "_request", boom)
        assert service_shipping_dhl.quote(500, "CH") is None

    def test_post_parses_bare_price(self, tmp_db, monkeypatch):
        from models.model_config import set_config
        from services import service_shipping_post

        set_config("post_enabled", "1")
        set_config("post_api_key", "key")
        monkeypatch.setattr(
            service_shipping_post, "_request",
            lambda url, key, payload: {"price_chf": 9.7},
        )

        assert service_shipping_post.quote(500, "CH") == [
            {"carrier": "post", "service": "PostPac", "price_chf": 9.7, "source": "post"}
        ]


class TestShippingCalculateApiOptions:
    def test_returns_options_and_backcompat_fields(self, client, csrf_headers):
        from unittest.mock import patch

        with patch("routes.routes_checkout.chf_to_sats", return_value=8500):
            resp = client.post(
                "/api/shipping/calculate",
                json={"country": "CH", "weight_grams": 500},
                headers=csrf_headers,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["zone"] == "CH"
        assert len(data["options"]) == 1
        assert data["options"][0]["price_sats"] == 8500
        assert data["shipping_sats"] == 8500
