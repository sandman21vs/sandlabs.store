"""Shipping cost calculator.

Prices come from a rate table stored in the config table (key
``shipping_rates``) and editable in the admin. Swiss Post publishes no price
API, so its PostPac prices live in this table. Live carrier quotes (DHL) are
added on top when credentials are configured.

A zone maps either weight brackets to prices (one unnamed service)::

    "EU": {"2": 20.0, "5": 30.0}

or service names to their own brackets (several options at checkout)::

    "CH": {"PostPac Economy": {"2": 9.0}, "PostPac Priority": {"2": 10.5}}

Bracket keys are the maximum weight in kg; prices are in CHF.
"""
import json
import logging

import db

logger = logging.getLogger(__name__)

TABLE_CARRIER = "post"
DEFAULT_SERVICE = "PostPac"

# Swiss Post list prices in CHF incl. VAT (post.ch, checked October 2026).
DEFAULT_RATES = {
    "CH": {
        "PostPac Economy": {2: 9.00, 10: 12.00, 30: 21.00},
        "PostPac Priority": {2: 10.50, 10: 13.50, 30: 22.50},
    },
    "EU":    {2: 20.00, 5: 30.00, 10: 45.00, 30: 80.00},
    "WORLD": {2: 30.00, 5: 50.00, 10: 75.00, 30: 120.00},
}

# The single-service table shipped before PostPac Economy/Priority were split.
# init_db drops a stored copy of it so untouched installs pick up DEFAULT_RATES.
LEGACY_DEFAULT_RATES = {
    "CH":    {"2": 7.0, "10": 9.5, "30": 16.0},
    "EU":    {"2": 20.0, "5": 30.0, "10": 45.0, "30": 80.0},
    "WORLD": {"2": 30.0, "5": 50.0, "10": 75.0, "30": 120.0},
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


def default_rates_json() -> str:
    """DEFAULT_RATES as pretty JSON, for the admin editor."""
    return json.dumps(DEFAULT_RATES, indent=2, ensure_ascii=False)


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
            rates = json.loads(row["value"])
            if isinstance(rates, dict):
                return rates
    except Exception:
        logger.exception("Failed to load shipping rates from DB")
    return DEFAULT_RATES


def _zone_services(zone_rates) -> dict:
    """Normalize a zone to ``{service_name: {threshold: price}}``."""
    if not isinstance(zone_rates, dict) or not zone_rates:
        return {}
    if all(isinstance(value, dict) for value in zone_rates.values()):
        return {name: brackets for name, brackets in zone_rates.items() if brackets}
    if any(isinstance(value, dict) for value in zone_rates.values()):
        logger.warning("Shipping zone mixes brackets and services; ignoring it")
        return {}
    return {DEFAULT_SERVICE: zone_rates}


def _bracket_price(brackets, weight_grams):
    """Price of the smallest bracket covering the weight, or None if unusable."""
    try:
        thresholds = sorted(brackets.keys(), key=float)
        weight_kg = (weight_grams or 0) / 1000.0
        for threshold in thresholds:
            if weight_kg <= float(threshold):
                return float(brackets[threshold])
        # Heavier than all brackets — use the largest bracket price
        return float(brackets[thresholds[-1]])
    except (TypeError, ValueError, IndexError):
        logger.warning("Shipping brackets are malformed; skipping them")
        return None


def get_table_options(weight_grams, country_code):
    """Rate-table options for a destination, one per configured service."""
    rates = get_shipping_rates()
    zone_rates = rates.get(get_country_zone(country_code)) or rates.get("WORLD") or {}
    options = []
    for service, brackets in _zone_services(zone_rates).items():
        price = _bracket_price(brackets, weight_grams)
        if price is None:
            continue
        options.append({
            "carrier": TABLE_CARRIER,
            "service": service,
            "price_chf": price,
            "source": "table",
        })
    return options


def calculate_shipping_chf(weight_grams: int, country_code: str) -> float:
    """Cheapest rate-table price in CHF for a destination.

    Args:
        weight_grams: Total shipment weight in grams.
        country_code: ISO 3166-1 alpha-2 country code (e.g. 'CH', 'DE', 'BR').

    Returns:
        Shipping cost in CHF (float). Returns 0.0 if rates are empty.
    """
    options = get_table_options(weight_grams, country_code)
    if not options:
        return 0.0
    return min(opt["price_chf"] for opt in options)


def get_shipping_options(weight_grams, country_code):
    """Return available shipping options for a destination, cheapest first.

    Rate-table options are always offered. Live DHL quotes are added when DHL
    credentials are configured; a failing carrier never removes the table
    options. Each option is a dict with keys ``carrier``, ``service``,
    ``price_chf`` and ``source`` (``"table"`` or the live carrier name).

    Prices are in CHF; satoshi conversion is left to the caller.
    """
    # Imported lazily to avoid import cycles and keep providers optional.
    from services import service_shipping_dhl

    options = get_table_options(weight_grams, country_code)
    for provider in (service_shipping_dhl,):
        try:
            quotes = provider.quote(weight_grams, country_code)
        except Exception:
            logger.exception("Shipping provider %s failed", getattr(provider, "CARRIER", "?"))
            quotes = None
        if quotes:
            options.extend(quotes)

    if not options:
        # Empty or unusable table: keep checkout working with a zero-cost line
        # the admin will notice, rather than failing the order.
        logger.error("No shipping options available; check the shipping rate table")
        options = [{
            "carrier": TABLE_CARRIER,
            "service": DEFAULT_SERVICE,
            "price_chf": 0.0,
            "source": "table",
        }]

    options.sort(key=lambda opt: opt["price_chf"])
    return options
