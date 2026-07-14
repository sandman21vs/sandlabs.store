"""Tests for the Coinos client: enabled methods, invoice types, addresses."""

import json


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def _fake_urlopen(capture, payload):
    def _inner(req, timeout=10):
        capture["payload"] = json.loads(req.data.decode())
        capture["url"] = req.full_url
        return _FakeResp(payload)

    return _inner


def test_get_enabled_methods_reflects_config(tmp_db):
    from models.model_config import set_config
    from services.service_coinos import get_enabled_methods

    set_config("coinos_enabled", "0")
    assert get_enabled_methods() == []

    set_config("coinos_enabled", "1")
    assert get_enabled_methods() == ["lightning"]

    set_config("coinos_liquid", "1")
    set_config("coinos_onchain", "1")
    assert get_enabled_methods() == ["lightning", "liquid", "onchain"]


def test_create_invoice_maps_onchain_to_bitcoin(tmp_db, monkeypatch):
    from models.model_config import set_config
    from services import service_coinos

    set_config("coinos_enabled", "1")
    set_config("coinos_api_key", "key")
    capture = {}
    monkeypatch.setattr(
        service_coinos.urllib.request, "urlopen",
        _fake_urlopen(capture, {"hash": "h", "text": "bc1qaddr"}),
    )

    invoice = service_coinos.create_invoice(1000, invoice_type="onchain")
    assert capture["payload"]["invoice"]["type"] == "bitcoin"
    assert capture["payload"]["invoice"]["amount"] == 1000
    assert invoice["text"] == "bc1qaddr"


def test_create_invoice_rejects_unknown_type(tmp_db):
    from models.model_config import set_config
    from services.service_coinos import create_invoice

    set_config("coinos_enabled", "1")
    set_config("coinos_api_key", "key")
    assert create_invoice(1000, invoice_type="dogecoin") is None


def test_create_invoice_returns_none_when_disabled(tmp_db):
    from models.model_config import set_config
    from services.service_coinos import create_invoice

    set_config("coinos_enabled", "0")
    assert create_invoice(1000, invoice_type="lightning") is None


def test_get_fresh_onchain_address(tmp_db, monkeypatch):
    from models.model_config import set_config
    from services import service_coinos

    set_config("coinos_enabled", "1")
    set_config("coinos_api_key", "key")
    capture = {}
    monkeypatch.setattr(
        service_coinos.urllib.request, "urlopen",
        _fake_urlopen(capture, {"hash": "bc1qfresh"}),
    )

    address = service_coinos.get_fresh_onchain_address()
    assert address == "bc1qfresh"
    assert capture["payload"]["invoice"]["type"] == "bitcoin"
    assert capture["payload"]["invoice"]["amount"] == 0


def test_get_fresh_liquid_address(tmp_db, monkeypatch):
    from models.model_config import set_config
    from services import service_coinos

    set_config("coinos_enabled", "1")
    set_config("coinos_api_key", "key")
    capture = {}
    monkeypatch.setattr(
        service_coinos.urllib.request, "urlopen",
        _fake_urlopen(capture, {"hash": "lq1qfresh"}),
    )

    address = service_coinos.get_fresh_liquid_address()
    assert address == "lq1qfresh"
    assert capture["payload"]["invoice"]["type"] == "liquid"
