"""Sign in with Google (OpenID Connect authorization-code flow).

Off unless ``google_login_enabled`` is set and an OAuth client id and secret
are stored (admin settings). The browser is sent to Google with ``state``, a
``nonce`` and a PKCE challenge; the callback exchanges the code server-side.

The ID token is read straight from Google's token endpoint over TLS, which
OpenID Connect Core 3.1.3.7 accepts in place of checking the token signature.
Its claims are still validated: issuer, audience, expiry, nonce and a
verified email.

Nothing here logs tokens, codes, emails or the client secret.
"""

import base64
import hashlib
import json
import logging
import secrets
import time
import urllib.parse
import urllib.request

from models.model_config import get_bool_config, get_config

logger = logging.getLogger(__name__)

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
_TIMEOUT = 10


def _credentials():
    """Return ``(client_id, client_secret)`` or ``None`` when not usable."""
    if not get_bool_config("google_login_enabled", False):
        return None
    client_id = (get_config("google_client_id") or "").strip()
    client_secret = (get_config("google_client_secret") or "").strip()
    if not client_id or not client_secret:
        return None
    return client_id, client_secret


def is_enabled():
    """True when Google sign-in is switched on and has credentials."""
    return _credentials() is not None


def new_login_attempt():
    """Fresh per-attempt secrets to keep in the visitor's session."""
    return {
        "state": secrets.token_urlsafe(32),
        "nonce": secrets.token_urlsafe(32),
        "verifier": secrets.token_urlsafe(64),
    }


def _code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def authorization_url(redirect_uri, attempt):
    """URL to send the browser to, or ``None`` when sign-in is off."""
    credentials = _credentials()
    if credentials is None:
        return None
    query = urllib.parse.urlencode({
        "client_id": credentials[0],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": attempt["state"],
        "nonce": attempt["nonce"],
        "code_challenge": _code_challenge(attempt["verifier"]),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    })
    return f"{AUTHORIZATION_URL}?{query}"


def _http_post(url, form):
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read())


def _decode_claims(id_token):
    payload = id_token.split(".")[1]
    padded = payload + "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(padded))
    if not isinstance(claims, dict):
        raise ValueError("ID token payload is not an object")
    return claims


def exchange_code(code, redirect_uri, attempt):
    """Trade an authorization code for the signed-in Google identity.

    Returns ``{"sub", "email", "name"}`` or ``None`` when sign-in is off, the
    exchange fails, or the ID token does not check out (wrong issuer or
    audience, expired, nonce mismatch, unverified email).
    """
    credentials = _credentials()
    if credentials is None or not code:
        return None
    client_id, client_secret = credentials

    try:
        result = _http_post(TOKEN_URL, {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": attempt["verifier"],
        })
        claims = _decode_claims(result["id_token"])
    except Exception as exc:
        # The exception text can echo the request, which carries the secret.
        logger.error("Google token exchange failed: %s", type(exc).__name__)
        return None

    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    try:
        expires_at = float(claims.get("exp") or 0)
    except (TypeError, ValueError):
        expires_at = 0

    problem = None
    if claims.get("iss") not in _ISSUERS:
        problem = "issuer"
    elif client_id not in audiences:
        problem = "audience"
    elif expires_at <= time.time():
        problem = "expired"
    elif not secrets.compare_digest(str(claims.get("nonce") or ""), attempt["nonce"]):
        problem = "nonce"
    elif claims.get("email_verified") not in (True, "true"):
        problem = "email_unverified"
    elif not claims.get("sub") or not claims.get("email"):
        problem = "missing_claims"
    if problem:
        logger.warning("Google ID token rejected reason=%s", problem)
        return None

    return {
        "sub": str(claims["sub"]),
        "email": str(claims["email"]).strip().lower(),
        "name": str(claims.get("name") or "").strip(),
    }
