import os

import config
import db
from services.service_security import encrypt_value
from werkzeug.security import generate_password_hash


SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    summary         TEXT NOT NULL,
    details_html    TEXT NOT NULL DEFAULT '',
    weight_grams    INTEGER DEFAULT 200,
    buy_button_text TEXT NOT NULL DEFAULT 'Comprar',
    allow_addon_seed INTEGER DEFAULT 0,
    badge_text      TEXT,
    badge_variant   TEXT,
    sort_order      INTEGER DEFAULT 0,
    active          INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS product_prices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   TEXT NOT NULL,
    label        TEXT NOT NULL,
    amount_sats  INTEGER NOT NULL,
    pricing_mode TEXT,
    currency_code TEXT,
    amount_fiat  TEXT,
    display_text TEXT NOT NULL,
    sort_order   INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_images (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    filename   TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  TEXT NOT NULL,
    option_type TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    sort_order  INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS colors (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    display_name  TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    is_admin      INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cart_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT,
    user_id      INTEGER,
    product_id   TEXT NOT NULL,
    price_id     INTEGER NOT NULL,
    quantity     INTEGER DEFAULT 1,
    options_json TEXT DEFAULT '{}',
    created_at   TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (price_id) REFERENCES product_prices(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER,
    session_id           TEXT,
    status               TEXT DEFAULT 'pending',
    total_sats           INTEGER NOT NULL,
    shipping_sats        INTEGER DEFAULT 0,
    invoice_hash         TEXT,
    bolt11               TEXT,
    payment_confirmed_at TEXT,
    shipping_name        TEXT,
    shipping_address     TEXT,
    shipping_postal_code TEXT,
    shipping_country     TEXT DEFAULT 'CH',
    shipping_tracking    TEXT,
    coupon_code          TEXT,
    notes                TEXT DEFAULT '',
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL,
    product_id   TEXT NOT NULL,
    price_id     INTEGER NOT NULL,
    quantity     INTEGER DEFAULT 1,
    unit_sats    INTEGER NOT NULL,
    options_json TEXT DEFAULT '{}',
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ip           TEXT NOT NULL,
    attempted_at TEXT DEFAULT (datetime('now'))
);
"""

DEFAULT_COLORS = [
    ("amarelo", "Amarelo"),
    ("azul", "Azul"),
    ("laranja", "Laranja"),
    ("preto", "Preto"),
    ("translucido", "Translúcido"),
    ("vermelho", "Vermelho"),
]


def _ensure_column(conn, table_name, column_name, column_sql):
    existing_columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def _migrate_legacy_shipping_data(conn):
    rows = conn.execute(
        """
        SELECT
            id,
            shipping_name,
            shipping_address,
            shipping_postal_code,
            shipping_country,
            shipping_name_enc,
            shipping_street_enc,
            shipping_house_number_enc,
            shipping_address_extra_enc,
            shipping_city_enc,
            shipping_postal_code_enc,
            shipping_country_enc
        FROM orders
        """
    ).fetchall()

    for row in rows:
        has_legacy = any(
            (row[column] or "").strip()
            for column in (
                "shipping_name",
                "shipping_address",
                "shipping_postal_code",
                "shipping_country",
            )
        )
        has_encrypted = any(
            (row[column] or "").strip()
            for column in (
                "shipping_name_enc",
                "shipping_street_enc",
                "shipping_house_number_enc",
                "shipping_address_extra_enc",
                "shipping_city_enc",
                "shipping_postal_code_enc",
                "shipping_country_enc",
            )
        )
        if not has_legacy or has_encrypted:
            continue

        conn.execute(
            """
            UPDATE orders
            SET
                shipping_name_enc = ?,
                shipping_street_enc = ?,
                shipping_house_number_enc = ?,
                shipping_address_extra_enc = ?,
                shipping_city_enc = ?,
                shipping_postal_code_enc = ?,
                shipping_country_enc = ?,
                shipping_name = NULL,
                shipping_address = NULL,
                shipping_postal_code = NULL,
                shipping_country = NULL,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                encrypt_value(row["shipping_name"]),
                encrypt_value(row["shipping_address"]),
                "",
                "",
                "",
                encrypt_value(row["shipping_postal_code"]),
                encrypt_value(row["shipping_country"] or "CH"),
                row["id"],
            ),
        )


def init_db():
    db_dir = os.path.dirname(config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = db.get_db()
    try:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "product_prices", "pricing_mode", "pricing_mode TEXT")
        _ensure_column(conn, "product_prices", "currency_code", "currency_code TEXT")
        _ensure_column(conn, "product_prices", "amount_fiat", "amount_fiat TEXT")
        _ensure_column(conn, "orders", "shipping_name_enc", "shipping_name_enc TEXT")
        _ensure_column(conn, "orders", "shipping_street_enc", "shipping_street_enc TEXT")
        _ensure_column(conn, "orders", "shipping_house_number_enc", "shipping_house_number_enc TEXT")
        _ensure_column(conn, "orders", "shipping_address_extra_enc", "shipping_address_extra_enc TEXT")
        _ensure_column(conn, "orders", "shipping_city_enc", "shipping_city_enc TEXT")
        _ensure_column(conn, "orders", "shipping_postal_code_enc", "shipping_postal_code_enc TEXT")
        _ensure_column(conn, "orders", "shipping_country_enc", "shipping_country_enc TEXT")
        _migrate_legacy_shipping_data(conn)
        conn.executemany(
            """
            INSERT INTO colors (id, name)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET name = excluded.name
            """,
            DEFAULT_COLORS,
        )
        if config.ADMIN_PASSWORD:
            admin_email = f"{config.ADMIN_USERNAME}@admin.local"
            admin_exists = conn.execute(
                "SELECT id FROM users WHERE email = ? LIMIT 1",
                (admin_email,),
            ).fetchone()
            if admin_exists is None:
                conn.execute(
                    """
                    INSERT INTO users (email, display_name, password_hash, is_admin)
                    VALUES (?, ?, ?, 1)
                    """,
                    (
                        admin_email,
                        config.ADMIN_USERNAME,
                        generate_password_hash(config.ADMIN_PASSWORD),
                    ),
                )
            conn.execute(
                """
                INSERT INTO config (key, value) VALUES ('setup_complete', '1')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
        conn.commit()
    finally:
        conn.close()
