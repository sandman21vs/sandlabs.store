import json

import db


def _order_row_to_dict(row):
    if row is None:
        return None
    return dict(row)


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

    items = []
    for row in rows:
        item = dict(row)
        item["options"] = json.loads(item["options_json"] or "{}")
        item["line_total_sats"] = int(item["unit_sats"] or 0) * int(item["quantity"] or 0)
        items.append(item)
    return items


def get_order(order_id):
    """Retorna pedido com order_items."""
    conn = db.get_db()
    try:
        row = conn.execute(
            """
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
            WHERE o.id = ?
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        order = _order_row_to_dict(row)
        if order is None:
            return None
        order["items"] = _get_order_items(conn, order_id)
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
        return [dict(row) for row in rows]
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
        return [dict(row) for row in rows]
    finally:
        conn.close()
