"""Tests for reusable in-memory QR generation."""

from services.service_qr import build_qr_png


def test_build_qr_png_returns_png_bytes():
    png = build_qr_png("https://example.test/orders/42")

    assert isinstance(png, bytes)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_build_qr_png_rejects_empty_or_oversized_values():
    assert build_qr_png("") is None
    assert build_qr_png("x" * 2001) is None
