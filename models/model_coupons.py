"""Raw-SQL data access for discount coupons."""

import db


VALID_TYPES = ("percent", "fixed_sats")


def normalize_code(code):
    return (code or "").strip().upper()


def _row_to_coupon(row):
    if row is None:
        return None
    coupon = dict(row)
    coupon["active"] = bool(coupon["active"])
    coupon["discount_value"] = int(coupon["discount_value"] or 0)
    coupon["used_count"] = int(coupon["used_count"] or 0)
    coupon["max_uses"] = (
        int(coupon["max_uses"]) if coupon["max_uses"] is not None else None
    )
    return coupon


def get_coupon(code):
    """Return a coupon by (case-insensitive) code, or None."""
    normalized = normalize_code(code)
    if not normalized:
        return None
    conn = db.get_db()
    try:
        row = conn.execute(
            "SELECT * FROM coupons WHERE code = ? LIMIT 1",
            (normalized,),
        ).fetchone()
        return _row_to_coupon(row)
    finally:
        conn.close()


def list_coupons():
    conn = db.get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM coupons ORDER BY active DESC, code"
        ).fetchall()
        return [_row_to_coupon(row) for row in rows]
    finally:
        conn.close()


def create_coupon(code, discount_type, discount_value, expires_at=None,
                  max_uses=None, active=True):
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO coupons (
                    code, discount_type, discount_value, active, expires_at, max_uses
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    normalize_code(code),
                    discount_type,
                    int(discount_value),
                    1 if active else 0,
                    expires_at or None,
                    int(max_uses) if max_uses not in (None, "") else None,
                ),
            )
    finally:
        conn.close()


def update_coupon(coupon_id, discount_type, discount_value, expires_at=None,
                  max_uses=None, active=True):
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                """
                UPDATE coupons
                SET discount_type = ?, discount_value = ?, active = ?,
                    expires_at = ?, max_uses = ?
                WHERE id = ?
                """,
                (
                    discount_type,
                    int(discount_value),
                    1 if active else 0,
                    expires_at or None,
                    int(max_uses) if max_uses not in (None, "") else None,
                    int(coupon_id),
                ),
            )
    finally:
        conn.close()


def delete_coupon(coupon_id):
    conn = db.get_db()
    try:
        with conn:
            conn.execute("DELETE FROM coupons WHERE id = ?", (int(coupon_id),))
    finally:
        conn.close()


def increment_usage(code):
    """Atomically bump used_count for a coupon (best-effort, post-order)."""
    normalized = normalize_code(code)
    if not normalized:
        return
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                "UPDATE coupons SET used_count = used_count + 1 WHERE code = ?",
                (normalized,),
            )
    finally:
        conn.close()
