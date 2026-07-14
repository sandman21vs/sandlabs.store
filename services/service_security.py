"""Helpers for encrypting sensitive PII at rest and deriving blind indexes.

The master key material is derived from a BIP39 mnemonic (``MASTER_MNEMONIC``)
so the operator can back it up as a familiar seed phrase. Everything below is
derived from that single secret:

- a Fernet key for symmetric encryption of PII (name, address, email, ...);
- a separate HMAC key for deterministic *blind indexes* (so an encrypted
  column can still be looked up / kept unique without storing plaintext).

Backward compatibility: values encrypted with the previous scheme (a Fernet key
derived from ``SHIPPING_DATA_KEY`` via SHA-256) are still decryptable through a
``MultiFernet``. New writes always use the seed-derived key; a migration
re-encrypts legacy rows.

Security note: deriving the key from a BIP39 seed is *not* cryptographically
stronger than a random key — the benefit is operator usability/backup.
Encryption at rest protects against database theft, not against a compromised
running server (which must hold the key in memory to decrypt for fulfilment).
"""

import base64
import hashlib
import hmac
import unicodedata

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

import config

# HKDF context labels — changing these rotates the derived keys.
_ENC_INFO = b"sandlabs/pii-encrypt/v1"
_BIDX_INFO = b"sandlabs/pii-blind-index/v1"
_DEV_FALLBACK = "sandlabs-default-shipping-key"


def _mnemonic_to_seed(mnemonic, passphrase=""):
    """BIP39 mnemonic -> 64-byte seed (PBKDF2-HMAC-SHA512, 2048 rounds).

    We accept any phrase (no wordlist/checksum validation) so operators are
    free to use a real BIP39 seed or any strong passphrase as entropy.
    """
    mnemonic_nfkd = unicodedata.normalize("NFKD", mnemonic).encode("utf-8")
    salt = ("mnemonic" + unicodedata.normalize("NFKD", passphrase)).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha512", mnemonic_nfkd, salt, 2048, dklen=64)


def _master_seed():
    """Return the master seed bytes from the strongest configured source."""
    mnemonic = (getattr(config, "MASTER_MNEMONIC", "") or "").strip()
    if mnemonic:
        passphrase = (getattr(config, "MASTER_MNEMONIC_PASSPHRASE", "") or "").strip()
        return _mnemonic_to_seed(mnemonic, passphrase)

    # Dev/legacy fallback so local runs and tests work without a mnemonic.
    source = (config.SHIPPING_DATA_KEY or config.SECRET_KEY or _DEV_FALLBACK).strip()
    return hashlib.sha512(source.encode("utf-8")).digest()


def _hkdf(seed, info, length=32):
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=None,
        info=info,
    ).derive(seed)


def _legacy_fernet():
    """Fernet from the previous SHA-256(SHIPPING_DATA_KEY) scheme, for reads."""
    source = (config.SHIPPING_DATA_KEY or config.SECRET_KEY or "").strip()
    if not source:
        source = _DEV_FALLBACK
    digest = hashlib.sha256(source.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _build_state():
    seed = _master_seed()
    enc_key = base64.urlsafe_b64encode(_hkdf(seed, _ENC_INFO))
    primary = Fernet(enc_key)
    # Encrypt with the seed-derived key; decrypt with it OR the legacy key.
    fernet = MultiFernet([primary, _legacy_fernet()])
    bidx_key = _hkdf(seed, _BIDX_INFO)
    return fernet, bidx_key


_FERNET, _BIDX_KEY = _build_state()


def is_using_secure_key():
    """True when a dedicated PII secret (mnemonic or SHIPPING_DATA_KEY) is set."""
    if (getattr(config, "MASTER_MNEMONIC", "") or "").strip():
        return True
    return bool((config.SHIPPING_DATA_KEY or "").strip())


def require_pii_key():
    """Raise if no dedicated PII secret is configured. Call in production."""
    if not is_using_secure_key():
        raise RuntimeError(
            "No PII encryption secret configured. Set MASTER_MNEMONIC "
            "(preferred) or SHIPPING_DATA_KEY before serving production traffic."
        )


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


def blind_index(value):
    """Deterministic, non-reversible index for exact-match lookups on PII.

    Returns a hex HMAC-SHA256 of the normalized value, or "" for empty input.
    """
    text = (value or "").strip()
    if not text:
        return ""
    return hmac.new(_BIDX_KEY, text.encode("utf-8"), hashlib.sha256).hexdigest()


def email_blind_index(email):
    """Blind index for an email address (lower-cased, stripped)."""
    return blind_index((email or "").strip().lower())
