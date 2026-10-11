"""Tests for Google sign-in (the token endpoint is always mocked)."""

import base64
import json
import time
import urllib.parse

import pytest


def _id_token(**overrides):
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "client-id",
        "exp": time.time() + 600,
        "nonce": "nonce-1",
        "sub": "google-sub-123",
        "email": "Buyer@Example.com",
        "email_verified": True,
        "name": "Buyer Example",
    }
    claims.update(overrides)
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"header.{body}.signature"


ATTEMPT = {"state": "state-1", "nonce": "nonce-1", "verifier": "verifier-1"}
REDIRECT = "https://store.example/auth/google/callback"


@pytest.fixture()
def google(tmp_db):
    from models.model_config import set_config
    from services import service_google_auth

    set_config("google_login_enabled", "1")
    set_config("google_client_id", "client-id")
    set_config("google_client_secret", "client-secret")
    return service_google_auth


class TestService:
    def test_disabled_without_flag_or_credentials(self, tmp_db):
        from models.model_config import set_config
        from services import service_google_auth

        assert service_google_auth.is_enabled() is False
        assert service_google_auth.authorization_url(REDIRECT, ATTEMPT) is None
        set_config("google_client_id", "client-id")
        set_config("google_client_secret", "client-secret")
        assert service_google_auth.is_enabled() is False
        set_config("google_login_enabled", "1")
        assert service_google_auth.is_enabled() is True

    def test_attempt_secrets_are_fresh(self, google):
        first, second = google.new_login_attempt(), google.new_login_attempt()
        assert set(first) == {"state", "nonce", "verifier"}
        assert first["state"] != second["state"] and first["verifier"] != second["verifier"]

    def test_authorization_url_carries_state_nonce_and_pkce(self, google):
        url = urllib.parse.urlsplit(google.authorization_url(REDIRECT, ATTEMPT))
        query = urllib.parse.parse_qs(url.query)

        assert f"{url.scheme}://{url.netloc}{url.path}" == "https://accounts.google.com/o/oauth2/v2/auth"
        assert query["client_id"] == ["client-id"]
        assert query["redirect_uri"] == [REDIRECT]
        assert query["response_type"] == ["code"]
        assert query["scope"] == ["openid email profile"]
        assert query["state"] == ["state-1"]
        assert query["nonce"] == ["nonce-1"]
        assert query["code_challenge_method"] == ["S256"]
        assert "client-secret" not in url.query

    def test_pkce_challenge_matches_rfc_7636_test_vector(self, google):
        attempt = {**ATTEMPT, "verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"}
        url = urllib.parse.urlsplit(google.authorization_url(REDIRECT, attempt))
        assert urllib.parse.parse_qs(url.query)["code_challenge"] == [
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        ]

    def test_exchange_returns_identity(self, google, monkeypatch):
        seen = {}

        def fake_post(url, form):
            seen.update(url=url, form=form)
            return {"id_token": _id_token()}

        monkeypatch.setattr(google, "_http_post", fake_post)

        assert google.exchange_code("the-code", REDIRECT, ATTEMPT) == {
            "sub": "google-sub-123", "email": "buyer@example.com", "name": "Buyer Example",
        }
        assert seen["url"] == "https://oauth2.googleapis.com/token"
        assert seen["form"] == {
            "grant_type": "authorization_code", "code": "the-code", "redirect_uri": REDIRECT,
            "client_id": "client-id", "client_secret": "client-secret", "code_verifier": "verifier-1",
        }

    @pytest.mark.parametrize("overrides", [
        {"iss": "https://evil.example"},
        {"aud": "another-client"},
        {"exp": 1},
        {"nonce": "other-nonce"},
        {"email_verified": False},
        {"sub": ""},
        {"email": ""},
    ])
    def test_exchange_rejects_bad_claims(self, google, monkeypatch, overrides):
        monkeypatch.setattr(google, "_http_post", lambda url, form: {"id_token": _id_token(**overrides)})
        assert google.exchange_code("the-code", REDIRECT, ATTEMPT) is None

    @pytest.mark.parametrize("response", [
        OSError("network down"),
        {"error": "invalid_grant"},
        {"id_token": "not-a-jwt"},
        {"id_token": "a." + base64.urlsafe_b64encode(b"[1]").decode() + ".c"},
    ])
    def test_exchange_survives_failures_without_leaking(self, google, monkeypatch, response, caplog):
        def fake_post(url, form):
            if isinstance(response, Exception):
                raise response
            return response

        monkeypatch.setattr(google, "_http_post", fake_post)
        with caplog.at_level("DEBUG"):
            assert google.exchange_code("the-code", REDIRECT, ATTEMPT) is None
        assert "client-secret" not in caplog.text and "the-code" not in caplog.text

    def test_exchange_needs_a_code(self, google, monkeypatch):
        monkeypatch.setattr(google, "_http_post", lambda url, form: pytest.fail("no request expected"))
        assert google.exchange_code("", REDIRECT, ATTEMPT) is None


def _start(client, next_url=""):
    resp = client.get("/auth/google" + (f"?next={next_url}" if next_url else ""))
    assert resp.status_code == 302
    return urllib.parse.parse_qs(urllib.parse.urlsplit(resp.headers["Location"]).query)


def _finish(client, google, monkeypatch, state, **claims):
    with client.session_transaction() as sess:
        nonce = sess["google_oauth"]["nonce"]
    monkeypatch.setattr(
        google, "_http_post",
        lambda url, form: {"id_token": _id_token(nonce=nonce, **claims)},
    )
    return client.get(f"/auth/google/callback?state={state}&code=the-code")


class TestRoutes:
    def test_routes_are_404_when_disabled(self, client):
        assert client.get("/auth/google").status_code == 404
        assert client.get("/auth/google/callback?state=x&code=y").status_code == 404

    def test_button_only_when_enabled(self, client, google):
        from models.model_config import set_config

        assert b"/auth/google" in client.get("/auth/login").data
        assert b"/auth/google" in client.get("/auth/register").data
        set_config("google_login_enabled", "0")
        assert b"/auth/google" not in client.get("/auth/login").data

    def test_start_redirects_to_google_with_session_secrets(self, client, google):
        query = _start(client)
        with client.session_transaction() as sess:
            stored = sess["google_oauth"]
        assert query["state"] == [stored["state"]]
        assert query["nonce"] == [stored["nonce"]]
        assert query["redirect_uri"][0].endswith("/auth/google/callback")

    def test_new_customer_is_created_and_signed_in(self, client, google, monkeypatch, db_conn):
        from models.model_users import get_user_by_email

        state = _start(client, "/carrinho")["state"][0]
        resp = _finish(client, google, monkeypatch, state)

        assert resp.status_code == 302 and resp.headers["Location"].endswith("/carrinho")
        user = get_user_by_email("buyer@example.com")
        assert user["display_name"] == "Buyer Example" and user["is_admin"] is False
        with client.session_transaction() as sess:
            assert sess["user_id"] == user["id"] and sess["is_admin"] is False
            assert "google_oauth" not in sess
        # Neither the Google id nor the email is stored in the clear.
        row = db_conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        assert all("google-sub-123" not in str(v) and "buyer@example.com" not in str(v) for v in tuple(row))

    def test_returning_google_user_gets_the_same_account(self, client, google, monkeypatch):
        from models.model_users import get_user_by_email

        _finish(client, google, monkeypatch, _start(client)["state"][0])
        first = get_user_by_email("buyer@example.com")["id"]
        client.post("/auth/logout", headers={"X-CSRFToken": _csrf(client)})

        # Same Google account, email changed on Google's side: matched by sub.
        _finish(client, google, monkeypatch, _start(client)["state"][0], email="renamed@example.com")
        with client.session_transaction() as sess:
            assert sess["user_id"] == first

    def test_existing_password_account_is_linked_and_old_password_dropped(self, client, google, monkeypatch):
        from models.model_users import create_user, verify_user

        user_id = create_user("buyer@example.com", "old-password", "Old Name")
        _finish(client, google, monkeypatch, _start(client)["state"][0])

        with client.session_transaction() as sess:
            assert sess["user_id"] == user_id
        assert verify_user("buyer@example.com", "old-password") is None

    def test_admin_accounts_cannot_use_google(self, client, google, monkeypatch):
        from models.model_users import create_user, get_user_by_google_sub

        create_user("buyer@example.com", "admin-password", "Boss", is_admin=True)
        resp = _finish(client, google, monkeypatch, _start(client)["state"][0])

        assert resp.status_code == 403
        assert get_user_by_google_sub("google-sub-123") is None
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_state_mismatch_is_rejected_and_attempt_consumed(self, client, google, monkeypatch):
        state = _start(client)["state"][0]
        monkeypatch.setattr(google, "_http_post", lambda url, form: pytest.fail("no exchange expected"))

        assert client.get("/auth/google/callback?state=forged&code=the-code").status_code == 400
        # The real state cannot be replayed after a failed attempt.
        assert client.get(f"/auth/google/callback?state={state}&code=the-code").status_code == 400
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_callback_without_started_attempt_is_rejected(self, client, google):
        assert client.get("/auth/google/callback?state=x&code=y").status_code == 400

    def test_cancelled_consent_shows_error(self, client, google, monkeypatch):
        state = _start(client)["state"][0]
        monkeypatch.setattr(google, "_http_post", lambda url, form: pytest.fail("no exchange expected"))
        assert client.get(f"/auth/google/callback?state={state}&error=access_denied").status_code == 400

    def test_rejected_token_does_not_sign_in(self, client, google, monkeypatch):
        state = _start(client)["state"][0]
        resp = _finish(client, google, monkeypatch, state, email_verified=False)
        assert resp.status_code == 400
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_external_next_is_not_followed(self, client, google, monkeypatch):
        state = _start(client, "https://evil.example/")["state"][0]
        resp = _finish(client, google, monkeypatch, state)
        assert resp.status_code == 302 and "evil.example" not in resp.headers["Location"]

    def test_redirect_uri_prefers_public_base_url(self, client, google, monkeypatch):
        import config

        monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://store.example")
        assert _start(client)["redirect_uri"] == ["https://store.example/auth/google/callback"]


def _csrf(client):
    with client.session_transaction() as sess:
        return sess.get("csrf_token", "")


class TestAdminSettings:
    FORM = {"whatsapp": "", "telegram": "", "shipping_rates": '{"CH":{"2":9}}'}

    def test_saves_client_and_keeps_secret_when_blank(self, admin_client, csrf_headers):
        from models.model_config import get_config

        admin_client.post("/admin/settings", headers=csrf_headers, data={
            **self.FORM, "google_login_enabled": "on",
            "google_client_id": "abc.apps.googleusercontent.com", "google_client_secret": "s3cret",
        })
        assert get_config("google_login_enabled") == "1"
        assert get_config("google_client_secret") == "s3cret"

        admin_client.post("/admin/settings", headers=csrf_headers, data={
            **self.FORM, "google_client_id": "abc.apps.googleusercontent.com",
        })
        assert get_config("google_login_enabled") == "0"
        assert get_config("google_client_secret") == "s3cret"

    def test_page_shows_redirect_uri_but_never_the_secret(self, admin_client):
        from models.model_config import set_config

        set_config("google_client_secret", "super-secret-value")
        html = admin_client.get("/admin/settings").data.decode()
        assert "/auth/google/callback" in html
        assert "super-secret-value" not in html
