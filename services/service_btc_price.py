"""BTC price feed helpers for shipping and price display.

Fetches live rates from CoinGecko with a 5-minute in-process cache.
Falls back to the last known value on network errors.
"""
import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

_cache: dict = {"rates": {}, "timestamp": 0.0}
CACHE_TTL = 300  # seconds

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=chf,brl"
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
                "chf": float(bitcoin["chf"]) if bitcoin.get("chf") else None,
                "brl": float(bitcoin["brl"]) if bitcoin.get("brl") else None,
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


def chf_to_sats(amount_chf: float) -> int:
    """Convert a CHF amount to satoshis at current BTC/CHF rate.

    Returns 0 if the rate is unavailable.
    """
    rate = get_btc_chf_rate()
    if not rate or rate <= 0:
        return 0
    btc_amount = amount_chf / rate
    return int(btc_amount * 100_000_000)


def brl_to_sats(amount_brl: float) -> int:
    """Convert a BRL amount to satoshis at current BTC/BRL rate."""
    rate = get_btc_brl_rate()
    if not rate or rate <= 0:
        return 0
    btc_amount = amount_brl / rate
    return int(btc_amount * 100_000_000)
