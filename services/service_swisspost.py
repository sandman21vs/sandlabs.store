"""Swiss Post Digital Commerce API client.

Covers what the API actually offers for a shop: OAuth2 client-credentials
tokens and address validation. It has no price endpoint; shipping prices come
from the rate table in ``service_shipping``.

The integration is off unless ``swisspost_enabled`` is set and client
credentials are stored (admin settings). Every public function returns
``None`` when the integration is off or the call fails, and never raises, so
checkout keeps working without Swiss Post.

Endpoints and field names follow the public documentation at
https://developer.post.ch/en/digital-commerce-api (read October 2026). They
have not been exercised against the live service from this codebase yet.

Privacy: address validation sends street, house number, postal code and city.
The recipient's name is never sent, and no address data is logged.
"""

import json
import logging
import threading
import time
import urllib.parse
import urllib.request

from models.model_config import get_bool_config, get_config

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.post.ch/OAuth/token"
ADDRESS_VALIDATION_URL = "https://dcapi.apis.post.ch/address/v1/addresses/validation"
SCOPE_ADDRESS_VALIDATE = "DCAPI_ADDRESS_VALIDATE"

_TIMEOUT = 10
_TOKEN_EXPIRY_MARGIN = 60  # refresh this many seconds before the token expires
_token_cache = {}          # scope -> (client_id, access_token, expires_at)
_token_lock = threading.Lock()


def _credentials():
    """Return ``(client_id, client_secret)`` or ``None`` when not usable."""
    if not get_bool_config("swisspost_enabled", False):
        return None
    client_id = (get_config("swisspost_client_id") or "").strip()
    client_secret = (get_config("swisspost_client_secret") or "").strip()
    if not client_id or not client_secret:
        return None
    return client_id, client_secret


def is_enabled():
    """True when the integration is switched on and has credentials."""
    return _credentials() is not None


def _http_post(url, data, headers):
    req = urllib.request.Request(url, data=data, method="POST")
    for name, value in headers.items():
        req.add_header(name, value)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read())


def reset_token_cache():
    """Forget cached tokens (credentials changed, or tests)."""
    with _token_lock:
        _token_cache.clear()


def _get_token(scope):
    """Return a bearer token for ``scope``, or ``None``."""
    credentials = _credentials()
    if credentials is None:
        return None
    client_id, client_secret = credentials

    with _token_lock:
        cached = _token_cache.get(scope)
        if cached and cached[0] == client_id and cached[2] > time.time():
            return cached[1]

        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope,
        }).encode()
        try:
            result = _http_post(
                TOKEN_URL, body, {"Content-Type": "application/x-www-form-urlencoded"}
            )
            token = result["access_token"]
            lifetime = int(result.get("expires_in") or 0)
        except Exception:
            # Never log the request body: it carries the client secret.
            logger.exception("Swiss Post token request failed scope=%s", scope)
            return None

        if lifetime > _TOKEN_EXPIRY_MARGIN:
            _token_cache[scope] = (client_id, token, time.time() + lifetime - _TOKEN_EXPIRY_MARGIN)
        return token


def _api_post(url, scope, payload):
    token = _get_token(scope)
    if not token:
        return None
    try:
        return _http_post(
            url,
            json.dumps(payload).encode(),
            {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
    except Exception:
        # The payload holds customer address data; log the endpoint only.
        logger.exception("Swiss Post API request failed url=%s", url)
        return None


def _clean(value):
    return " ".join(str(value or "").split())


def _same(left, right):
    return _clean(left).casefold() == _clean(right).casefold()


def validate_address(street, house_number, postal_code, city):
    """Check a Swiss address against Swiss Post.

    Returns ``None`` when the integration is off, the input is incomplete or
    the request fails. Otherwise a dict::

        {"status": "valid" | "corrected" | "unknown",
         "suggestion": {"street", "house_number", "postal_code", "city"} | None}

    ``corrected`` means Swiss Post recognised the address but returned it
    spelled differently; ``suggestion`` then holds its version. ``unknown``
    means it could not confirm the address. The result is advisory only.
    """
    entered = {
        "street": _clean(street),
        "house_number": _clean(house_number),
        "postal_code": _clean(postal_code),
        "city": _clean(city),
    }
    if not all(entered.values()):
        return None

    result = _api_post(ADDRESS_VALIDATION_URL, SCOPE_ADDRESS_VALIDATE, {
        "geographicLocation": {
            "house": {"street": entered["street"], "houseNumber": entered["house_number"]},
            "zip": {"zip": entered["postal_code"], "city": entered["city"]},
        },
        # Full validation also checks the addressee, which we do not send.
        "fullValidation": False,
    })
    if not isinstance(result, dict):
        return None

    quality = str(result.get("quality") or "").upper()
    if "CERTIFIED" not in quality:
        return {"status": "unknown", "suggestion": None}

    location = (result.get("address") or {}).get("geographicLocation") or {}
    house = location.get("house") or {}
    zip_info = location.get("zip") or {}
    returned = {
        "street": _clean(house.get("street")),
        "house_number": _clean(house.get("houseNumber")),
        "postal_code": _clean(zip_info.get("zip")),
        "city": _clean(zip_info.get("city")),
    }
    # A certified answer without an address block confirms what was entered.
    if not any(returned.values()):
        return {"status": "valid", "suggestion": None}

    suggestion = {key: returned[key] or entered[key] for key in entered}
    if all(_same(suggestion[key], entered[key]) for key in entered):
        return {"status": "valid", "suggestion": None}
    return {"status": "corrected", "suggestion": suggestion}
