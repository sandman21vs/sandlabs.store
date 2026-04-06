import json

import db
from services.service_pricing import resolve_price_snapshot


def _scope_clause(session_id, user_id=None, alias="ci"):
    prefix = f"{alias}." if alias else ""
    if user_id is not None:
        return f"{prefix}user_id = ?", [user_id]
    return f"{prefix}session_id = ? AND {prefix}user_id IS NULL", [session_id]


def _normalize_options_json(options_json):
    if isinstance(options_json, str):
        if not options_json.strip():
            parsed = {}
        else:
            parsed = json.loads(options_json)
    elif options_json is None:
        parsed = {}
    else:
        parsed = options_json

    return json.dumps(parsed, ensure_ascii=False, sort_keys=True)


def get_cart(session_id, user_id=None):
    """Retorna itens do carrinho com detalhes do produto.
    Se user_id fornecido, busca por user_id. Senao, por session_id.
    Retorna lista de dicts:
    [{ id, product_id, product_name, price_label, display_text, amount_sats, quantity, options_json }]
    """
    where_clause, params = _scope_clause(session_id, user_id)
    conn = db.get_db()
    try:
        rows = conn.execute(
            f"""
            SELECT
                ci.id,
                ci.product_id,
                ci.price_id,
                p.name AS product_name,
                p.weight_grams,
                pp.label AS price_label,
                pp.pricing_mode,
                pp.currency_code,
                pp.amount_fiat,
                pp.display_text,
                pp.amount_sats,
                ci.quantity,
                ci.options_json
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            JOIN product_prices pp ON pp.id = ci.price_id
            WHERE {where_clause}
            ORDER BY ci.created_at, ci.id
            """,
            params,
        ).fetchall()

        items = []
        for row in rows:
            item = dict(row)
            price_snapshot = resolve_price_snapshot(item)
            item.update(price_snapshot)
            item["display_text"] = price_snapshot["display_text_resolved"]
            item["amount_sats"] = int(price_snapshot["resolved_amount_sats"] or 0)
            item["quantity"] = int(item["quantity"] or 0)
            item["weight_grams"] = int(item["weight_grams"] or 0)
            item["line_total_sats"] = item["amount_sats"] * item["quantity"]
            item["line_weight_grams"] = item["weight_grams"] * item["quantity"]
            items.append(item)
        return items
    finally:
        conn.close()


def add_to_cart(session_id, product_id, price_id, quantity, options_json, user_id=None):
    """Insere item no carrinho. Se ja existe (mesmo product_id + price_id + options), incrementa quantity."""
    normalized_options = _normalize_options_json(options_json)
    quantity = max(1, int(quantity or 1))
    where_clause, params = _scope_clause(session_id, user_id)

    conn = db.get_db()
    try:
        with conn:
            existing = conn.execute(
                f"""
                SELECT id, quantity
                FROM cart_items ci
                WHERE {where_clause}
                  AND ci.product_id = ?
                  AND ci.price_id = ?
                  AND ci.options_json = ?
                LIMIT 1
                """,
                params + [product_id, int(price_id), normalized_options],
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE cart_items SET quantity = ? WHERE id = ?",
                    (int(existing["quantity"]) + quantity, existing["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO cart_items (
                        session_id,
                        user_id,
                        product_id,
                        price_id,
                        quantity,
                        options_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_id,
                        product_id,
                        int(price_id),
                        quantity,
                        normalized_options,
                    ),
                )
    finally:
        conn.close()


def update_cart_item(item_id, quantity):
    """Atualiza quantidade. Se quantity <= 0, remove o item."""
    quantity = int(quantity or 0)
    if quantity <= 0:
        return remove_cart_item(item_id)

    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE cart_items SET quantity = ? WHERE id = ?",
                (quantity, item_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def remove_cart_item(item_id):
    """DELETE do item."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def clear_cart(session_id, user_id=None):
    """Remove todos os itens do carrinho do usuario/sessao."""
    where_clause, params = _scope_clause(session_id, user_id, alias="")
    conn = db.get_db()
    try:
        with conn:
            conn.execute(f"DELETE FROM cart_items WHERE {where_clause}", params)
    finally:
        conn.close()


def merge_cart(session_id, user_id):
    """Move itens do carrinho anonimo (session_id) para o usuario logado (user_id).
    Usado apos login. Se item ja existe no carrinho do user, soma quantidades.
    """
    anonymous_items = get_cart(session_id, user_id=None)
    if not anonymous_items:
        return

    for item in anonymous_items:
        add_to_cart(
            session_id=session_id,
            product_id=item["product_id"],
            price_id=item["price_id"],
            quantity=item["quantity"],
            options_json=item["options_json"],
            user_id=user_id,
        )

    clear_cart(session_id, user_id=None)


def get_cart_total(session_id, user_id=None):
    """Retorna total em sats de todos os itens."""
    return sum(item["line_total_sats"] for item in get_cart(session_id, user_id))


def get_cart_count(session_id, user_id=None):
    """Retorna numero total de itens (para badge no header)."""
    where_clause, params = _scope_clause(session_id, user_id)
    conn = db.get_db()
    try:
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM(ci.quantity), 0) AS item_count
            FROM cart_items ci
            WHERE {where_clause}
            """,
            params,
        ).fetchone()
        return int(row["item_count"] or 0)
    finally:
        conn.close()
