import json

import db


_PRODUCT_SELECT = """
SELECT
    id,
    name,
    summary,
    details_html,
    weight_grams,
    buy_button_text,
    allow_addon_seed,
    badge_text,
    badge_variant,
    sort_order,
    active,
    created_at,
    updated_at
FROM products
"""


def _bool_to_int(value):
    return 1 if value else 0


def _row_to_product(row):
    product = dict(row)
    product["allow_addon_seed"] = bool(product["allow_addon_seed"])
    product["active"] = bool(product["active"])
    product["prices"] = []
    product["images"] = []
    product["options"] = []
    return product


def _load_related_records(conn, products):
    if not products:
        return products

    product_ids = [product["id"] for product in products]
    placeholders = ",".join("?" for _ in product_ids)
    product_map = {product["id"]: product for product in products}

    price_rows = conn.execute(
        f"""
        SELECT id, product_id, label, amount_sats, display_text, sort_order
        FROM product_prices
        WHERE product_id IN ({placeholders})
        ORDER BY product_id, sort_order, id
        """,
        product_ids,
    ).fetchall()
    for row in price_rows:
        product_map[row["product_id"]]["prices"].append(dict(row))

    image_rows = conn.execute(
        f"""
        SELECT id, product_id, filename, sort_order
        FROM product_images
        WHERE product_id IN ({placeholders})
        ORDER BY product_id, sort_order, id
        """,
        product_ids,
    ).fetchall()
    for row in image_rows:
        product_map[row["product_id"]]["images"].append(dict(row))

    option_rows = conn.execute(
        f"""
        SELECT id, product_id, option_type, title, config_json, sort_order
        FROM product_options
        WHERE product_id IN ({placeholders})
        ORDER BY product_id, sort_order, id
        """,
        product_ids,
    ).fetchall()
    for row in option_rows:
        option = {
            "id": row["id"],
            "type": row["option_type"],
            "title": row["title"],
            "sort_order": row["sort_order"],
        }
        option.update(json.loads(row["config_json"] or "{}"))
        product_map[row["product_id"]]["options"].append(option)

    return products


def _normalize_prices(prices):
    normalized = []
    for index, price in enumerate(prices or []):
        normalized.append(
            {
                "label": price["label"],
                "amount_sats": int(price.get("amount_sats", 0)),
                "display_text": price["display_text"],
                "sort_order": int(price.get("sort_order", index)),
            }
        )
    return normalized


def _normalize_images(images):
    normalized = []
    for index, image in enumerate(images or []):
        if isinstance(image, str):
            normalized.append({"filename": image, "sort_order": index})
            continue

        normalized.append(
            {
                "filename": image["filename"],
                "sort_order": int(image.get("sort_order", index)),
            }
        )
    return normalized


def _normalize_options(options):
    normalized = []
    for index, option in enumerate(options or []):
        config_json = json.dumps(
            {
                key: value
                for key, value in option.items()
                if key not in {"id", "type", "title", "sort_order"}
            },
            ensure_ascii=False,
        )
        normalized.append(
            {
                "type": option["type"],
                "title": option.get("title", ""),
                "config_json": config_json,
                "sort_order": int(option.get("sort_order", index)),
            }
        )
    return normalized


def _replace_related_records(conn, product_id, prices, images, options):
    conn.execute("DELETE FROM product_prices WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM product_options WHERE product_id = ?", (product_id,))

    conn.executemany(
        """
        INSERT INTO product_prices (product_id, label, amount_sats, display_text, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                product_id,
                price["label"],
                price["amount_sats"],
                price["display_text"],
                price["sort_order"],
            )
            for price in _normalize_prices(prices)
        ],
    )
    conn.executemany(
        """
        INSERT INTO product_images (product_id, filename, sort_order)
        VALUES (?, ?, ?)
        """,
        [
            (product_id, image["filename"], image["sort_order"])
            for image in _normalize_images(images)
        ],
    )
    conn.executemany(
        """
        INSERT INTO product_options (product_id, option_type, title, config_json, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                product_id,
                option["type"],
                option["title"],
                option["config_json"],
                option["sort_order"],
            )
            for option in _normalize_options(options)
        ],
    )


def get_all_products():
    """Retorna lista de dicts com produtos ativos, incluindo prices, images e options."""
    conn = db.get_db()
    try:
        rows = conn.execute(
            f"{_PRODUCT_SELECT} WHERE active = 1 ORDER BY sort_order, id"
        ).fetchall()
        products = [_row_to_product(row) for row in rows]
        return _load_related_records(conn, products)
    finally:
        conn.close()


def get_product_by_id(product_id):
    """Retorna um unico produto com prices, images e options."""
    conn = db.get_db()
    try:
        row = conn.execute(
            f"{_PRODUCT_SELECT} WHERE id = ? LIMIT 1",
            (product_id,),
        ).fetchone()
        if row is None:
            return None

        product = _row_to_product(row)
        _load_related_records(conn, [product])
        return product
    finally:
        conn.close()


def create_product(data):
    """Insere produto + prices + images + options. data e um dict."""
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO products (
                    id,
                    name,
                    summary,
                    details_html,
                    weight_grams,
                    buy_button_text,
                    allow_addon_seed,
                    badge_text,
                    badge_variant,
                    sort_order,
                    active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["id"],
                    data["name"],
                    data["summary"],
                    data.get("details_html", ""),
                    int(data.get("weight_grams", 200)),
                    data.get("buy_button_text", "Comprar"),
                    _bool_to_int(data.get("allow_addon_seed", False)),
                    data.get("badge_text"),
                    data.get("badge_variant"),
                    int(data.get("sort_order", 0)),
                    _bool_to_int(data.get("active", True)),
                ),
            )
            _replace_related_records(
                conn,
                data["id"],
                data.get("prices", []),
                data.get("images", []),
                data.get("options", []),
            )
    finally:
        conn.close()

    return get_product_by_id(data["id"])


def update_product(product_id, data):
    """Atualiza produto existente. Substitui prices/images/options."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE products
                SET
                    name = ?,
                    summary = ?,
                    details_html = ?,
                    weight_grams = ?,
                    buy_button_text = ?,
                    allow_addon_seed = ?,
                    badge_text = ?,
                    badge_variant = ?,
                    sort_order = ?,
                    active = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    data["name"],
                    data["summary"],
                    data.get("details_html", ""),
                    int(data.get("weight_grams", 200)),
                    data.get("buy_button_text", "Comprar"),
                    _bool_to_int(data.get("allow_addon_seed", False)),
                    data.get("badge_text"),
                    data.get("badge_variant"),
                    int(data.get("sort_order", 0)),
                    _bool_to_int(data.get("active", True)),
                    product_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Product not found: {product_id}")

            _replace_related_records(
                conn,
                product_id,
                data.get("prices", []),
                data.get("images", []),
                data.get("options", []),
            )
    finally:
        conn.close()

    return get_product_by_id(product_id)


def delete_product(product_id):
    """DELETE CASCADE remove produto e tudo relacionado."""
    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def products_to_js_format(products):
    """Converte lista de produtos do banco para o formato window.PRODUTOS."""
    js_products = []
    for product in products:
        option_list = []
        for option in product.get("options", []):
            js_option = {"type": option["type"]}
            if option.get("title"):
                js_option["title"] = option["title"]
            if "inputs" in option:
                js_option["inputs"] = option["inputs"]
            if "input" in option:
                js_option["input"] = option["input"]
            for key, value in option.items():
                if key in {"id", "type", "title", "sort_order", "inputs", "input"}:
                    continue
                js_option[key] = value
            option_list.append(js_option)

        badge = None
        if product.get("badge_text"):
            badge = {
                "text": product["badge_text"],
                "variant": product.get("badge_variant"),
            }

        js_products.append(
            {
                "id": product["id"],
                "nome": product["name"],
                "imagens": [
                    image["filename"] if isinstance(image, dict) else image
                    for image in product.get("images", [])
                ],
                "resumo": product["summary"],
                "preco": [
                    {
                        "id": price["id"],
                        "label": price["label"],
                        "valor": price["display_text"],
                        "amountSats": price["amount_sats"],
                    }
                    for price in product.get("prices", [])
                ],
                "detalhesHTML": product["details_html"],
                "options": option_list,
                "allowAddOnSeed": bool(product.get("allow_addon_seed", False)),
                "buyButtonText": product.get("buy_button_text") or "Comprar",
                "badge": badge,
            }
        )

    return js_products
