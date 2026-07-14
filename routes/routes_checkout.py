"""Checkout and payment routes."""

import json
import logging
import secrets
import uuid
from io import BytesIO
from urllib.parse import urlsplit

import config
from flask import (
    Blueprint,
    abort,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from i18n import translate
from models.model_cart import clear_cart, get_cart, get_cart_total
from models.model_config import get_config
from models.model_orders import (
    confirm_order_payment,
    create_order as create_order_record,
    delete_order,
    get_guest_order_by_access_token,
    get_order,
    get_order_by_invoice_hash,
    set_order_payment,
)
from services.service_coinos import (
    PAYMENT_METHODS,
    check_invoice,
    create_invoice,
    get_enabled_methods,
)
from services.service_qr import get_invoice_qr_response
from services.service_pdf import build_order_pdf
from services.service_shipping import get_country_zone, get_shipping_options
from services.service_btc_price import chf_to_sats

checkout = Blueprint("checkout", __name__)
logger = logging.getLogger(__name__)
_GUEST_ORDER_ACCESS_KEY = "guest_order_ids"
_MAX_REMEMBERED_GUEST_ORDERS = 20
_PDF_LABEL_KEYS = (
    "title", "receipt", "summary", "access_token", "account_order", "created",
    "order_status", "payment", "payment_status", "paid", "pending", "products",
    "shipping", "total", "fiat_total", "not_recorded", "items", "no_items",
    "quantity", "shipping_address", "tracking", "contact",
)


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
        lines.append(translate("commerce.cart.option_mode_kit"))
    elif options.get("mode") == "single":
        lines.append(translate("commerce.cart.option_mode_single"))

    return lines


def _has_unpriced_items(items):
    return any(int(item.get("amount_sats") or 0) <= 0 for item in items)


def _normalize_shipping_form(form_data):
    return {
        "name": (form_data.get("name") or "").strip(),
        "street": (form_data.get("street") or "").strip(),
        "house_number": (form_data.get("house_number") or "").strip(),
        "address_extra": (form_data.get("address_extra") or "").strip(),
        "city": (form_data.get("city") or "").strip(),
        "postal_code": (form_data.get("postal_code") or "").strip(),
        "country": (form_data.get("country") or "CH").strip().upper(),
    }


def _shipping_options_with_sats(weight_grams, country):
    """Shipping options for a destination, each with price_chf and price_sats."""
    options = get_shipping_options(weight_grams, country)
    for opt in options:
        opt["price_sats"] = chf_to_sats(opt["price_chf"])
    return options


def _resolve_shipping(weight_grams, country, carrier=None, service=None):
    """Pick the shipping option (server-authoritative price).

    Returns ``(chosen_option, options)``. Honors a requested carrier/service if
    it matches an available option; otherwise uses the cheapest.
    """
    options = _shipping_options_with_sats(weight_grams, country)
    chosen = None
    if carrier:
        chosen = next(
            (
                opt
                for opt in options
                if opt["carrier"] == carrier and (not service or opt.get("service") == service)
            ),
            None,
        )
    if chosen is None:
        chosen = options[0]  # options are sorted cheapest-first
    return chosen, options


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
    chosen_shipping, shipping_options = _resolve_shipping(total_weight_grams, preview_country)
    shipping_chf = chosen_shipping["price_chf"]
    shipping_sats = chosen_shipping["price_sats"]

    response = make_response(render_template(
        "checkout.html",
        active="cart",
        items=items,
        total_sats=total_sats,
        total_weight_grams=total_weight_grams,
        shipping_form=shipping_form,
        shipping_chf=shipping_chf,
        shipping_sats=shipping_sats,
        shipping_options=shipping_options,
        grand_total_sats=total_sats + shipping_sats,
        shipping_zone=get_country_zone(preview_country),
        has_unpriced_items=_has_unpriced_items(items),
        payment_methods=get_enabled_methods(),
        error=error,
    ), status_code)
    return _no_store(response)


def _remember_guest_order(order_id):
    remembered = [
        int(value)
        for value in session.get(_GUEST_ORDER_ACCESS_KEY, [])
        if str(value).isdigit()
    ]
    if order_id in remembered:
        remembered.remove(order_id)
    remembered.append(int(order_id))
    session[_GUEST_ORDER_ACCESS_KEY] = remembered[-_MAX_REMEMBERED_GUEST_ORDERS:]


def _has_remembered_guest_order(order_id):
    return int(order_id) in {
        int(value)
        for value in session.get(_GUEST_ORDER_ACCESS_KEY, [])
        if str(value).isdigit()
    }


def _ensure_order_access(order):
    if order is None:
        abort(404)
    if session.get("is_admin"):
        return order

    order_user_id = order.get("user_id")
    if order_user_id is not None:
        if order_user_id == session.get("user_id"):
            return order
        abort(404)

    same_checkout_session = (
        bool(order.get("session_id"))
        and order.get("session_id") == session.get("cart_session")
    )
    if same_checkout_session or _has_remembered_guest_order(order["id"]):
        return order
    abort(404)


def _order_detail_url(order):
    if order.get("user_id") is not None:
        return url_for("account.order_detail", order_id=order["id"])
    return url_for("checkout.order_detail", order_id=order["id"])


def _no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers.pop("Expires", None)
    return response


def _pdf_labels():
    return {key: translate(f"account.pdf.{key}") for key in _PDF_LABEL_KEYS}


def _public_url(endpoint, **values):
    path = url_for(endpoint, **values)
    base_url = (config.PUBLIC_BASE_URL or "").rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return f"{origin}{path}"
    return path


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
        return jsonify({"ok": False, "error": translate("commerce.api.errors.country_required")}), 400

    if weight_grams is None:
        return jsonify({"ok": False, "error": translate("commerce.api.errors.weight_required")}), 400

    try:
        weight_grams = int(weight_grams)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": translate("commerce.api.errors.weight_integer")}), 400

    if weight_grams < 0:
        return jsonify({"ok": False, "error": translate("commerce.api.errors.weight_non_negative")}), 400

    options = _shipping_options_with_sats(weight_grams, country)
    default = options[0]  # cheapest (sorted); back-compat single value
    zone = get_country_zone(country)
    logger.info(
        "shipping_calculated weight_grams=%s zone=%s shipping_chf=%.2f shipping_sats=%s options=%s",
        weight_grams,
        zone,
        default["price_chf"],
        default["price_sats"],
        len(options),
    )

    return jsonify({
        "ok": True,
        "shipping_chf": default["price_chf"],
        "shipping_sats": default["price_sats"],
        "zone": zone,
        "options": options,
    })


@checkout.route("/checkout")
def checkout_page():
    return _render_checkout()


@checkout.route("/checkout/create-order", methods=["POST"])
def create_order():
    session_id, user_id, items, total_sats, total_weight_grams = _get_checkout_items()
    if not items:
        logger.info("checkout_create_order_empty_cart user_id=%s", user_id)
        return redirect(url_for("cart.cart_page"))
    if _has_unpriced_items(items):
        logger.warning("checkout_create_order_unpriced_items user_id=%s", user_id)
        return _render_checkout(
            error=translate("commerce.checkout.errors.unpriced_items"),
            form_data=request.form,
            status_code=400,
        )

    shipping_info = _normalize_shipping_form(request.form)
    required_fields = ("name", "street", "house_number", "city", "postal_code")
    if any(not shipping_info[field] for field in required_fields):
        logger.warning("checkout_create_order_invalid_shipping user_id=%s", user_id)
        return _render_checkout(
            error=translate("commerce.checkout.errors.shipping_required"),
            form_data=request.form,
            status_code=400,
        )

    carrier = (request.form.get("shipping_carrier") or "").strip() or None
    service = (request.form.get("shipping_service") or "").strip() or None
    chosen_shipping, _ = _resolve_shipping(
        total_weight_grams, shipping_info["country"], carrier, service
    )
    shipping_sats = chosen_shipping["price_sats"]
    access_token = secrets.token_urlsafe(32) if user_id is None else None
    order_id = create_order_record(
        user_id=user_id,
        session_id=session_id,
        items=items,
        shipping_info=shipping_info,
        total_sats=total_sats,
        shipping_sats=shipping_sats,
        shipping_carrier=chosen_shipping.get("carrier"),
        shipping_service=chosen_shipping.get("service"),
        access_token=access_token,
    )

    method = (request.form.get("payment_method") or "lightning").strip().lower()
    # Validate the chosen method against what the admin enabled; fall back to
    # the first enabled rail (Lightning). create_invoice() is the source of
    # truth for whether Coinos can actually settle, returning None otherwise.
    enabled_methods = get_enabled_methods() or ["lightning"]
    if method not in enabled_methods:
        method = enabled_methods[0]
    coinos_type = PAYMENT_METHODS[method]

    webhook_url = request.url_root.rstrip("/") + url_for("checkout.coinos_webhook")
    invoice = create_invoice(total_sats + shipping_sats, invoice_type=method, webhook_url=webhook_url)
    invoice_hash = (invoice or {}).get("hash", "")
    payable = (invoice or {}).get("text", "")
    if not invoice_hash or not payable:
        delete_order(order_id)
        logger.warning("checkout_invoice_creation_failed order_id=%s user_id=%s", order_id, user_id)
        return _render_checkout(
            error=translate("commerce.checkout.errors.invoice_failed"),
            form_data=request.form,
            status_code=502,
        )

    bolt11 = payable if method == "lightning" else None
    btc_address = payable if method in ("liquid", "onchain") else None
    set_order_payment(
        order_id,
        invoice_hash,
        bolt11,
        payment_method=method,
        invoice_type=coinos_type,
        btc_address=btc_address,
    )
    clear_cart(session_id, user_id)
    if user_id is None:
        _remember_guest_order(order_id)
    logger.info(
        "checkout_order_created order_id=%s user_id=%s total_sats=%s shipping_sats=%s",
        order_id,
        user_id,
        total_sats,
        shipping_sats,
    )
    return redirect(url_for("checkout.payment_page", order_id=order_id))


@checkout.route("/checkout/payment/<int:order_id>")
def payment_page(order_id):
    order = _ensure_order_access(get_order(order_id))
    payable = order.get("bolt11") or order.get("btc_address")
    if not payable:
        return redirect(_order_detail_url(order))
    logger.info("checkout_payment_page_viewed order_id=%s user_id=%s", order_id, session.get("user_id"))

    return _no_store(make_response(render_template(
        "payment.html",
        active="orders",
        order=order,
        payable=payable,
        qr_url=url_for("checkout.order_payment_qr", order_id=order_id),
        order_detail_url=_order_detail_url(order),
    )))


@checkout.route("/api/checkout/check-payment/<int:order_id>")
def check_payment(order_id):
    order = _ensure_order_access(get_order(order_id))
    if order.get("payment_confirmed_at") or order.get("status") in {"paid", "processing", "shipped", "delivered"}:
        logger.info("checkout_payment_already_confirmed order_id=%s", order_id)
        return _no_store(jsonify({"paid": True}))

    invoice_hash = order.get("invoice_hash")
    if not invoice_hash:
        response = jsonify({"paid": False, "error": "invoice_missing"})
        response.status_code = 400
        return _no_store(response)

    invoice = check_invoice(invoice_hash)
    try:
        received = int((invoice or {}).get("received", 0) or 0)
    except (TypeError, ValueError):
        received = 0

    if received > 0:
        confirm_order_payment(order_id)
        logger.info("checkout_payment_confirmed order_id=%s received=%s", order_id, received)
        return _no_store(jsonify({"paid": True}))
    logger.info("checkout_payment_pending order_id=%s", order_id)
    return _no_store(jsonify({"paid": False}))


@checkout.route("/checkout/payment/<int:order_id>/qr")
def order_payment_qr(order_id):
    order = _ensure_order_access(get_order(order_id))
    payable = order.get("bolt11") or order.get("btc_address")
    response = get_invoice_qr_response(payable)
    if response is None:
        abort(400)
    return _no_store(response)


@checkout.route("/orders/lookup", methods=["GET", "POST"])
def order_lookup():
    error = None
    form_data = {}
    if request.method == "POST":
        form_data = {
            "order_id": (request.form.get("order_id") or "").strip(),
            "access_token": (request.form.get("access_token") or "").strip(),
        }
        try:
            order_id = int(form_data["order_id"])
        except (TypeError, ValueError):
            order_id = 0
        order = get_guest_order_by_access_token(order_id, form_data["access_token"])
        if order is not None:
            _remember_guest_order(order_id)
            return _no_store(redirect(url_for("checkout.order_detail", order_id=order_id)))
        error = translate("account.order_lookup.invalid")

    response = make_response(render_template(
        "order_lookup.html",
        active="order_lookup",
        error=error,
        form_data=form_data,
    ))
    if error:
        response.status_code = 404
    return _no_store(response)


@checkout.route("/orders/<int:order_id>")
def order_detail(order_id):
    order = _ensure_order_access(get_order(order_id))
    return _no_store(make_response(render_template(
        "account/order_detail.html",
        active="orders",
        order=order,
    )))


@checkout.route("/orders/<int:order_id>/receipt.pdf")
def order_pdf(order_id):
    order = _ensure_order_access(get_order(order_id))
    contacts = {
        "whatsapp": get_config("whatsapp"),
        "telegram": get_config("telegram"),
    }
    tracking_url = (
        _public_url("account.order_detail", order_id=order_id)
        if order.get("user_id") is not None
        else _public_url("checkout.order_lookup")
    )
    pdf = build_order_pdf(
        order,
        contacts=contacts,
        tracking_url=tracking_url,
        labels=_pdf_labels(),
    )
    response = send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"sandlabs-order-{order_id}.pdf",
        max_age=0,
    )
    return _no_store(response)


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
