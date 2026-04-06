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
