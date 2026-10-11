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
    """calculate_shipping_chf returns the cheapest table service (Economy in CH)."""

    def test_ch_light_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 500g -> first bracket (<=2kg) -> 9.00 CHF
        assert calculate_shipping_chf(500, "CH") == 9.00

    def test_ch_medium_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 3000g (3kg) -> second bracket (<=10kg) -> 12.00 CHF
        assert calculate_shipping_chf(3000, "CH") == 12.00

    def test_ch_heavy_package(self):
        from services.service_shipping import calculate_shipping_chf
        # 15000g (15kg) -> third bracket (<=30kg) -> 21.00 CHF
        assert calculate_shipping_chf(15000, "CH") == 21.00

    def test_ch_oversize_uses_largest_bracket(self):
        from services.service_shipping import calculate_shipping_chf
        # 35kg > all brackets -> uses 30kg bracket
        assert calculate_shipping_chf(35000, "CH") == 21.00

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
        # Exactly 2kg -> CH first bracket -> 9.00 CHF
        assert calculate_shipping_chf(2000, "CH") == 9.00

    def test_zero_weight(self):
        from services.service_shipping import calculate_shipping_chf
        # 0g still falls in first bracket
        assert calculate_shipping_chf(0, "CH") == 9.00

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


class TestRateTableServices:
    def test_switzerland_offers_economy_and_priority(self, tmp_db):
        from services.service_shipping import get_table_options

        options = get_table_options(500, "CH")
        assert [(o["service"], o["price_chf"]) for o in options] == [
            ("PostPac Economy", 9.0),
            ("PostPac Priority", 10.5),
        ]
        assert all(o["carrier"] == "post" and o["source"] == "table" for o in options)

    def test_each_service_uses_its_own_bracket(self, tmp_db):
        from services.service_shipping import get_table_options

        prices = {o["service"]: o["price_chf"] for o in get_table_options(12000, "CH")}
        assert prices == {"PostPac Economy": 21.0, "PostPac Priority": 22.5}

    def test_flat_zone_is_one_unnamed_service(self, tmp_db):
        from services.service_shipping import get_table_options

        assert get_table_options(500, "DE") == [
            {"carrier": "post", "service": "PostPac", "price_chf": 20.0, "source": "table"}
        ]

    def test_stored_flat_table_keeps_working(self, tmp_db):
        from models.model_config import set_config
        from services.service_shipping import get_shipping_options

        set_config("shipping_rates", json.dumps({"CH": {"1": 5.0, "5": 8.0}}))
        options = get_shipping_options(500, "CH")
        assert [(o["service"], o["price_chf"]) for o in options] == [("PostPac", 5.0)]

    def test_malformed_service_is_skipped(self, tmp_db):
        from models.model_config import set_config
        from services.service_shipping import get_table_options

        set_config("shipping_rates", json.dumps({
            "CH": {"Good": {"2": 6.0}, "Bad": {"heavy": "lots"}},
        }))
        assert [o["service"] for o in get_table_options(500, "CH")] == ["Good"]

    def test_non_object_table_falls_back_to_defaults(self, tmp_db):
        from models.model_config import set_config
        from services.service_shipping import calculate_shipping_chf

        set_config("shipping_rates", "[1, 2, 3]")
        assert calculate_shipping_chf(500, "CH") == 9.0

    def test_empty_table_still_returns_an_option(self, tmp_db):
        from models.model_config import set_config
        from services.service_shipping import get_shipping_options

        set_config("shipping_rates", "{}")
        options = get_shipping_options(500, "CH")
        assert len(options) == 1 and options[0]["price_chf"] == 0.0


class TestLegacyRateTableMigration:
    def test_untouched_legacy_table_is_dropped(self, tmp_db):
        import init_db
        from models.model_config import get_config, set_config
        from services.service_shipping import LEGACY_DEFAULT_RATES, calculate_shipping_chf

        set_config("shipping_rates", json.dumps(LEGACY_DEFAULT_RATES, indent=2))
        init_db.init_db()

        assert get_config("shipping_rates", "missing") == "missing"
        assert calculate_shipping_chf(500, "CH") == 9.0

    def test_edited_table_is_preserved(self, tmp_db):
        import init_db
        from models.model_config import get_config, set_config

        edited = json.dumps({"CH": {"2": 6.5}})
        set_config("shipping_rates", edited)
        init_db.init_db()

        assert get_config("shipping_rates") == edited


class TestHybridShippingOptions:
    def test_table_only_without_live_carriers(self, tmp_db):
        from services.service_shipping import get_shipping_options

        options = get_shipping_options(500, "CH")
        assert [o["service"] for o in options] == ["PostPac Economy", "PostPac Priority"]
        assert all(o["source"] == "table" for o in options)

    def test_live_quotes_are_added_and_sorted_cheapest_first(self, tmp_db, monkeypatch):
        from services import service_shipping, service_shipping_dhl

        monkeypatch.setattr(
            service_shipping_dhl, "quote",
            lambda w, c: [{"carrier": "dhl", "service": "Express", "price_chf": 9.9, "source": "dhl"}],
        )

        options = service_shipping.get_shipping_options(500, "CH")
        assert [(o["carrier"], o["service"]) for o in options] == [
            ("post", "PostPac Economy"),
            ("dhl", "Express"),
            ("post", "PostPac Priority"),
        ]

    def test_survives_a_failing_carrier(self, tmp_db, monkeypatch):
        from services import service_shipping, service_shipping_dhl

        def boom(w, c):
            raise RuntimeError("carrier down")

        monkeypatch.setattr(service_shipping_dhl, "quote", boom)

        options = service_shipping.get_shipping_options(500, "CH")
        assert [o["carrier"] for o in options] == ["post", "post"]


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
        assert [o["service"] for o in data["options"]] == ["PostPac Economy", "PostPac Priority"]
        assert data["options"][0]["price_sats"] == 8500
        assert data["shipping_chf"] == 9.0
        assert data["shipping_sats"] == 8500
