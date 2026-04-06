"""Coinos.io API client for sandlabs.store."""

import json
import logging
import re
import urllib.request

from models.model_config import get_coinos_config

logger = logging.getLogger(__name__)

COINOS_API_BASE = "https://coinos.io/api"
_COINOS_HASH_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")


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


def create_invoice(amount_sats, invoice_type="lightning", webhook_url=None):
    coinos_config = get_coinos_config()
    if not coinos_config["enabled"]:
        return None
    if not amount_sats or int(amount_sats) < 1:
        return None
    if invoice_type not in ("lightning", "liquid"):
        return None

    invoice_data = {"amount": int(amount_sats), "type": invoice_type}
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
