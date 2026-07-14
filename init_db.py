import os

import config
import db
from services.service_security import email_blind_index, encrypt_value
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
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    email_enc        TEXT NOT NULL,
    email_bidx       TEXT UNIQUE NOT NULL,
    display_name_enc TEXT NOT NULL DEFAULT '',
    password_hash    TEXT NOT NULL,
    is_admin         INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT (datetime('now'))
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


def _migrate_users_pii(conn):
    """Rebuild a legacy ``users`` table (plaintext ``email``) into the encrypted
    schema (``email_enc`` / ``email_bidx`` / ``display_name_enc``).

    Idempotent: once the plaintext ``email`` column is gone, this is a no-op.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "email" not in columns:
        return  # already migrated (or fresh DB created with the new schema)

    legacy_rows = conn.execute(
        "SELECT id, email, display_name, password_hash, is_admin, created_at FROM users"
    ).fetchall()

    # PRAGMA foreign_keys cannot change inside a transaction; commit any pending
    # implicit transaction first, then disable FKs so the DROP/RENAME below does
    # not trip enforcement (row ids are preserved, so FKs stay valid).
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE users_new (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_enc        TEXT NOT NULL,
                    email_bidx       TEXT UNIQUE NOT NULL,
                    display_name_enc TEXT NOT NULL DEFAULT '',
                    password_hash    TEXT NOT NULL,
                    is_admin         INTEGER DEFAULT 0,
                    created_at       TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.executemany(
                """
                INSERT INTO users_new (
                    id, email_enc, email_bidx, display_name_enc,
                    password_hash, is_admin, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["id"],
                        encrypt_value(row["email"]),
                        email_blind_index(row["email"]),
                        encrypt_value(row["display_name"]),
                        row["password_hash"],
                        row["is_admin"],
                        row["created_at"],
                    )
                    for row in legacy_rows
                ],
            )
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_new RENAME TO users")
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def init_db():
    db_dir = os.path.dirname(config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = db.get_db()
    try:
        conn.executescript(SCHEMA)
        _migrate_users_pii(conn)
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
            admin_bidx = email_blind_index(admin_email)
            admin_exists = conn.execute(
                "SELECT id FROM users WHERE email_bidx = ? LIMIT 1",
                (admin_bidx,),
            ).fetchone()
            if admin_exists is None:
                conn.execute(
                    """
                    INSERT INTO users (email_enc, email_bidx, display_name_enc, password_hash, is_admin)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (
                        encrypt_value(admin_email),
                        admin_bidx,
                        encrypt_value(config.ADMIN_USERNAME),
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
