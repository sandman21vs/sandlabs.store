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


def test_orders_schema_is_standardized(db_conn):
    """Fresh orders table has the new columns and no plaintext shipping columns."""
    columns = {row["name"] for row in db_conn.execute("PRAGMA table_info(orders)").fetchall()}
    # Legacy plaintext shipping columns are gone.
    assert {"shipping_name", "shipping_address", "shipping_postal_code", "shipping_country"}.isdisjoint(columns)
    # Encrypted + new standardized columns are present.
    assert {
        "shipping_name_enc", "shipping_country_enc",
        "shipping_carrier", "shipping_service",
        "payment_method", "invoice_type", "btc_address", "access_token",
    } <= columns


def test_legacy_shipping_columns_migrated_and_dropped(tmp_path):
    """A legacy orders row (plaintext shipping) is migrated into the encrypted
    columns and the plaintext columns are dropped."""
    import sqlite3

    from init_db import (
        _drop_legacy_shipping_columns,
        _ensure_column,
        _migrate_legacy_shipping_data,
    )
    from services.service_security import decrypt_value

    conn = sqlite3.connect(str(tmp_path / "legacy_orders.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE orders (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            total_sats           INTEGER NOT NULL,
            shipping_name        TEXT,
            shipping_address     TEXT,
            shipping_postal_code TEXT,
            shipping_country     TEXT DEFAULT 'CH',
            updated_at           TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        "INSERT INTO orders (id, total_sats, shipping_name, shipping_address, "
        "shipping_postal_code, shipping_country) "
        "VALUES (1, 1000, 'Alice', 'Main St 5', '8000', 'CH')"
    )
    conn.commit()

    # Mirror init_db(): add encrypted columns, migrate data, drop plaintext.
    for col in (
        "shipping_name_enc", "shipping_street_enc", "shipping_house_number_enc",
        "shipping_address_extra_enc", "shipping_city_enc",
        "shipping_postal_code_enc", "shipping_country_enc",
    ):
        _ensure_column(conn, "orders", col, f"{col} TEXT")
    _migrate_legacy_shipping_data(conn)
    _drop_legacy_shipping_columns(conn)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
    assert "shipping_name" not in columns
    row = conn.execute("SELECT * FROM orders WHERE id = 1").fetchone()
    assert decrypt_value(row["shipping_name_enc"]) == "Alice"
    assert decrypt_value(row["shipping_street_enc"]) == "Main St 5"
    assert decrypt_value(row["shipping_country_enc"]) == "CH"
    conn.close()


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

    from services.service_security import decrypt_value, email_blind_index

    conn = db_mod.get_db()
    row = conn.execute(
        "SELECT email_enc, email_bidx, display_name_enc, is_admin, password_hash "
        "FROM users WHERE email_bidx = ?",
        (email_blind_index("owner@admin.local"),),
    ).fetchone()
    conn.close()

    assert row is not None
    # Email is stored encrypted, never in plaintext.
    assert row["email_enc"] != "owner@admin.local"
    assert decrypt_value(row["email_enc"]) == "owner@admin.local"
    assert decrypt_value(row["display_name_enc"]) == "owner"
    assert row["is_admin"] == 1
    assert row["password_hash"] != "admin-secret"
