"""BTC price feed helpers for shipping and dynamic product pricing.

Fetches live rates from CoinGecko with a 5-minute in-process cache.
Falls back to the last known value on network errors.
"""
import json
import logging
import time
import urllib.request
from decimal import Decimal

logger = logging.getLogger(__name__)

_cache: dict = {"rates": {}, "timestamp": 0.0}
CACHE_TTL = 300  # seconds
SUPPORTED_RATE_CURRENCIES = ("chf", "brl", "usd", "eur")

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    f"?ids=bitcoin&vs_currencies={','.join(SUPPORTED_RATE_CURRENCIES)}"
)


def _get_btc_rates() -> dict:
    """Return cached BTC fiat rates keyed by currency code."""
    now = time.time()
    if _cache["rates"] and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["rates"]

    try:
        req = urllib.request.Request(COINGECKO_URL)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            bitcoin = data.get("bitcoin", {})
            rates = {
                code: float(bitcoin[code]) if bitcoin.get(code) else None
                for code in SUPPORTED_RATE_CURRENCIES
            }
            _cache["rates"] = rates
            _cache["timestamp"] = now
            return rates
    except Exception:
        logger.exception("Failed to fetch BTC fiat rates from CoinGecko")
        return _cache["rates"]


def get_btc_chf_rate() -> float | None:
    """Return current BTC price in CHF."""
    return _get_btc_rates().get("chf")


def get_btc_brl_rate() -> float | None:
    """Return current BTC price in BRL."""
    return _get_btc_rates().get("brl")


def get_btc_rate(currency_code: str) -> float | None:
    """Return current BTC price in the requested fiat currency."""
    return _get_btc_rates().get((currency_code or "").strip().lower())


def fiat_to_sats(amount: float | Decimal, currency_code: str) -> int:
    """Convert a fiat amount to satoshis at the current BTC/fiat rate."""
    rate = get_btc_rate(currency_code)
    if not rate or rate <= 0:
        return 0

    amount_decimal = Decimal(str(amount or 0))
    btc_amount = amount_decimal / Decimal(str(rate))
    return int(btc_amount * Decimal("100000000"))


def chf_to_sats(amount_chf: float) -> int:
    """Convert a CHF amount to satoshis at current BTC/CHF rate.

    Returns 0 if the rate is unavailable.
    """
    return fiat_to_sats(amount_chf, "CHF")


def brl_to_sats(amount_brl: float) -> int:
    """Convert a BRL amount to satoshis at current BTC/BRL rate."""
    return fiat_to_sats(amount_brl, "BRL")
