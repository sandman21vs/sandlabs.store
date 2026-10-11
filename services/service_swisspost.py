"""Swiss Post Digital Commerce API client.

Covers what the API actually offers for a shop: OAuth2 client-credentials
tokens, address validation and address labels with a tracking code. It has no
price endpoint; shipping prices come from the rate table in
``service_shipping``.

The integration is off unless ``swisspost_enabled`` is set and client
credentials are stored (admin settings). Every public function returns
``None`` when the integration is off or the call fails, and never raises, so
checkout keeps working without Swiss Post.

Endpoints and field names follow the public documentation at
https://developer.post.ch/en/digital-commerce-api (read October 2026). They
have not been exercised against the live service from this codebase yet.

Privacy: address validation sends street, house number, postal code and city.
The recipient's name is never sent there. A label needs the full recipient
address including the name. No address data is logged in either case.

Labels cost money: outside test mode every generated label is a franked
consignment billed to the franking licence.
"""

import base64
import binascii
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
BARCODE_URL = "https://dcapi.apis.post.ch/barcode/v1/generateAddressLabel"
SCOPE_BARCODE = "DCAPI_BARCODE_READ"
LABEL_FILE_TYPE = "PDF"

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


def label_settings():
    """Return the label configuration, or ``None`` when labels cannot be made.

    Labels need the integration enabled plus a franking licence and a complete
    sender address. ``test_mode`` is on unless ``swisspost_label_live`` was
    switched on explicitly; in test mode Swiss Post returns SPECIMEN labels
    that are not billed and cannot be posted.
    """
    if not is_enabled():
        return None
    settings = {
        "franking_license": _clean(get_config("swisspost_franking_license")),
        "sender_name": _clean(get_config("swisspost_sender_name")),
        "sender_street": _clean(get_config("swisspost_sender_street")),
        "sender_zip": _clean(get_config("swisspost_sender_zip")),
        "sender_city": _clean(get_config("swisspost_sender_city")),
    }
    if not all(settings.values()):
        return None
    settings["test_mode"] = not get_bool_config("swisspost_label_live", False)
    return settings


def delivery_code(service_name):
    """Map a checkout service name to the Swiss Post basic service code."""
    return "PRI" if "priority" in (service_name or "").casefold() else "ECO"


def generate_label(recipient, service_name, weight_grams, item_id):
    """Create an A6 address label for a Swiss recipient.

    ``recipient`` needs ``name``, ``street``, ``house_number``, ``postal_code``
    and ``city``; ``address_extra`` is optional. Returns ``None`` when labels
    are not configured, the recipient is incomplete or the request fails.
    Otherwise::

        {"ident_code": str, "document": bytes, "file_type": "PDF", "test": bool}

    In test mode the label is a SPECIMEN and ``ident_code`` is not a usable
    tracking number.
    """
    settings = label_settings()
    if settings is None:
        return None

    to = {key: _clean(recipient.get(key)) for key in
          ("name", "street", "house_number", "postal_code", "city", "address_extra")}
    if not all(to[key] for key in ("name", "street", "house_number", "postal_code", "city")):
        return None

    recipient_block = {
        "name1": to["name"],
        "street": to["street"],
        "houseNo": to["house_number"],
        "zip": to["postal_code"],
        "city": to["city"],
        "country": "CH",
    }
    if to["address_extra"]:
        recipient_block["name2"] = to["address_extra"]

    result = _api_post(BARCODE_URL, SCOPE_BARCODE, {
        "language": "DE",
        "frankingLicense": settings["franking_license"],
        "ppFranking": False,
        "customer": {
            "name1": settings["sender_name"],
            "street": settings["sender_street"],
            "zip": settings["sender_zip"],
            "city": settings["sender_city"],
            "country": "CH",
        },
        "labelDefinition": {
            "labelLayout": "A6",
            "printAddresses": "RECIPIENT_AND_CUSTOMER",
            "imageFileType": LABEL_FILE_TYPE,
            "imageResolution": 300,
            "printPreview": settings["test_mode"],
        },
        "item": {
            "itemID": str(item_id),
            "recipient": recipient_block,
            "attributes": {
                "przl": [delivery_code(service_name)],
                "weight": max(1, int(weight_grams or 0)),
            },
        },
    })
    if not isinstance(result, dict):
        return None

    item = result.get("item") or {}
    labels = item.get("label") or []
    ident_code = _clean(item.get("identCode"))
    if not ident_code or not labels:
        # Error details can echo the address, so only the fact is logged.
        logger.error("Swiss Post label response had no label item_id=%s", item_id)
        return None
    try:
        document = base64.b64decode(labels[0], validate=True)
    except (binascii.Error, TypeError, ValueError):
        logger.error("Swiss Post label was not valid base64 item_id=%s", item_id)
        return None

    return {
        "ident_code": ident_code,
        "document": document,
        "file_type": LABEL_FILE_TYPE,
        "test": settings["test_mode"],
    }


def tracking_url(tracking_code):
    """Public Swiss Post tracking page for a consignment number."""
    code = _clean(tracking_code)
    if not code:
        return ""
    return "https://service.post.ch/ekp-web/ui/entry/search/" + urllib.parse.quote(code, safe="")
