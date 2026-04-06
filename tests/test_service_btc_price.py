"""Tests for BTC price conversion helpers."""

import importlib
import json


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_btc_rates_reads_chf_and_brl(monkeypatch):
    import services.service_btc_price as sbp

    importlib.reload(sbp)
    monkeypatch.setattr(
        sbp.urllib.request,
        "urlopen",
        lambda req, timeout=10: _MockResponse({"bitcoin": {"chf": 100000, "brl": 500000}}),
    )

    assert sbp.get_btc_chf_rate() == 100000.0
    assert sbp.get_btc_brl_rate() == 500000.0


def test_brl_to_sats(monkeypatch):
    import services.service_btc_price as sbp

    monkeypatch.setattr(sbp, "get_btc_brl_rate", lambda: 500000.0)
    assert sbp.brl_to_sats(2500.0) == 500000


def test_chf_to_sats_returns_zero_without_rate(monkeypatch):
    import services.service_btc_price as sbp

    monkeypatch.setattr(sbp, "get_btc_chf_rate", lambda: None)
    assert sbp.chf_to_sats(7.0) == 0
