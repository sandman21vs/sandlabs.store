"""Checkout routes.

Phase 6: Shipping calculation endpoint.
Phases 4+5 will add full checkout, order creation, and Lightning payment.
"""
from flask import Blueprint, jsonify, request

from services.service_shipping import calculate_shipping_chf, get_country_zone
from services.service_btc_price import chf_to_sats

checkout = Blueprint("checkout", __name__)


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

    return jsonify({
        "ok": True,
        "shipping_chf": shipping_chf,
        "shipping_sats": shipping_sats,
        "zone": zone,
    })
