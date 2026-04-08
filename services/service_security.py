"""Helpers for encrypting sensitive shipping data at rest."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

import config


def _derive_fernet_key():
    source = (config.SHIPPING_DATA_KEY or config.SECRET_KEY or "").strip()
    if not source:
        source = "sandlabs-default-shipping-key"
    digest = hashlib.sha256(source.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_FERNET = Fernet(_derive_fernet_key())


def encrypt_value(value):
    text = (value or "").strip()
    if not text:
        return ""
    return _FERNET.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_value(value):
    token = (value or "").strip()
    if not token:
        return ""
    try:
        return _FERNET.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return ""
