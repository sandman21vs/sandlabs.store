"""DHL live shipping-rate provider.

Returns live quotes only when DHL credentials are configured in the admin
(``dhl_enabled`` + ``dhl_api_key``, optional ``dhl_api_url``). Real carrier
rating APIs require a commercial DHL account; without credentials this provider
returns ``None`` so the orchestrator falls back to the static rate table.

The parser is intentionally tolerant of a few response shapes so the endpoint
can be pointed at a real DHL rating endpoint (or a compatible proxy) via
``dhl_api_url`` without code changes.
"""

import json
import logging
import urllib.request

from models.model_config import get_bool_config, get_config

logger = logging.getLogger(__name__)

CARRIER = "dhl"
_DEFAULT_API_URL = "https://api.dhl.com/rates"


def _request(url, api_key, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _parse(result):
    """Normalize a DHL-ish response into a list of option dicts, or None."""
    if not result:
        return None

    raw_options = None
    if isinstance(result, list):
        raw_options = result
    elif isinstance(result, dict):
        raw_options = result.get("options") or result.get("rates")
        if raw_options is None and result.get("price_chf") is not None:
            raw_options = [result]

    if not raw_options:
        return None

    options = []
    for entry in raw_options:
        try:
            price_chf = round(float(entry["price_chf"]), 2)
        except (KeyError, TypeError, ValueError):
            continue
        options.append({
            "carrier": CARRIER,
            "service": entry.get("service") or "DHL",
            "price_chf": price_chf,
            "source": CARRIER,
        })
    return options or None


def quote(weight_grams, country_code):
    """Return a list of DHL shipping options, or None if unavailable."""
    if not get_bool_config("dhl_enabled", False):
        return None
    api_key = (get_config("dhl_api_key") or "").strip()
    if not api_key:
        return None

    api_url = (get_config("dhl_api_url") or _DEFAULT_API_URL).strip()
    payload = {
        "weight_grams": int(weight_grams or 0),
        "country": (country_code or "").upper().strip(),
        "currency": "CHF",
    }
    try:
        result = _request(api_url, api_key, payload)
        return _parse(result)
    except Exception:
        logger.exception("DHL rate request failed country=%s", payload["country"])
        return None
