"""Tests for deterministic order PDF rendering."""

from services.service_pdf import build_order_pdf


def _sample_order():
    return {
        "id": 42,
        "access_token": "guest-token-123",
        "created_at": "2026-07-14T12:00:00+00:00",
        "status": "paid",
        "payment_method": "lightning",
        "payment_confirmed_at": "2026-07-14T12:01:00+00:00",
        "total_sats": 10_000,
        "shipping_sats": 2_000,
        "grand_total_sats": 12_000,
        "grand_total_fiat": "125.50",
        "fiat_currency": "CHF",
        "shipping_address_lines": [
            "João Käufer",
            "Bahnhofstrasse 12",
            "8000 Zürich",
            "CH",
        ],
        "items": [
            {
                "product_name": "Test Product",
                "price_label": "Base",
                "quantity": 1,
                "unit_sats": 10_000,
                "line_total_sats": 10_000,
            }
        ],
    }


def test_build_order_pdf_returns_non_empty_pdf_bytes():
    pdf = build_order_pdf(
        _sample_order(),
        contacts={"whatsapp": "41770000000", "telegram": "Sandlabs"},
        tracking_url="https://example.test/orders/42",
    )

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1_000
    assert b"guest-token-123" in pdf
    assert b"CHF 125.50" in pdf


def test_build_order_pdf_is_deterministic_for_same_input():
    first = build_order_pdf(_sample_order(), tracking_url="https://example.test/orders/42")
    second = build_order_pdf(_sample_order(), tracking_url="https://example.test/orders/42")

    assert first == second


def test_build_order_pdf_requires_order_id():
    try:
        build_order_pdf({})
    except ValueError as exc:
        assert "id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
