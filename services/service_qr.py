"""QR code generation for Lightning invoices."""

import io

import qrcode
from flask import send_file


def get_invoice_qr_response(bolt11):
    """Gera PNG com QR code do BOLT11. Retorna Flask response ou None."""
    if not bolt11 or len(bolt11) > 2000:
        return None
    img = qrcode.make(bolt11, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", max_age=60)
