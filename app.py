import logging
import os

from flask import Flask, abort, redirect, request, session

import config
from init_db import init_db
from routes.routes_account import account
from routes.routes_admin import admin
from routes.routes_auth import auth
from routes.routes_cart import cart
from routes.routes_checkout import checkout
from routes.routes_public import public

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


app = Flask(__name__, static_url_path="")
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

CSRF_EXEMPT = set()
CSRF_EXEMPT.add("/checkout/webhook/coinos")


@app.before_request
def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = os.urandom(16).hex()


@app.before_request
def csrf_protect():
    if request.method == "POST":
        if request.path in CSRF_EXEMPT:
            return
        token = session.get("csrf_token", "")
        form_token = request.form.get("csrf_token", "") or request.headers.get("X-CSRFToken", "")
        if not token or token != form_token:
            abort(403)


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not app.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


init_db()
app.register_blueprint(public)
app.register_blueprint(cart)
app.register_blueprint(auth)
app.register_blueprint(account)
app.register_blueprint(checkout)
app.register_blueprint(admin)


# Legacy .html redirects so existing JS links (e.g. location.href='produtos.html') keep working
_HTML_ROUTES = {
    "index.html": "public.index",
    "produtos.html": "public.produtos",
    "carrinho.html": "cart.cart_page",
    "sobre.html": "public.sobre",
    "termos.html": "public.termos",
    "suporte.html": "public.suporte",
    "config.html": "public.config_page",
    "login.html": "auth.login",
    "register.html": "auth.register",
}


@app.route("/<page>.html")
def legacy_html_redirect(page):
    endpoint = _HTML_ROUTES.get(f"{page}.html")
    if endpoint:
        qs = request.query_string.decode()
        target = redirect(f"/{page if page != 'index' else ''}" + (f"?{qs}" if qs else ""), code=301)
        return target
    return "Not found", 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
