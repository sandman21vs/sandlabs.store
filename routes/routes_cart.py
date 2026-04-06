import json
import uuid

from flask import Blueprint, jsonify, render_template, request, session

import db
from models.model_cart import (
    add_to_cart,
    clear_cart,
    get_cart,
    get_cart_count,
    get_cart_total,
    remove_cart_item,
    update_cart_item,
)


cart = Blueprint("cart", __name__)


def _get_cart_session_id():
    if "cart_session" not in session:
        session["cart_session"] = str(uuid.uuid4())
    return session["cart_session"]


def _current_user_id():
    return session.get("user_id")


def _serialize_item(item):
    serialized = dict(item)
    serialized["options"] = json.loads(item["options_json"] or "{}")
    return serialized


def _get_cart_snapshot():
    session_id = _get_cart_session_id()
    user_id = _current_user_id()
    items = get_cart(session_id, user_id)
    total_sats = get_cart_total(session_id, user_id)
    count = get_cart_count(session_id, user_id)
    return session_id, user_id, items, total_sats, count


def _option_lines(item):
    options = json.loads(item["options_json"] or "{}")
    lines = []

    for selection in options.get("selections", []):
        title = selection.get("title")
        inputs = selection.get("inputs", [])
        values = [f"{entry.get('label')}: {entry.get('value')}" for entry in inputs if entry.get("value")]
        if title and values:
            lines.append(f"{title}: {' • '.join(values)}")
        elif values:
            lines.extend(values)

    if options.get("mode") == "kit":
        lines.append("Formato: Kit 5 un")
    elif options.get("mode") == "single":
        lines.append("Formato: Placa avulsa")

    return lines


def _owns_item(item_id, items):
    return any(int(item["id"]) == int(item_id) for item in items)


def _price_exists_for_product(product_id, price_id):
    conn = db.get_db()
    try:
        row = conn.execute(
            """
            SELECT pp.id
            FROM product_prices pp
            JOIN products p ON p.id = pp.product_id
            WHERE pp.id = ? AND pp.product_id = ? AND p.active = 1
            LIMIT 1
            """,
            (int(price_id), product_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


@cart.route("/api/cart/add", methods=["POST"])
def add_cart_item():
    payload = request.get_json(silent=True) or {}
    product_id = payload.get("product_id")
    price_id = payload.get("price_id")
    quantity = payload.get("quantity", 1)
    options = payload.get("options", {})

    if not product_id or price_id is None:
        return jsonify({"ok": False, "error": "product_id and price_id are required"}), 400

    if not _price_exists_for_product(product_id, price_id):
        return jsonify({"ok": False, "error": "Invalid product or price"}), 400

    session_id = _get_cart_session_id()
    user_id = _current_user_id()
    add_to_cart(session_id, product_id, price_id, quantity, options, user_id=user_id)
    cart_count = get_cart_count(session_id, user_id)
    return jsonify({"ok": True, "cart_count": cart_count})


@cart.route("/api/cart")
def cart_api():
    session_id, user_id, items, total_sats, count = _get_cart_snapshot()
    return jsonify(
        {
            "items": [_serialize_item(item) for item in items],
            "total_sats": total_sats,
            "count": count,
        }
    )


@cart.route("/api/cart/<int:item_id>", methods=["PUT"])
def update_cart_api(item_id):
    payload = request.get_json(silent=True) or {}
    quantity = payload.get("quantity")
    if quantity is None:
        return jsonify({"ok": False, "error": "quantity is required"}), 400

    session_id, user_id, items, _, _ = _get_cart_snapshot()
    if not _owns_item(item_id, items):
        return jsonify({"ok": False, "error": "Item not found"}), 404

    update_cart_item(item_id, quantity)
    cart_count = get_cart_count(session_id, user_id)
    return jsonify({"ok": True, "cart_count": cart_count})


@cart.route("/api/cart/<int:item_id>", methods=["DELETE"])
def remove_cart_api(item_id):
    session_id, user_id, items, _, _ = _get_cart_snapshot()
    if not _owns_item(item_id, items):
        return jsonify({"ok": False, "error": "Item not found"}), 404

    remove_cart_item(item_id)
    cart_count = get_cart_count(session_id, user_id)
    return jsonify({"ok": True, "cart_count": cart_count})


@cart.route("/api/cart", methods=["DELETE"])
def clear_cart_api():
    session_id = _get_cart_session_id()
    user_id = _current_user_id()
    clear_cart(session_id, user_id)
    return jsonify({"ok": True})


@cart.route("/carrinho")
def cart_page():
    _, _, items, total_sats, count = _get_cart_snapshot()

    for item in items:
        item["option_lines"] = _option_lines(item)
        item["has_amount_sats"] = item["amount_sats"] > 0

    has_pending_prices = any(not item["has_amount_sats"] for item in items)
    return render_template(
        "cart.html",
        active="cart",
        items=items,
        total_sats=total_sats,
        count=count,
        has_pending_prices=has_pending_prices,
    )
