"""Coinos.io API client for sandlabs.store.

Supports three settlement rails, all ultimately received in satoshis:

- ``lightning`` — bolt11 invoice; Coinos webhook fires on payment.
- ``liquid``    — Liquid address (per order); confirmed by polling.
- ``onchain``   — on-chain BTC address (per order); confirmed by polling.

For every rail we create a Coinos invoice and keep its ``hash``; payment is
detected uniformly via ``check_invoice(hash).received`` (and, for Lightning,
also via the webhook). On-chain/Liquid are gated behind admin toggles.
"""

import json
import logging
import re
import urllib.request

from models.model_config import get_coinos_config

logger = logging.getLogger(__name__)

COINOS_API_BASE = "https://coinos.io/api"
_COINOS_HASH_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")

# Public payment method -> Coinos invoice type.
PAYMENT_METHODS = {
    "lightning": "lightning",
    "liquid": "liquid",
    "onchain": "bitcoin",
}


def _coinos_request(method, path, body=None):
    api_key = get_coinos_config()["api_key"]
    if not api_key:
        return None

    url = f"{COINOS_API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        logger.exception("Coinos API request failed method=%s path=%s", method, path)
        return None


def get_enabled_methods():
    """Return the payment methods available given the current admin config.

    Lightning is available whenever Coinos is enabled; Liquid and on-chain are
    each behind their own toggle.
    """
    cfg = get_coinos_config()
    if not cfg["enabled"]:
        return []
    methods = ["lightning"]
    if cfg.get("liquid"):
        methods.append("liquid")
    if cfg.get("onchain"):
        methods.append("onchain")
    return methods


def create_invoice(amount_sats, invoice_type="lightning", webhook_url=None):
    """Create a Coinos invoice for the given amount and rail.

    ``invoice_type`` accepts a public method name ("lightning"/"liquid"/
    "onchain") or a raw Coinos type ("lightning"/"liquid"/"bitcoin").
    Returns the Coinos response ``{"hash": ..., "text": ...}`` where ``text`` is
    the bolt11 (Lightning) or the address (Liquid/on-chain), or ``None``.
    """
    coinos_config = get_coinos_config()
    if not coinos_config["enabled"]:
        return None
    if not amount_sats or int(amount_sats) < 1:
        return None

    coinos_type = PAYMENT_METHODS.get(invoice_type, invoice_type)
    if coinos_type not in ("lightning", "liquid", "bitcoin"):
        return None

    invoice_data = {"amount": int(amount_sats), "type": coinos_type}
    if webhook_url:
        if coinos_config["webhook_secret"]:
            invoice_data["secret"] = coinos_config["webhook_secret"]
        invoice_data["webhook"] = webhook_url

    return _coinos_request("POST", "/invoice", {"invoice": invoice_data})


def check_invoice(invoice_hash):
    if not invoice_hash:
        return None
    if not _COINOS_HASH_PATTERN.match(invoice_hash):
        return None
    return _coinos_request("GET", f"/invoice/{invoice_hash}")


def _fresh_address(coinos_type):
    """Create a 0-amount invoice of the given type; return its address hash."""
    if not get_coinos_config()["api_key"]:
        return None
    result = _coinos_request(
        "POST", "/invoice", {"invoice": {"amount": 0, "type": coinos_type}}
    )
    if result and "hash" in result:
        logger.info(
            "Coinos %s address generated address_suffix=%s",
            coinos_type,
            result["hash"][-8:],
        )
        return result["hash"]
    return None


def get_fresh_onchain_address():
    """Generate a fresh Coinos on-chain BTC address (0-amount bitcoin invoice)."""
    return _fresh_address("bitcoin")


def get_fresh_liquid_address():
    """Generate a fresh Coinos Liquid address (0-amount liquid invoice)."""
    return _fresh_address("liquid")


def get_received_sats():
    """Total incoming sats across all rails, or None on failure."""
    result = _coinos_request("GET", "/payments")
    if not result or "incoming" not in result:
        return None
    total_sats = 0
    for currency_data in result["incoming"].values():
        total_sats += currency_data.get("sats", 0)
    return total_sats
