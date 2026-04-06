"""Checkout and payment routes."""

import json
import logging
import uuid

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from models.model_cart import clear_cart, get_cart, get_cart_total
from models.model_config import get_config
from models.model_orders import (
    confirm_order_payment,
    create_order as create_order_record,
    delete_order,
    get_order,
    get_order_by_invoice_hash,
    set_order_payment,
)
from routes.auth_utils import login_required
from services.service_coinos import check_invoice, create_invoice
from services.service_qr import get_invoice_qr_response
from services.service_shipping import calculate_shipping_chf, get_country_zone
from services.service_btc_price import chf_to_sats

checkout = Blueprint("checkout", __name__)
logger = logging.getLogger(__name__)


def _get_cart_session_id():
    if "cart_session" not in session:
        session["cart_session"] = str(uuid.uuid4())
    return session["cart_session"]


def _current_user_id():
    return session.get("user_id")


def _get_checkout_items():
    session_id = _get_cart_session_id()
    user_id = _current_user_id()
    items = get_cart(session_id, user_id)
    total_sats = get_cart_total(session_id, user_id)
    total_weight_grams = sum(int(item.get("line_weight_grams") or 0) for item in items)
    return session_id, user_id, items, total_sats, total_weight_grams


def _option_lines(item):
    options = json.loads(item.get("options_json") or "{}")
    lines = []

    for selection in options.get("selections", []):
        title = selection.get("title")
        inputs = selection.get("inputs", [])
        values = [
            f"{entry.get('label')}: {entry.get('value')}"
            for entry in inputs
            if entry.get("value")
        ]
        if title and values:
            lines.append(f"{title}: {' • '.join(values)}")
        elif values:
            lines.extend(values)

    if options.get("mode") == "kit":
        lines.append("Formato: Kit 5 un")
    elif options.get("mode") == "single":
        lines.append("Formato: Placa avulsa")

    return lines


def _has_unpriced_items(items):
    return any(int(item.get("amount_sats") or 0) <= 0 for item in items)


def _normalize_shipping_form(form_data):
    return {
        "name": (form_data.get("name") or "").strip(),
        "address": (form_data.get("address") or "").strip(),
        "postal_code": (form_data.get("postal_code") or "").strip(),
        "country": (form_data.get("country") or "CH").strip().upper(),
    }


def _render_checkout(error=None, form_data=None, status_code=200):
    session_id, user_id, items, total_sats, total_weight_grams = _get_checkout_items()
    if not items:
        return redirect(url_for("cart.cart_page"))

    for item in items:
        item["option_lines"] = _option_lines(item)
        item["has_amount_sats"] = int(item.get("amount_sats") or 0) > 0

    shipping_form = _normalize_shipping_form(
        form_data
        or {
            "name": session.get("display_name", ""),
            "country": "CH",
        }
    )
    preview_country = shipping_form["country"] or "CH"
    shipping_chf = calculate_shipping_chf(total_weight_grams, preview_country)
    shipping_sats = chf_to_sats(shipping_chf)

    return (
        render_template(
            "checkout.html",
            active="cart",
            items=items,
            total_sats=total_sats,
            total_weight_grams=total_weight_grams,
            shipping_form=shipping_form,
            shipping_chf=shipping_chf,
            shipping_sats=shipping_sats,
            grand_total_sats=total_sats + shipping_sats,
            shipping_zone=get_country_zone(preview_country),
            has_unpriced_items=_has_unpriced_items(items),
            error=error,
        ),
        status_code,
    )


def _ensure_order_owner(order):
    if order is None:
        abort(404)
    if session.get("is_admin"):
        return order
    if order.get("user_id") != session.get("user_id"):
        abort(403)
    return order


@checkout.route("/api/shipping/calculate", methods=["POST"])
def shipping_calculate():
    """Calculate shipping cost for a given country and weight.

    Request JSON:
        country      (str) ISO 3166-1 alpha-2 country code, e.g. "CH"
        weight_grams (int) total shipment weight in grams

    Response JSON:
        shipping_chf  (float) cost in Swiss Francs
        shipping_sats (int)   cost in satoshis at current BTC/CHF rate
        zone          (str)   "CH", "EU", or "WORLD"
        ok            (bool)  true
    """
    data = request.get_json(silent=True) or {}
    country = data.get("country", "")
    weight_grams = data.get("weight_grams")

    if not country:
        return jsonify({"ok": False, "error": "country is required"}), 400

    if weight_grams is None:
        return jsonify({"ok": False, "error": "weight_grams is required"}), 400

    try:
        weight_grams = int(weight_grams)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "weight_grams must be an integer"}), 400

    if weight_grams < 0:
        return jsonify({"ok": False, "error": "weight_grams must be non-negative"}), 400

    shipping_chf = calculate_shipping_chf(weight_grams, country)
    shipping_sats = chf_to_sats(shipping_chf)
    zone = get_country_zone(country)
    logger.info(
        "shipping_calculated country=%s weight_grams=%s zone=%s shipping_chf=%.2f shipping_sats=%s",
        country.upper().strip(),
        weight_grams,
        zone,
        shipping_chf,
        shipping_sats,
    )

    return jsonify({
        "ok": True,
        "shipping_chf": shipping_chf,
        "shipping_sats": shipping_sats,
        "zone": zone,
    })


@checkout.route("/checkout")
@login_required
def checkout_page():
    return _render_checkout()


@checkout.route("/checkout/create-order", methods=["POST"])
@login_required
def create_order():
    session_id, user_id, items, total_sats, total_weight_grams = _get_checkout_items()
    if not items:
        logger.info("checkout_create_order_empty_cart user_id=%s session_id=%s", user_id, session_id)
        return redirect(url_for("cart.cart_page"))
    if _has_unpriced_items(items):
        logger.warning("checkout_create_order_unpriced_items user_id=%s session_id=%s", user_id, session_id)
        return _render_checkout(
            error="Existem itens sem preco em sats cadastrado. Atualize os precos antes de gerar a invoice Lightning.",
            form_data=request.form,
            status_code=400,
        )

    shipping_info = _normalize_shipping_form(request.form)
    if not shipping_info["name"] or not shipping_info["address"] or not shipping_info["postal_code"]:
        logger.warning("checkout_create_order_invalid_shipping user_id=%s session_id=%s", user_id, session_id)
        return _render_checkout(
            error="Preencha nome, endereco e codigo postal para continuar.",
            form_data=request.form,
            status_code=400,
        )

    shipping_chf = calculate_shipping_chf(total_weight_grams, shipping_info["country"])
    shipping_sats = chf_to_sats(shipping_chf)
    order_id = create_order_record(
        user_id=user_id,
        session_id=session_id,
        items=items,
        shipping_info=shipping_info,
        total_sats=total_sats,
        shipping_sats=shipping_sats,
    )

    webhook_url = request.url_root.rstrip("/") + url_for("checkout.coinos_webhook")
    invoice = create_invoice(total_sats + shipping_sats, webhook_url=webhook_url)
    invoice_hash = (invoice or {}).get("hash", "")
    bolt11 = (invoice or {}).get("text", "")
    if not invoice_hash or not bolt11:
        delete_order(order_id)
        logger.warning("checkout_invoice_creation_failed order_id=%s user_id=%s", order_id, user_id)
        return _render_checkout(
            error="Nao foi possivel criar a invoice Lightning agora. Verifique a configuracao do Coinos.",
            form_data=request.form,
            status_code=502,
        )

    set_order_payment(order_id, invoice_hash, bolt11)
    clear_cart(session_id, user_id)
    logger.info(
        "checkout_order_created order_id=%s user_id=%s total_sats=%s shipping_sats=%s country=%s",
        order_id,
        user_id,
        total_sats,
        shipping_sats,
        shipping_info["country"],
    )
    return redirect(url_for("checkout.payment_page", order_id=order_id))


@checkout.route("/checkout/payment/<int:order_id>")
@login_required
def payment_page(order_id):
    order = _ensure_order_owner(get_order(order_id))
    if not order.get("bolt11"):
        return redirect(url_for("account.order_detail", order_id=order_id))
    logger.info("checkout_payment_page_viewed order_id=%s user_id=%s", order_id, session.get("user_id"))

    return render_template(
        "payment.html",
        active="orders",
        order=order,
        qr_url=url_for("checkout.invoice_qr", bolt11=order["bolt11"]),
    )


@checkout.route("/api/checkout/check-payment/<int:order_id>")
@login_required
def check_payment(order_id):
    order = _ensure_order_owner(get_order(order_id))
    if order.get("payment_confirmed_at") or order.get("status") in {"paid", "processing", "shipped", "delivered"}:
        logger.info("checkout_payment_already_confirmed order_id=%s", order_id)
        return jsonify({"paid": True})

    invoice_hash = order.get("invoice_hash")
    if not invoice_hash:
        return jsonify({"paid": False, "error": "invoice_missing"}), 400

    invoice = check_invoice(invoice_hash)
    try:
        received = int((invoice or {}).get("received", 0) or 0)
    except (TypeError, ValueError):
        received = 0

    if received > 0:
        confirm_order_payment(order_id)
        logger.info("checkout_payment_confirmed order_id=%s received=%s", order_id, received)
        return jsonify({"paid": True})
    logger.info("checkout_payment_pending order_id=%s", order_id)
    return jsonify({"paid": False})


@checkout.route("/checkout/invoice-qr")
@login_required
def invoice_qr():
    response = get_invoice_qr_response(request.args.get("bolt11", ""))
    if response is None:
        abort(400)
    return response


@checkout.route("/checkout/webhook/coinos", methods=["POST"])
def coinos_webhook():
    data = request.get_json(silent=True) or {}
    expected_secret = get_config("coinos_webhook_secret")
    if expected_secret and data.get("secret") != expected_secret:
        logger.warning("checkout_webhook_invalid_secret")
        return jsonify({"ok": False}), 403

    invoice_hash = (data.get("hash") or "").strip()
    if not invoice_hash:
        logger.warning("checkout_webhook_missing_hash")
        return jsonify({"ok": False}), 400

    try:
        received = int(data.get("received", 0) or 0)
    except (TypeError, ValueError):
        logger.warning("checkout_webhook_invalid_received hash=%s", invoice_hash[:12])
        return jsonify({"ok": False}), 400

    if received > 0:
        order = get_order_by_invoice_hash(invoice_hash)
        if order:
            confirm_order_payment(order["id"])
            logger.info("checkout_webhook_confirmed order_id=%s received=%s", order["id"], received)
        else:
            logger.warning("checkout_webhook_order_not_found hash=%s", invoice_hash[:12])

    return jsonify({"ok": True})
