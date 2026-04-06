"""Tests for database initialization and schema."""

import importlib


def test_schema_creates_all_tables(db_conn):
    """All expected tables exist after init_db()."""
    rows = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    tables = {row["name"] for row in rows}

    expected = {
        "config",
        "products",
        "product_prices",
        "product_images",
        "product_options",
        "colors",
        "users",
        "cart_items",
        "orders",
        "order_items",
        "login_attempts",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_default_colors_seeded(db_conn):
    """The 6 default colors are present after init_db()."""
    rows = db_conn.execute("SELECT id, name FROM colors ORDER BY id").fetchall()
    colors = {row["id"]: row["name"] for row in rows}

    assert colors["amarelo"] == "Amarelo"
    assert colors["azul"] == "Azul"
    assert colors["laranja"] == "Laranja"
    assert colors["preto"] == "Preto"
    assert colors["translucido"] == "Translúcido"
    assert colors["vermelho"] == "Vermelho"
    assert len(colors) == 6


def test_wal_mode_enabled(db_conn):
    """WAL journal mode is active."""
    row = db_conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0] == "wal"


def test_foreign_keys_enabled(db_conn):
    """Foreign key enforcement is on."""
    row = db_conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


def test_init_db_idempotent(tmp_db):
    """Calling init_db() twice doesn't raise or duplicate data."""
    from init_db import init_db
    import db as db_mod

    init_db()  # second call
    conn = db_mod.get_db()
    count = conn.execute("SELECT COUNT(*) FROM colors").fetchone()[0]
    conn.close()
    assert count == 6


def test_admin_bootstrap_creates_admin_user(tmp_path, monkeypatch):
    db_path = str(tmp_path / "admin.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("ADMIN_USERNAME", "owner")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")

    import config
    import db as db_mod
    import init_db

    importlib.reload(config)
    importlib.reload(db_mod)
    importlib.reload(init_db)
    init_db.init_db()

    conn = db_mod.get_db()
    row = conn.execute(
        "SELECT email, display_name, is_admin, password_hash FROM users WHERE email = ?",
        ("owner@admin.local",),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["email"] == "owner@admin.local"
    assert row["display_name"] == "owner"
    assert row["is_admin"] == 1
    assert row["password_hash"] != "admin-secret"
