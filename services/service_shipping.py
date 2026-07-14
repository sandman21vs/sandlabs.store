"""Swiss Post shipping cost calculator.

Uses a static lookup table (Post.ch rates) stored in the config table.
The table is editable via the admin panel (Phase 7).
"""
import json
import logging

import db

logger = logging.getLogger(__name__)

# Default PostPac rates (CHF) — thresholds are max weight in kg
DEFAULT_RATES = {
    "CH":    {2: 7.00, 10: 9.50, 30: 16.00},
    "EU":    {2: 20.00, 5: 30.00, 10: 45.00, 30: 80.00},
    "WORLD": {2: 30.00, 5: 50.00, 10: 75.00, 30: 120.00},
}

# EU + EEA countries (ISO 3166-1 alpha-2)
EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
    "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
    "RO", "SK", "SI", "ES", "SE",
    "NO", "IS", "LI", "GB",  # EEA + UK
}


def get_country_zone(country_code: str) -> str:
    """Return shipping zone: 'CH', 'EU', or 'WORLD'."""
    cc = (country_code or "").upper().strip()
    if cc == "CH":
        return "CH"
    if cc in EU_COUNTRIES:
        return "EU"
    return "WORLD"


def get_shipping_rates() -> dict:
    """Fetch rate table from config DB (key 'shipping_rates').

    Falls back to DEFAULT_RATES if not configured or on parse error.
    Rates are stored as JSON with string keys (JSON limitation).
    """
    try:
        conn = db.get_db()
        row = conn.execute(
            "SELECT value FROM config WHERE key='shipping_rates'"
        ).fetchone()
        conn.close()
        if row:
            return json.loads(row["value"])
    except Exception:
        logger.exception("Failed to load shipping rates from DB")
    return DEFAULT_RATES


def calculate_shipping_chf(weight_grams: int, country_code: str) -> float:
    """Calculate shipping cost in CHF.

    Looks up the rate table for the destination zone and returns the
    price for the smallest weight bracket that covers weight_grams.

    Args:
        weight_grams: Total shipment weight in grams.
        country_code: ISO 3166-1 alpha-2 country code (e.g. 'CH', 'DE', 'BR').

    Returns:
        Shipping cost in CHF (float). Returns 0.0 if rates are empty.
    """
    zone = get_country_zone(country_code)
    rates = get_shipping_rates()
    zone_rates = rates.get(zone) or rates.get("WORLD") or {}

    if not zone_rates:
        return 0.0

    weight_kg = weight_grams / 1000.0

    # Keys may be ints (DEFAULT_RATES) or strings (from JSON in DB)
    sorted_thresholds = sorted(zone_rates.keys(), key=lambda x: float(x))
    for threshold in sorted_thresholds:
        if weight_kg <= float(threshold):
            return float(zone_rates[threshold])

    # Heavier than all brackets — use the largest bracket price
    return float(zone_rates[sorted_thresholds[-1]])


def _table_option(weight_grams, country_code):
    """The static rate-table option (always available as a fallback)."""
    return {
        "carrier": "post",
        "service": "PostPac",
        "price_chf": calculate_shipping_chf(weight_grams, country_code),
        "source": "table",
    }


def get_shipping_options(weight_grams, country_code):
    """Return available shipping options for a destination (hybrid).

    Live carrier quotes are used when credentials are configured (DHL and/or
    Swiss Post); if none are available, falls back to a single option computed
    from the static rate table. Each option is a dict with keys ``carrier``,
    ``service``, ``price_chf`` and ``source`` (``"dhl"``/``"post"``/``"table"``).

    Prices are in CHF; satoshi conversion is left to the caller.
    """
    # Imported lazily to avoid import cycles and keep providers optional.
    from services import service_shipping_dhl, service_shipping_post

    options = []
    for provider in (service_shipping_dhl, service_shipping_post):
        try:
            quotes = provider.quote(weight_grams, country_code)
        except Exception:
            logger.exception("Shipping provider %s failed", getattr(provider, "CARRIER", "?"))
            quotes = None
        if quotes:
            options.extend(quotes)

    if not options:
        options = [_table_option(weight_grams, country_code)]

    options.sort(key=lambda opt: opt["price_chf"])
    return options
