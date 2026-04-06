"""BTC/CHF price feed for shipping cost conversion.

Fetches live rate from CoinGecko with a 5-minute in-process cache.
Falls back to the last known value on network errors.
"""
import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

_cache: dict = {"rate": None, "timestamp": 0.0}
CACHE_TTL = 300  # seconds

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=chf"
)


def get_btc_chf_rate() -> float | None:
    """Return current BTC price in CHF.

    Uses an in-process cache (TTL 5 minutes) to avoid hammering
    the CoinGecko free tier. Returns None if no rate is available
    (first call with network failure).
    """
    now = time.time()
    if _cache["rate"] is not None and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["rate"]

    try:
        req = urllib.request.Request(COINGECKO_URL)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            rate = float(data["bitcoin"]["chf"])
            _cache["rate"] = rate
            _cache["timestamp"] = now
            return rate
    except Exception:
        logger.exception("Failed to fetch BTC/CHF rate from CoinGecko")
        return _cache["rate"]  # last known value, may be None


def chf_to_sats(amount_chf: float) -> int:
    """Convert a CHF amount to satoshis at current BTC/CHF rate.

    Returns 0 if the rate is unavailable.
    """
    rate = get_btc_chf_rate()
    if not rate or rate <= 0:
        return 0
    btc_amount = amount_chf / rate
    return int(btc_amount * 100_000_000)
