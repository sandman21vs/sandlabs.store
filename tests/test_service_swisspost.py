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


# ── Labels ────────────────────────────────────────────────────────────────────

RECIPIENT = {
    "name": "Anna Muster", "street": "Wankdorfallee", "house_number": "4",
    "postal_code": "3030", "city": "Bern", "address_extra": "",
}
LABEL_BYTES = b"%PDF-1.4 specimen label"


def _label_response(ident="996012345600000017"):
    import base64
    return {"item": {"itemID": "7", "identCode": ident,
                     "label": [base64.b64encode(LABEL_BYTES).decode()]}}


@pytest.fixture()
def swisspost_labels(swisspost):
    from models.model_config import set_config

    set_config("swisspost_franking_license", "60012345")
    set_config("swisspost_sender_name", "Sandlabs")
    set_config("swisspost_sender_street", "Musterweg 1")
    set_config("swisspost_sender_zip", "8000")
    set_config("swisspost_sender_city", "Zürich")
    return swisspost


class TestLabelSettings:
    def test_none_until_licence_and_sender_are_complete(self, swisspost):
        from models.model_config import set_config

        assert swisspost.label_settings() is None
        set_config("swisspost_franking_license", "60012345")
        set_config("swisspost_sender_name", "Sandlabs")
        set_config("swisspost_sender_street", "Musterweg 1")
        set_config("swisspost_sender_zip", "8000")
        assert swisspost.label_settings() is None
        set_config("swisspost_sender_city", "Zürich")
        assert swisspost.label_settings()["franking_license"] == "60012345"

    def test_test_mode_unless_live_is_switched_on(self, swisspost_labels):
        from models.model_config import set_config

        assert swisspost_labels.label_settings()["test_mode"] is True
        set_config("swisspost_label_live", "1")
        assert swisspost_labels.label_settings()["test_mode"] is False

    def test_delivery_code(self, swisspost):
        assert swisspost.delivery_code("PostPac Priority") == "PRI"
        assert swisspost.delivery_code("PostPac Economy") == "ECO"
        assert swisspost.delivery_code(None) == "ECO"

    def test_tracking_url(self, swisspost):
        assert swisspost.tracking_url("99.60.123456.00000017") == (
            "https://service.post.ch/ekp-web/ui/entry/search/99.60.123456.00000017"
        )
        assert swisspost.tracking_url("a b/c") == "https://service.post.ch/ekp-web/ui/entry/search/a%20b%2Fc"
        assert swisspost.tracking_url("") == ""


class TestGenerateLabel:
    def test_builds_specimen_request_by_default(self, swisspost_labels, monkeypatch):
        fake = FakePost(validation=_label_response())
        monkeypatch.setattr(swisspost_labels, "_http_post", fake)

        result = swisspost_labels.generate_label(RECIPIENT, "PostPac Priority", 400, 7)

        assert result == {"ident_code": "996012345600000017", "document": LABEL_BYTES,
                          "file_type": "PDF", "test": True}
        token_form = urllib.parse.parse_qs(fake.token_calls[0][1].decode())
        assert token_form["scope"] == ["DCAPI_BARCODE_READ"]
        url, data, _headers = fake.api_calls[0]
        assert url == "https://dcapi.apis.post.ch/barcode/v1/generateAddressLabel"
        assert json.loads(data) == {
            "language": "DE",
            "frankingLicense": "60012345",
            "ppFranking": False,
            "customer": {"name1": "Sandlabs", "street": "Musterweg 1", "zip": "8000",
                         "city": "Zürich", "country": "CH"},
            "labelDefinition": {"labelLayout": "A6", "printAddresses": "RECIPIENT_AND_CUSTOMER",
                                "imageFileType": "PDF", "imageResolution": 300, "printPreview": True},
            "item": {
                "itemID": "7",
                "recipient": {"name1": "Anna Muster", "street": "Wankdorfallee", "houseNo": "4",
                              "zip": "3030", "city": "Bern", "country": "CH"},
                "attributes": {"przl": ["PRI"], "weight": 400},
            },
        }

    def test_live_mode_and_address_extra(self, swisspost_labels, monkeypatch):
        from models.model_config import set_config

        set_config("swisspost_label_live", "1")
        fake = FakePost(validation=_label_response())
        monkeypatch.setattr(swisspost_labels, "_http_post", fake)

        result = swisspost_labels.generate_label({**RECIPIENT, "address_extra": "c/o Beispiel"}, "PostPac Economy", 0, 7)

        payload = json.loads(fake.api_calls[0][1])
        assert result["test"] is False
        assert payload["labelDefinition"]["printPreview"] is False
        assert payload["item"]["recipient"]["name2"] == "c/o Beispiel"
        assert payload["item"]["attributes"] == {"przl": ["ECO"], "weight": 1}

    def test_none_when_labels_are_not_configured(self, swisspost, monkeypatch):
        fake = FakePost(validation=_label_response())
        monkeypatch.setattr(swisspost, "_http_post", fake)
        assert swisspost.generate_label(RECIPIENT, "PostPac Economy", 400, 7) is None
        assert fake.calls == []

    def test_none_when_recipient_is_incomplete(self, swisspost_labels, monkeypatch):
        fake = FakePost(validation=_label_response())
        monkeypatch.setattr(swisspost_labels, "_http_post", fake)
        assert swisspost_labels.generate_label({**RECIPIENT, "name": ""}, "PostPac Economy", 400, 7) is None
        assert fake.calls == []

    @pytest.mark.parametrize("response", [
        TimeoutError("slow"),
        {"item": {"errors": [{"code": "E2009"}]}},
        {"item": {"identCode": "99", "label": ["not base64!"]}},
        {"item": {"identCode": "", "label": ["QQ=="]}},
    ])
    def test_none_on_failed_or_unusable_response(self, swisspost_labels, monkeypatch, response, caplog):
        monkeypatch.setattr(swisspost_labels, "_http_post", FakePost(validation=response))
        with caplog.at_level("DEBUG"):
            assert swisspost_labels.generate_label(RECIPIENT, "PostPac Economy", 400, 7) is None
        assert "Anna Muster" not in caplog.text
        assert "Wankdorfallee" not in caplog.text


def _make_order(seeded_product, status="paid", country="CH", service="PostPac Priority"):
    import db as db_mod
    from models.model_orders import create_order

    order_id = create_order(
        user_id=None,
        session_id="sess-label",
        items=[{"product_id": seeded_product["id"], "price_id": seeded_product["prices"][0]["id"],
                "quantity": 2, "unit_sats": 1000}],
        shipping_info={**{k: v for k, v in RECIPIENT.items()}, "country": country},
        total_sats=2000,
        shipping_sats=500,
        shipping_carrier="post",
        shipping_service=service,
    )
    conn = db_mod.get_db()
    try:
        with conn:
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    finally:
        conn.close()
    return order_id


def _fake_label(test):
    return lambda **kwargs: {"ident_code": "996012345600000017", "document": LABEL_BYTES,
                             "file_type": "PDF", "test": test}


class TestOrderLabelStorage:
    def test_label_is_encrypted_at_rest(self, seeded_product, db_conn):
        from models.model_orders import get_order, get_order_label, set_order_label

        order_id = _make_order(seeded_product)
        assert get_order(order_id)["has_shipping_label"] is False
        assert get_order_label(order_id) is None

        set_order_label(order_id, {"document": "QUJD", "ident_code": "99", "test": True, "file_type": "PDF"})

        stored = db_conn.execute("SELECT shipping_label_enc FROM orders WHERE id = ?", (order_id,)).fetchone()[0]
        assert "QUJD" not in stored and '"ident_code"' not in stored
        assert get_order_label(order_id)["ident_code"] == "99"
        assert get_order(order_id)["has_shipping_label"] is True

    def test_order_weight_sums_item_quantities(self, seeded_product):
        from models.model_orders import get_order_weight_grams

        order_id = _make_order(seeded_product)
        assert get_order_weight_grams(order_id) == 2 * int(seeded_product["weight_grams"])


class TestAdminOrderLabel:
    def _create(self, admin_client, csrf_headers, order_id, data=None):
        return admin_client.post(f"/admin/orders/{order_id}/label", data=data or {}, headers=csrf_headers)

    def test_requires_admin(self, client, csrf_headers, seeded_product, admin_user):
        order_id = _make_order(seeded_product)
        assert client.post(f"/admin/orders/{order_id}/label", headers=csrf_headers).status_code == 302
        assert client.get(f"/admin/orders/{order_id}/label").status_code == 302

    def test_test_label_is_stored_without_touching_tracking(
        self, admin_client, csrf_headers, seeded_product, swisspost_labels, monkeypatch
    ):
        from models.model_orders import get_order, get_order_label

        order_id = _make_order(seeded_product)
        seen = {}
        monkeypatch.setattr(
            swisspost_labels, "generate_label",
            lambda **kwargs: seen.update(kwargs) or _fake_label(True)(),
        )

        assert self._create(admin_client, csrf_headers, order_id).status_code == 302

        assert seen["recipient"]["name"] == "Anna Muster"
        assert seen["service_name"] == "PostPac Priority"
        assert seen["item_id"] == order_id
        assert seen["weight_grams"] == 2 * int(seeded_product["weight_grams"])
        assert get_order_label(order_id)["test"] is True
        assert not get_order(order_id)["shipping_tracking"]

    def test_live_label_sets_tracking_and_can_be_downloaded(
        self, admin_client, csrf_headers, seeded_product, swisspost_labels, monkeypatch
    ):
        from models.model_orders import get_order

        order_id = _make_order(seeded_product)
        monkeypatch.setattr(swisspost_labels, "generate_label", _fake_label(False))

        self._create(admin_client, csrf_headers, order_id)
        assert get_order(order_id)["shipping_tracking"] == "996012345600000017"

        resp = admin_client.get(f"/admin/orders/{order_id}/label")
        assert resp.status_code == 200
        assert resp.data == LABEL_BYTES
        assert resp.headers["Content-Type"] == "application/pdf"
        assert resp.headers["Cache-Control"] == "no-store"

    def test_live_label_is_not_bought_twice_without_replace(
        self, admin_client, csrf_headers, seeded_product, swisspost_labels, monkeypatch
    ):
        order_id = _make_order(seeded_product)
        calls = []
        monkeypatch.setattr(
            swisspost_labels, "generate_label",
            lambda **kwargs: calls.append(1) or _fake_label(False)(),
        )

        self._create(admin_client, csrf_headers, order_id)
        self._create(admin_client, csrf_headers, order_id)
        assert len(calls) == 1

        self._create(admin_client, csrf_headers, order_id, {"replace": "1"})
        assert len(calls) == 2

    @pytest.mark.parametrize("status,country", [("pending", "CH"), ("cancelled", "CH"), ("paid", "DE")])
    def test_refuses_unpaid_or_foreign_orders(
        self, admin_client, csrf_headers, seeded_product, swisspost_labels, monkeypatch, status, country
    ):
        from models.model_orders import get_order_label

        order_id = _make_order(seeded_product, status=status, country=country)
        monkeypatch.setattr(
            swisspost_labels, "generate_label",
            lambda **kwargs: pytest.fail("no label may be requested"),
        )

        assert self._create(admin_client, csrf_headers, order_id).status_code == 302
        assert get_order_label(order_id) is None

    def test_refuses_when_labels_are_not_configured(self, admin_client, csrf_headers, seeded_product, swisspost, monkeypatch):
        order_id = _make_order(seeded_product)
        monkeypatch.setattr(swisspost, "generate_label", lambda **kwargs: pytest.fail("not configured"))
        assert self._create(admin_client, csrf_headers, order_id).status_code == 302

    def test_failure_stores_nothing(self, admin_client, csrf_headers, seeded_product, swisspost_labels, monkeypatch):
        from models.model_orders import get_order_label

        order_id = _make_order(seeded_product)
        monkeypatch.setattr(swisspost_labels, "generate_label", lambda **kwargs: None)

        self._create(admin_client, csrf_headers, order_id)
        assert get_order_label(order_id) is None

    def test_download_without_label_redirects(self, admin_client, seeded_product):
        order_id = _make_order(seeded_product)
        assert admin_client.get(f"/admin/orders/{order_id}/label").status_code == 302

    def test_order_page_shows_label_card_and_tracking_link(
        self, admin_client, csrf_headers, seeded_product, swisspost_labels, monkeypatch
    ):
        order_id = _make_order(seeded_product)
        monkeypatch.setattr(swisspost_labels, "generate_label", _fake_label(False))
        self._create(admin_client, csrf_headers, order_id)

        html = admin_client.get(f"/admin/orders/{order_id}").data.decode()
        assert f"/admin/orders/{order_id}/label" in html
        assert "https://service.post.ch/ekp-web/ui/entry/search/996012345600000017" in html

    def test_live_switch_is_off_unless_checked(self, admin_client, csrf_headers):
        from models.model_config import get_config

        form = {"whatsapp": "", "telegram": "", "shipping_rates": '{"CH":{"2":9}}',
                "swisspost_franking_license": "60012345", "swisspost_sender_city": "Zürich"}
        admin_client.post("/admin/settings", data=form, headers=csrf_headers)
        assert get_config("swisspost_label_live") == "0"
        assert get_config("swisspost_franking_license") == "60012345"

        admin_client.post("/admin/settings", data={**form, "swisspost_label_live": "on"}, headers=csrf_headers)
        assert get_config("swisspost_label_live") == "1"
