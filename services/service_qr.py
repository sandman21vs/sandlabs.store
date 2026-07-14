"""QR code generation for payments and order tracking."""

import io

import qrcode
from flask import send_file


def build_qr_png(value):
    """Build a QR code as PNG bytes, or return ``None`` for invalid input."""
    if not value or len(value) > 2000:
        return None
    img = qrcode.make(value, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_invoice_qr_response(bolt11):
    """Generate a Flask PNG response for a BOLT11 invoice or address."""
    png = build_qr_png(bolt11)
    if png is None:
        return None
    return send_file(io.BytesIO(png), mimetype="image/png", max_age=60)
