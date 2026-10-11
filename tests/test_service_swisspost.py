"""Tests for services/service_swisspost.py (HTTP is always mocked)."""

import json
import urllib.parse

import pytest


@pytest.fixture()
def swisspost(tmp_db):
    from models.model_config import set_config
    from services import service_swisspost

    set_config("swisspost_enabled", "1")
    set_config("swisspost_client_id", "client-id")
    set_config("swisspost_client_secret", "client-secret")
    service_swisspost.reset_token_cache()
    yield service_swisspost
    service_swisspost.reset_token_cache()


class FakePost:
    """Stands in for ``_http_post``: records calls and replays responses."""

    def __init__(self, validation=None, expires_in=3600):
        self.calls = []
        self.validation = validation
        self.expires_in = expires_in

    def __call__(self, url, data, headers):
        self.calls.append((url, data, headers))
        if url.endswith("/OAuth/token"):
            return {"access_token": f"token-{len(self.token_calls)}", "expires_in": self.expires_in}
        if isinstance(self.validation, Exception):
            raise self.validation
        return self.validation

    @property
    def token_calls(self):
        return [call for call in self.calls if call[0].endswith("/OAuth/token")]

    @property
    def api_calls(self):
        return [call for call in self.calls if not call[0].endswith("/OAuth/token")]


def _certified(street="Wankdorfallee", house="4", zip_code="3030", city="Bern"):
    return {
        "quality": "CERTIFIED",
        "address": {"geographicLocation": {
            "house": {"street": street, "houseNumber": house},
            "zip": {"zip": zip_code, "city": city},
        }},
    }


ADDRESS = ("Wankdorfallee", "4", "3030", "Bern")


class TestEnabled:
    def test_disabled_by_default(self, tmp_db):
        from services import service_swisspost
        assert service_swisspost.is_enabled() is False
        assert service_swisspost.validate_address(*ADDRESS) is None

    def test_needs_flag_and_both_credentials(self, tmp_db):
        from models.model_config import set_config
        from services import service_swisspost

        set_config("swisspost_client_id", "client-id")
        set_config("swisspost_client_secret", "client-secret")
        assert service_swisspost.is_enabled() is False

        set_config("swisspost_enabled", "1")
        assert service_swisspost.is_enabled() is True

        set_config("swisspost_client_secret", "")
        assert service_swisspost.is_enabled() is False


class TestToken:
    def test_requests_client_credentials_token(self, swisspost, monkeypatch):
        fake = FakePost(validation=_certified())
        monkeypatch.setattr(swisspost, "_http_post", fake)

        swisspost.validate_address(*ADDRESS)

        url, data, headers = fake.token_calls[0]
        assert url == "https://api.post.ch/OAuth/token"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert urllib.parse.parse_qs(data.decode()) == {
            "grant_type": ["client_credentials"],
            "client_id": ["client-id"],
            "client_secret": ["client-secret"],
            "scope": ["DCAPI_ADDRESS_VALIDATE"],
        }
        assert fake.api_calls[0][2]["Authorization"] == "Bearer token-1"

    def test_token_is_cached_until_it_expires(self, swisspost, monkeypatch):
        fake = FakePost(validation=_certified())
        monkeypatch.setattr(swisspost, "_http_post", fake)

        swisspost.validate_address(*ADDRESS)
        swisspost.validate_address(*ADDRESS)
        assert len(fake.token_calls) == 1

        now = swisspost.time.time()
        monkeypatch.setattr(swisspost.time, "time", lambda: now + 3600)
        swisspost.validate_address(*ADDRESS)
        assert len(fake.token_calls) == 2

    def test_short_lived_token_is_not_cached(self, swisspost, monkeypatch):
        fake = FakePost(validation=_certified(), expires_in=30)
        monkeypatch.setattr(swisspost, "_http_post", fake)

        swisspost.validate_address(*ADDRESS)
        swisspost.validate_address(*ADDRESS)
        assert len(fake.token_calls) == 2

    def test_changed_client_id_invalidates_cached_token(self, swisspost, monkeypatch):
        from models.model_config import set_config

        fake = FakePost(validation=_certified())
        monkeypatch.setattr(swisspost, "_http_post", fake)

        swisspost.validate_address(*ADDRESS)
        set_config("swisspost_client_id", "other-client")
        swisspost.validate_address(*ADDRESS)
        assert len(fake.token_calls) == 2

    def test_token_failure_returns_none_without_calling_the_api(self, swisspost, monkeypatch):
        calls = []

        def boom(url, data, headers):
            calls.append(url)
            raise OSError("network down")

        monkeypatch.setattr(swisspost, "_http_post", boom)
        assert swisspost.validate_address(*ADDRESS) is None
        assert calls == ["https://api.post.ch/OAuth/token"]


class TestValidateAddress:
    def test_sends_address_without_any_name(self, swisspost, monkeypatch):
        fake = FakePost(validation=_certified())
        monkeypatch.setattr(swisspost, "_http_post", fake)

        swisspost.validate_address("  Wankdorfallee ", "4", "3030", "Bern")

        url, data, _headers = fake.api_calls[0]
        assert url == "https://dcapi.apis.post.ch/address/v1/addresses/validation"
        assert json.loads(data) == {
            "geographicLocation": {
                "house": {"street": "Wankdorfallee", "houseNumber": "4"},
                "zip": {"zip": "3030", "city": "Bern"},
            },
            "fullValidation": False,
        }

    def test_matching_certified_address_is_valid(self, swisspost, monkeypatch):
        monkeypatch.setattr(swisspost, "_http_post", FakePost(validation=_certified()))
        assert swisspost.validate_address("wankdorfallee", "4", "3030", "BERN") == {
            "status": "valid", "suggestion": None,
        }

    def test_certified_with_different_spelling_is_corrected(self, swisspost, monkeypatch):
        monkeypatch.setattr(swisspost, "_http_post", FakePost(validation=_certified()))
        assert swisspost.validate_address("Wankdorfalle", "4", "3030", "Bern") == {
            "status": "corrected",
            "suggestion": {
                "street": "Wankdorfallee", "house_number": "4",
                "postal_code": "3030", "city": "Bern",
            },
        }

    def test_certified_without_address_block_is_valid(self, swisspost, monkeypatch):
        monkeypatch.setattr(swisspost, "_http_post", FakePost(validation={"quality": "CERTIFIED"}))
        assert swisspost.validate_address(*ADDRESS)["status"] == "valid"

    def test_uncertified_quality_is_unknown(self, swisspost, monkeypatch):
        monkeypatch.setattr(swisspost, "_http_post", FakePost(validation={"quality": "UNUSABLE"}))
        assert swisspost.validate_address(*ADDRESS) == {"status": "unknown", "suggestion": None}

    def test_incomplete_input_is_not_sent(self, swisspost, monkeypatch):
        fake = FakePost(validation=_certified())
        monkeypatch.setattr(swisspost, "_http_post", fake)
        assert swisspost.validate_address("Wankdorfallee", "", "3030", "Bern") is None
        assert fake.calls == []

    def test_api_error_returns_none(self, swisspost, monkeypatch):
        monkeypatch.setattr(swisspost, "_http_post", FakePost(validation=TimeoutError("slow")))
        assert swisspost.validate_address(*ADDRESS) is None

    def test_unexpected_response_shape_returns_none(self, swisspost, monkeypatch):
        monkeypatch.setattr(swisspost, "_http_post", FakePost(validation=["not", "a", "dict"]))
        assert swisspost.validate_address(*ADDRESS) is None

    def test_failures_do_not_log_address_or_secret(self, swisspost, monkeypatch, caplog):
        monkeypatch.setattr(swisspost, "_http_post", FakePost(validation=TimeoutError("slow")))
        with caplog.at_level("DEBUG"):
            swisspost.validate_address("Geheimstrasse", "7", "8000", "Zürich")
        assert "Geheimstrasse" not in caplog.text
        assert "client-secret" not in caplog.text


class TestValidateAddressRoute:
    URL = "/api/shipping/validate-address"
    BODY = {"country": "CH", "street": "Wankdorfallee", "house_number": "4",
            "postal_code": "3030", "city": "Bern"}

    def test_requires_csrf(self, client):
        assert client.post(self.URL, json=self.BODY).status_code == 403

    def test_not_checked_when_integration_is_off(self, client, csrf_headers):
        resp = client.post(self.URL, json=self.BODY, headers=csrf_headers)
        assert resp.get_json() == {"ok": True, "checked": False}

    def test_returns_service_result(self, client, csrf_headers, monkeypatch):
        from services import service_swisspost

        seen = {}
        monkeypatch.setattr(service_swisspost, "is_enabled", lambda: True)
        monkeypatch.setattr(
            service_swisspost, "validate_address",
            lambda **fields: seen.update(fields) or {"status": "valid", "suggestion": None},
        )

        resp = client.post(self.URL, json=self.BODY, headers=csrf_headers)
        assert resp.get_json() == {"ok": True, "checked": True, "status": "valid", "suggestion": None}
        assert seen == {"street": "Wankdorfallee", "house_number": "4",
                        "postal_code": "3030", "city": "Bern"}

    @pytest.mark.parametrize("override", [
        {"country": "DE"},
        {"street": ""},
        {"city": "x" * 121},
    ])
    def test_skips_non_swiss_incomplete_or_oversized_input(self, client, csrf_headers, monkeypatch, override):
        from services import service_swisspost

        monkeypatch.setattr(service_swisspost, "is_enabled", lambda: True)
        monkeypatch.setattr(
            service_swisspost, "validate_address",
            lambda **fields: pytest.fail("the service must not be called"),
        )

        resp = client.post(self.URL, json={**self.BODY, **override}, headers=csrf_headers)
        assert resp.get_json() == {"ok": True, "checked": False}

    def test_lookup_failure_is_reported_as_not_checked(self, client, csrf_headers, monkeypatch):
        from services import service_swisspost

        monkeypatch.setattr(service_swisspost, "is_enabled", lambda: True)
        monkeypatch.setattr(service_swisspost, "validate_address", lambda **fields: None)

        resp = client.post(self.URL, json=self.BODY, headers=csrf_headers)
        assert resp.get_json() == {"ok": True, "checked": False}

    def test_lookups_are_capped_per_session(self, client, csrf_headers, monkeypatch):
        from routes import routes_checkout
        from services import service_swisspost

        calls = []
        monkeypatch.setattr(routes_checkout, "_MAX_ADDRESS_CHECKS_PER_SESSION", 2)
        monkeypatch.setattr(service_swisspost, "is_enabled", lambda: True)
        monkeypatch.setattr(
            service_swisspost, "validate_address",
            lambda **fields: calls.append(1) or {"status": "valid", "suggestion": None},
        )

        results = [
            client.post(self.URL, json=self.BODY, headers=csrf_headers).get_json()["checked"]
            for _ in range(3)
        ]
        assert results == [True, True, False]
        assert len(calls) == 2


class TestAdminSwissPostSettings:
    FORM = {"whatsapp": "", "telegram": "", "shipping_rates": '{"CH":{"2":9}}'}

    def _post(self, admin_client, csrf_headers, data):
        return admin_client.post("/admin/settings", data={**self.FORM, **data}, headers=csrf_headers)

    def test_saves_credentials_and_flag(self, admin_client, csrf_headers):
        from models.model_config import get_config

        resp = self._post(admin_client, csrf_headers, {
            "swisspost_enabled": "on",
            "swisspost_client_id": "abc",
            "swisspost_client_secret": "s3cret",
        })
        assert resp.status_code == 302
        assert get_config("swisspost_enabled") == "1"
        assert get_config("swisspost_client_id") == "abc"
        assert get_config("swisspost_client_secret") == "s3cret"

    def test_blank_secret_keeps_the_stored_one(self, admin_client, csrf_headers):
        from models.model_config import get_config, set_config

        set_config("swisspost_client_secret", "kept")
        self._post(admin_client, csrf_headers, {"swisspost_client_id": "abc"})

        assert get_config("swisspost_client_secret") == "kept"
        assert get_config("swisspost_enabled") == "0"

    def test_secret_is_never_rendered(self, admin_client):
        from models.model_config import set_config

        set_config("swisspost_client_secret", "super-secret-value")
        html = admin_client.get("/admin/settings").data.decode()
        assert "super-secret-value" not in html
        assert 'name="swisspost_client_secret"' in html
