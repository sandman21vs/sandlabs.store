"""Swiss Post live shipping-rate provider.

Returns live quotes only when Swiss Post credentials are configured in the
admin (``post_enabled`` + ``post_api_key``, optional ``post_api_url``). Real
Swiss Post rating APIs require a business account; without credentials this
provider returns ``None`` so the orchestrator falls back to the static rate
table (which itself models Swiss Post PostPac rates).
"""

import json
import logging
import urllib.request

from models.model_config import get_bool_config, get_config

logger = logging.getLogger(__name__)

CARRIER = "post"
_DEFAULT_API_URL = "https://api.post.ch/rates"


def _request(url, api_key, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _parse(result):
    """Normalize a Swiss-Post-ish response into a list of option dicts, or None."""
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
            "service": entry.get("service") or "PostPac",
            "price_chf": price_chf,
            "source": CARRIER,
        })
    return options or None


def quote(weight_grams, country_code):
    """Return a list of Swiss Post shipping options, or None if unavailable."""
    if not get_bool_config("post_enabled", False):
        return None
    api_key = (get_config("post_api_key") or "").strip()
    if not api_key:
        return None

    api_url = (get_config("post_api_url") or _DEFAULT_API_URL).strip()
    payload = {
        "weight_grams": int(weight_grams or 0),
        "country": (country_code or "").upper().strip(),
        "currency": "CHF",
    }
    try:
        result = _request(api_url, api_key, payload)
        return _parse(result)
    except Exception:
        logger.exception("Swiss Post rate request failed")
        return None
