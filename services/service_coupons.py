"""Coupon validation and discount computation (no Flask, no request state).

The discount is always recomputed server-side against the authoritative cart
subtotal — the client never supplies a discount amount.
"""

from datetime import date, datetime

from models.model_coupons import get_coupon, normalize_code


def _parse_expiry(value):
    """Return the inclusive expiry date, or None if unset/unparseable."""
    if not value:
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def compute_discount_sats(coupon, subtotal_sats):
    """Discount in sats for a valid coupon, clamped to [0, subtotal]."""
    subtotal = max(0, int(subtotal_sats or 0))
    if not coupon or subtotal <= 0:
        return 0
    if coupon["discount_type"] == "percent":
        percent = max(0, min(100, int(coupon["discount_value"] or 0)))
        discount = subtotal * percent // 100
    else:  # fixed_sats
        discount = max(0, int(coupon["discount_value"] or 0))
    return min(discount, subtotal)


def evaluate_coupon(code, subtotal_sats, today=None):
    """Validate a coupon code against a subtotal.

    Returns (coupon | None, discount_sats, error_key). ``error_key`` is None on
    success, otherwise an i18n suffix under commerce.checkout.coupon.errors.
    """
    normalized = normalize_code(code)
    if not normalized:
        return None, 0, None  # no coupon entered is not an error

    coupon = get_coupon(normalized)
    if coupon is None:
        return None, 0, "invalid"
    if not coupon["active"]:
        return None, 0, "inactive"

    expiry = _parse_expiry(coupon.get("expires_at"))
    if expiry is not None and (today or date.today()) > expiry:
        return None, 0, "expired"

    max_uses = coupon.get("max_uses")
    if max_uses is not None and coupon["used_count"] >= max_uses:
        return None, 0, "exhausted"

    discount = compute_discount_sats(coupon, subtotal_sats)
    if discount <= 0:
        return None, 0, "not_applicable"

    return coupon, discount, None
