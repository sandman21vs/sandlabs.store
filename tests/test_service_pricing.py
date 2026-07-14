"""Tests for product pricing configuration and normalization."""


def test_admin_enabled_currencies_include_usd():
    from services.service_pricing import ADMIN_ENABLED_CURRENCIES

    assert ADMIN_ENABLED_CURRENCIES == ("SATS", "CHF", "USD")


def test_normalize_usd_price_for_admin_preview():
    from services.service_pricing import normalize_price_record

    price = normalize_price_record({
        "label": "Base",
        "pricing_mode": "fiat",
        "currency_code": "usd",
        "amount_fiat": "149,995",
    })

    assert price["pricing_mode"] == "fiat"
    assert price["currency_code"] == "USD"
    assert price["amount_fiat"] == "150.00"
    assert price["amount_sats"] == 0
    assert price["display_text"] == "USD 150.00"
