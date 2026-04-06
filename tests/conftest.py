"""Shared fixtures for all tests."""

import os as pyos
import os
import sys
import tempfile

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture()
def tmp_db(tmp_path):
    """Override DATABASE_PATH to a temp file before importing anything."""
    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_PATH"] = db_path
    os.environ["SECRET_KEY"] = "test-secret-key"

    # Reload config so it picks up the env var
    import config
    import importlib
    importlib.reload(config)

    # Initialize schema
    import init_db
    importlib.reload(init_db)
    init_db.init_db()

    yield db_path

    # Cleanup: remove override
    os.environ.pop("DATABASE_PATH", None)
    importlib.reload(config)


@pytest.fixture()
def app(tmp_db):
    """Create a Flask test app with a fresh temp database."""
    import importlib

    # Reload modules that cache config at import time
    import config
    importlib.reload(config)
    import db as db_mod
    importlib.reload(db_mod)
    import models.model_config as mcfg
    importlib.reload(mcfg)
    import models.model_products as mp
    importlib.reload(mp)
    import models.model_cart as mc
    importlib.reload(mc)
    import routes.routes_public as rp
    importlib.reload(rp)
    import routes.routes_cart as rc
    importlib.reload(rc)
    import routes.routes_checkout as rco
    importlib.reload(rco)
    import models.model_users as mu
    importlib.reload(mu)
    import models.model_orders as mo
    importlib.reload(mo)
    import routes.routes_auth as ra
    importlib.reload(ra)
    import routes.routes_account as racc
    importlib.reload(racc)
    import routes.routes_admin as radm
    importlib.reload(radm)

    from flask import Flask
    test_app = Flask(
        __name__,
        static_url_path="",
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
    )
    test_app.secret_key = "test-secret-key"
    test_app.config["TESTING"] = True

    @test_app.before_request
    def generate_csrf_token():
        from flask import session

        if "csrf_token" not in session:
            session["csrf_token"] = pyos.urandom(16).hex()

    @test_app.before_request
    def csrf_protect():
        from flask import abort, request, session

        csrf_exempt = {"/checkout/webhook/coinos"}
        if request.method == "POST":
            if request.path in csrf_exempt:
                return
            token = session.get("csrf_token", "")
            form_token = request.form.get("csrf_token", "") or request.headers.get("X-CSRFToken", "")
            if not token or token != form_token:
                abort(403)

    @test_app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    test_app.register_blueprint(rp.public)
    test_app.register_blueprint(rc.cart)
    test_app.register_blueprint(rco.checkout)
    test_app.register_blueprint(ra.auth)
    test_app.register_blueprint(racc.account)
    test_app.register_blueprint(radm.admin)

    @test_app.route("/health")
    def health():
        return {"status": "ok"}, 200

    # Register legacy .html redirects (same as app.py)
    from flask import redirect, request as flask_request
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

    @test_app.route("/<page>.html")
    def legacy_html_redirect(page):
        endpoint = _HTML_ROUTES.get(f"{page}.html")
        if endpoint:
            qs = flask_request.query_string.decode()
            target = redirect(
                f"/{page if page != 'index' else ''}" + (f"?{qs}" if qs else ""),
                code=301,
            )
            return target
        return "Not found", 404

    yield test_app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def csrf_token(client):
    """Return the CSRF token for the current client session."""
    client.get("/")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


@pytest.fixture()
def csrf_headers(csrf_token):
    """Return headers with the current CSRF token."""
    return {"X-CSRFToken": csrf_token}


@pytest.fixture()
def db_conn(tmp_db):
    """Return a raw database connection for direct assertions."""
    import db as db_mod
    conn = db_mod.get_db()
    yield conn
    conn.close()


@pytest.fixture()
def sample_product_data():
    """Minimal product data dict for creating test products."""
    return {
        "id": "test-product",
        "name": "Test Product",
        "summary": "A test product for unit tests.",
        "details_html": "<p>Details here</p>",
        "weight_grams": 150,
        "buy_button_text": "Buy Test",
        "allow_addon_seed": True,
        "badge_text": "New",
        "badge_variant": "new",
        "sort_order": 0,
        "active": True,
        "prices": [
            {"label": "Base", "amount_sats": 10000, "display_text": "10 000 sats", "sort_order": 0},
            {"label": "Premium", "amount_sats": 25000, "display_text": "25 000 sats", "sort_order": 1},
        ],
        "images": [
            {"filename": "images/test1.png", "sort_order": 0},
            {"filename": "images/test2.png", "sort_order": 1},
        ],
        "options": [
            {
                "type": "colorPair",
                "title": "Cores",
                "inputs": [
                    {"name": "bodyColor", "label": "Corpo"},
                    {"name": "capColor", "label": "Tampa"},
                ],
            },
        ],
    }


@pytest.fixture()
def seeded_product(tmp_db, sample_product_data):
    """Insert sample product into DB and return its data."""
    from models.model_products import create_product
    return create_product(sample_product_data)


@pytest.fixture()
def test_user(tmp_db):
    """Create a test user in the DB and return its id."""
    import db as db_mod
    conn = db_mod.get_db()
    try:
        conn.execute(
            "INSERT INTO users (id, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
            (1, "test@test.com", "Test User", "fakehash"),
        )
        conn.commit()
    finally:
        conn.close()
    return 1


@pytest.fixture()
def admin_user(tmp_db):
    """Create an admin user and return (id, email, password)."""
    from werkzeug.security import generate_password_hash
    import db as db_mod
    conn = db_mod.get_db()
    try:
        conn.execute(
            "INSERT INTO users (email, display_name, password_hash, is_admin) VALUES (?,?,?,1)",
            ("admin@test.com", "Admin", generate_password_hash("adminpass123")),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM users WHERE email='admin@test.com'").fetchone()
    finally:
        conn.close()
    return {"id": row["id"], "email": "admin@test.com", "password": "adminpass123"}


@pytest.fixture()
def admin_client(client, admin_user):
    """Test client with an active admin session."""
    with client.session_transaction() as sess:
        sess["user_id"] = admin_user["id"]
        sess["is_admin"] = True
        sess["display_name"] = "Admin"
    return client
