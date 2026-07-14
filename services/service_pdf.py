"""Pure PDF rendering for customer order receipts."""

from datetime import datetime, timezone
from io import BytesIO

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from services.service_qr import build_qr_png


_DEFAULT_LABELS = {
    "title": "Order #{id}",
    "receipt": "Sandlabs order receipt",
    "summary": "Order summary",
    "access_token": "Access token",
    "account_order": "Account order",
    "created": "Created",
    "order_status": "Order status",
    "payment": "Payment",
    "payment_status": "Payment status",
    "paid": "Paid",
    "pending": "Pending",
    "products": "Products",
    "shipping": "Shipping",
    "total": "Total",
    "fiat_total": "Fiat total",
    "not_recorded": "Not recorded",
    "items": "Items",
    "no_items": "No items recorded.",
    "quantity": "Qty",
    "shipping_address": "Shipping address",
    "tracking": "Tracking",
    "contact": "Contact",
}


def _safe_text(value):
    """Return text supported by the built-in PDF font without control bytes."""
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _creation_date(value):
    if value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime(2000, 1, 1, tzinfo=timezone.utc)


def _line(pdf, label, value):
    pdf.set_font("helvetica", style="B", size=10)
    pdf.cell(42, 6, _safe_text(label))
    pdf.set_font("helvetica", size=10)
    pdf.multi_cell(0, 6, _safe_text(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _section(pdf, title):
    pdf.ln(2)
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 8, _safe_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(210, 210, 210)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _fiat_total(order, labels):
    amount = order.get("grand_total_fiat", order.get("total_fiat"))
    display = order.get("grand_total_fiat_display", order.get("total_fiat_display"))
    currency = _safe_text(order.get("fiat_currency") or order.get("currency_code") or "CHF")
    if display:
        return _safe_text(display)
    if amount not in (None, ""):
        return f"{currency} {_safe_text(amount)}"
    return labels["not_recorded"]


def build_order_pdf(order: dict, contacts=None, tracking_url=None, labels=None) -> bytes:
    """Render a normalized order as deterministic PDF bytes.

    ``contacts`` and ``tracking_url`` are explicit inputs so this service never
    reads configuration, request state, secrets, or the network.
    """
    if not isinstance(order, dict) or not order.get("id"):
        raise ValueError("Order with an id is required")

    contacts = dict(contacts or {})
    resolved_labels = {**_DEFAULT_LABELS, **dict(labels or {})}
    token = _safe_text(order.get("access_token"))
    resolved_tracking_url = tracking_url or order.get("tracking_url")
    if not resolved_tracking_url:
        resolved_tracking_url = f"order:{order['id']}:{token}" if token else f"order:{order['id']}"

    pdf = FPDF(format="A4")
    pdf.set_compression(False)
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_title(f"Sandlabs order #{order['id']}")
    pdf.set_author("Sandlabs")
    pdf.set_creation_date(_creation_date(order.get("created_at")))
    pdf.add_page()

    pdf.set_font("helvetica", style="B", size=18)
    title = resolved_labels["title"].format(id=order["id"])
    pdf.cell(0, 10, _safe_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", size=9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, _safe_text(resolved_labels["receipt"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)

    _section(pdf, resolved_labels["summary"])
    _line(pdf, resolved_labels["access_token"], token or resolved_labels["account_order"])
    _line(pdf, resolved_labels["created"], order.get("created_at") or "-")
    _line(pdf, resolved_labels["order_status"], order.get("status") or "pending")
    _line(pdf, resolved_labels["payment"], order.get("payment_method") or order.get("invoice_type") or "-")
    payment_status = resolved_labels["paid"] if order.get("payment_confirmed_at") else resolved_labels["pending"]
    _line(pdf, resolved_labels["payment_status"], payment_status)
    _line(pdf, resolved_labels["products"], f"{int(order.get('total_sats') or 0):,} sats")
    _line(pdf, resolved_labels["shipping"], f"{int(order.get('shipping_sats') or 0):,} sats")
    _line(pdf, resolved_labels["total"], f"{int(order.get('grand_total_sats') or 0):,} sats")
    _line(pdf, resolved_labels["fiat_total"], _fiat_total(order, resolved_labels))

    _section(pdf, resolved_labels["items"])
    items = order.get("items") or []
    if not items:
        pdf.set_font("helvetica", size=10)
        pdf.cell(0, 6, _safe_text(resolved_labels["no_items"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    for item in items:
        name = item.get("product_name") or item.get("product_id") or "Item"
        variant = item.get("price_label") or ""
        quantity = int(item.get("quantity") or 0)
        line_total = int(
            item.get("line_total_sats")
            or int(item.get("unit_sats") or 0) * quantity
        )
        description = f"{name}"
        if variant:
            description += f" - {variant}"
        description += f" | {resolved_labels['quantity']} {quantity} | {line_total:,} sats"
        pdf.set_font("helvetica", size=10)
        pdf.multi_cell(0, 6, _safe_text(description), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    address_lines = order.get("shipping_address_lines") or []
    if address_lines:
        _section(pdf, resolved_labels["shipping_address"])
        pdf.set_font("helvetica", size=10)
        for address_line in address_lines:
            pdf.cell(0, 6, _safe_text(address_line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    _section(pdf, resolved_labels["tracking"])
    qr_png = build_qr_png(str(resolved_tracking_url))
    if qr_png:
        qr_y = pdf.get_y()
        pdf.image(BytesIO(qr_png), x=pdf.l_margin, y=qr_y, w=34, h=34)
        pdf.set_xy(pdf.l_margin + 40, qr_y + 3)
        pdf.set_font("helvetica", size=9)
        pdf.multi_cell(0, 5, _safe_text(resolved_tracking_url), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_y(max(pdf.get_y(), qr_y + 38))

    contact_lines = []
    if contacts.get("whatsapp"):
        contact_lines.append(f"WhatsApp: {contacts['whatsapp']}")
    if contacts.get("telegram"):
        contact_lines.append(f"Telegram: {contacts['telegram']}")
    if contact_lines:
        _section(pdf, resolved_labels["contact"])
        pdf.set_font("helvetica", size=10)
        for contact in contact_lines:
            pdf.cell(0, 6, _safe_text(contact), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
