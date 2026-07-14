import json

from flask import Blueprint, jsonify, render_template

from i18n import current_lang, localize_products
from models.model_products import get_all_products, products_to_js_format
from services.service_btc_price import CACHE_TTL, get_display_rates

public = Blueprint("public", __name__)


@public.route("/api/pricing/rates")
def pricing_rates():
    """Expose cached BTC/fiat rates used only for storefront display."""
    response = jsonify({
        "base": "BTC",
        "rates": get_display_rates(),
        "ttl_seconds": CACHE_TTL,
    })
    response.headers["Cache-Control"] = f"private, max-age={CACHE_TTL}"
    return response


@public.route("/")
def index():
    products = get_all_products()
    products_json = json.dumps(
        localize_products(products_to_js_format(products), current_lang()),
        ensure_ascii=False,
    )
    return render_template("index.html", active="inicio", products_json=products_json)


@public.route("/produtos")
def produtos():
    products = get_all_products()
    products_json = json.dumps(
        localize_products(products_to_js_format(products), current_lang()),
        ensure_ascii=False,
    )
    return render_template("produtos.html", active="produtos", products_json=products_json)


@public.route("/sobre")
def sobre():
    return render_template("sobre.html", active="sobre")


@public.route("/termos")
def termos():
    return render_template("termos.html", active="termos")


@public.route("/suporte")
def suporte():
    return render_template("suporte.html", active="suporte")


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500
