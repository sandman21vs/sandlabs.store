import json

import db
from services.service_security import decrypt_value, encrypt_value


_ORDER_SELECT = """
SELECT
    o.id,
    o.user_id,
    o.session_id,
    o.status,
    o.total_sats,
    o.shipping_sats,
    o.invoice_hash,
    o.bolt11,
    o.payment_confirmed_at,
    o.shipping_name_enc,
    o.shipping_street_enc,
    o.shipping_house_number_enc,
    o.shipping_address_extra_enc,
    o.shipping_city_enc,
    o.shipping_postal_code_enc,
    o.shipping_country_enc,
    o.shipping_name,
    o.shipping_address,
    o.shipping_postal_code,
    o.shipping_country,
    o.shipping_tracking,
    o.coupon_code,
    o.notes,
    o.created_at,
    o.updated_at
FROM orders o
"""


def _parse_options_json(options_json):
    try:
        return json.loads(options_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def _normalize_order(order):
    if order is None:
        return None
    normalized = dict(order)
    normalized["total_sats"] = int(normalized.get("total_sats") or 0)
    normalized["shipping_sats"] = int(normalized.get("shipping_sats") or 0)
    normalized["grand_total_sats"] = normalized["total_sats"] + normalized["shipping_sats"]
    normalized["shipping_name"] = decrypt_value(normalized.get("shipping_name_enc")) or (normalized.get("shipping_name") or "").strip()
    normalized["shipping_street"] = decrypt_value(normalized.get("shipping_street_enc")) or (normalized.get("shipping_address") or "").strip()
    normalized["shipping_house_number"] = decrypt_value(normalized.get("shipping_house_number_enc"))
    normalized["shipping_address_extra"] = decrypt_value(normalized.get("shipping_address_extra_enc"))
    normalized["shipping_city"] = decrypt_value(normalized.get("shipping_city_enc"))
    normalized["shipping_postal_code"] = decrypt_value(normalized.get("shipping_postal_code_enc")) or (normalized.get("shipping_postal_code") or "").strip()
    normalized["shipping_country"] = (
        decrypt_value(normalized.get("shipping_country_enc"))
        or (normalized.get("shipping_country") or "CH").strip().upper()
    )
    street_line = " ".join(
        part for part in (
            normalized["shipping_street"],
            normalized["shipping_house_number"],
        ) if part
    ).strip()
    locality_line = " ".join(
        part for part in (
            normalized["shipping_postal_code"],
            normalized["shipping_city"],
        ) if part
    ).strip()
    normalized["shipping_address_lines"] = [
        line for line in (
            normalized["shipping_name"],
            street_line,
            normalized["shipping_address_extra"],
            locality_line,
            normalized["shipping_country"],
        ) if line
    ]
    return normalized


def _normalize_order_item(item):
    normalized = dict(item)
    normalized["quantity"] = int(normalized.get("quantity") or 0)
    normalized["unit_sats"] = int(normalized.get("unit_sats") or 0)
    normalized["options"] = _parse_options_json(normalized.get("options_json"))
    normalized["line_total_sats"] = normalized["unit_sats"] * normalized["quantity"]
    return normalized


def _get_order_items(conn, order_id):
    rows = conn.execute(
        """
        SELECT
            oi.id,
            oi.order_id,
            oi.product_id,
            oi.price_id,
            oi.quantity,
            oi.unit_sats,
            oi.options_json,
            p.name AS product_name,
            pp.label AS price_label
        FROM order_items oi
        LEFT JOIN products p ON p.id = oi.product_id
        LEFT JOIN product_prices pp ON pp.id = oi.price_id
        WHERE oi.order_id = ?
        ORDER BY oi.id
        """,
        (order_id,),
    ).fetchall()
    return [_normalize_order_item(row) for row in rows]


def _normalize_shipping_info(shipping_info):
    info = shipping_info or {}
    return {
        "name": (info.get("name") or "").strip(),
        "street": (info.get("street") or "").strip(),
        "house_number": (info.get("house_number") or "").strip(),
        "address_extra": (info.get("address_extra") or "").strip(),
        "city": (info.get("city") or "").strip(),
        "postal_code": (info.get("postal_code") or "").strip(),
        "country": (info.get("country") or "CH").strip().upper(),
    }


def create_order(user_id, session_id, items, shipping_info, total_sats, shipping_sats, coupon_code=None):
    """Cria pedido + order_items a partir dos itens do carrinho."""
    if not items:
        raise ValueError("Order requires at least one item")

    shipping = _normalize_shipping_info(shipping_info)
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO orders (
                    user_id,
                    session_id,
                    status,
                    total_sats,
                    shipping_sats,
                    shipping_name_enc,
                    shipping_street_enc,
                    shipping_house_number_enc,
                    shipping_address_extra_enc,
                    shipping_city_enc,
                    shipping_postal_code_enc,
                    shipping_country_enc,
                    shipping_name,
                    shipping_address,
                    shipping_postal_code,
                    shipping_country,
                    coupon_code
                ) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    session_id,
                    int(total_sats or 0),
                    int(shipping_sats or 0),
                    encrypt_value(shipping["name"]),
                    encrypt_value(shipping["street"]),
                    encrypt_value(shipping["house_number"]),
                    encrypt_value(shipping["address_extra"]),
                    encrypt_value(shipping["city"]),
                    encrypt_value(shipping["postal_code"]),
                    encrypt_value(shipping["country"] or "CH"),
                    None,
                    None,
                    None,
                    None,
                    coupon_code,
                ),
            )
            order_id = cursor.lastrowid
            conn.executemany(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    price_id,
                    quantity,
                    unit_sats,
                    options_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        order_id,
                        item["product_id"],
                        int(item["price_id"]),
                        int(item.get("quantity") or 1),
                        int(item.get("unit_sats", item.get("amount_sats", 0)) or 0),
                        item.get("options_json")
                        or json.dumps(item.get("options") or {}, ensure_ascii=False, sort_keys=True),
                    )
                    for item in items
                ],
            )
            return order_id
    finally:
        conn.close()


def set_order_payment(order_id, invoice_hash, bolt11):
    """Atualiza pedido com dados da invoice Coinos."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE orders
                SET invoice_hash = ?, bolt11 = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (invoice_hash, bolt11, order_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def confirm_order_payment(order_id):
    """Marca pedido como 'paid', seta payment_confirmed_at = now()."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE orders
                SET
                    status = 'paid',
                    payment_confirmed_at = COALESCE(payment_confirmed_at, datetime('now')),
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (order_id,),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def update_order_status(order_id, status):
    """Atualiza status (processing, shipped, delivered, cancelled)."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status, order_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def set_order_tracking(order_id, tracking_code):
    """Seta shipping_tracking."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE orders
                SET shipping_tracking = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (tracking_code, order_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_order(order_id):
    """Remove pedido e order_items relacionados."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_order(order_id):
    """Retorna pedido com order_items."""
    conn = db.get_db()
    try:
        row = conn.execute(
            f"{_ORDER_SELECT} WHERE o.id = ? LIMIT 1",
            (order_id,),
        ).fetchone()
        order = _normalize_order(row)
        if order is None:
            return None
        order["items"] = _get_order_items(conn, order_id)
        return order
    finally:
        conn.close()


def get_order_by_invoice_hash(invoice_hash):
    """Busca pedido pelo invoice_hash Coinos."""
    conn = db.get_db()
    try:
        row = conn.execute(
            f"{_ORDER_SELECT} WHERE o.invoice_hash = ? LIMIT 1",
            (invoice_hash,),
        ).fetchone()
        order = _normalize_order(row)
        if order is None:
            return None
        order["items"] = _get_order_items(conn, order["id"])
        return order
    finally:
        conn.close()


def get_orders_by_user(user_id):
    """Lista pedidos do usuario, ORDER BY created_at DESC."""
    conn = db.get_db()
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                user_id,
                session_id,
                status,
                total_sats,
                shipping_sats,
                shipping_tracking,
                created_at,
                updated_at
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
        return [_normalize_order(row) for row in rows]
    finally:
        conn.close()


def get_all_orders(status_filter=None):
    """Lista todos os pedidos (admin). Filtro opcional por status."""
    conn = db.get_db()
    try:
        if status_filter:
            rows = conn.execute(
                """
                SELECT
                    id,
                    user_id,
                    session_id,
                    status,
                    total_sats,
                    shipping_sats,
                    shipping_tracking,
                    created_at,
                    updated_at
                FROM orders
                WHERE status = ?
                ORDER BY created_at DESC, id DESC
                """,
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    id,
                    user_id,
                    session_id,
                    status,
                    total_sats,
                    shipping_sats,
                    shipping_tracking,
                    created_at,
                    updated_at
                FROM orders
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
        return [_normalize_order(row) for row in rows]
    finally:
        conn.close()
