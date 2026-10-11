import config
import db


DEFAULT_CONFIG = {
    "setup_complete": "0",
    "coinos_api_key": config.COINOS_API_KEY,
    "coinos_webhook_secret": config.COINOS_WEBHOOK_SECRET,
    "coinos_enabled": "1" if config.COINOS_ENABLED else "0",
    "coinos_liquid": "0",
    "coinos_onchain": "0",
    "dhl_enabled": "0",
    "dhl_api_key": "",
    "dhl_api_url": "",
    "swisspost_enabled": "0",
    "swisspost_client_id": "",
    "swisspost_client_secret": "",
    "swisspost_franking_license": "",
    "swisspost_sender_name": "",
    "swisspost_sender_street": "",
    "swisspost_sender_zip": "",
    "swisspost_sender_city": "",
    "swisspost_label_live": "0",
    "google_login_enabled": "0",
    "google_client_id": "",
    "google_client_secret": "",
    "whatsapp": "",
    "telegram": "",
}


def admin_exists():
    conn = db.get_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM users WHERE is_admin = 1 LIMIT 1"
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_config(key, default=None):
    conn = db.get_db()
    try:
        row = conn.execute(
            "SELECT value FROM config WHERE key = ?",
            (key,),
        ).fetchone()
    finally:
        conn.close()

    if row is not None:
        return row["value"]
    if default is not None:
        return default
    if key == "setup_complete" and admin_exists():
        return "1"
    return DEFAULT_CONFIG.get(key, "")


def get_all_config():
    cfg = dict(DEFAULT_CONFIG)
    conn = db.get_db()
    try:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
    finally:
        conn.close()

    cfg.update({row["key"]: row["value"] for row in rows})
    if admin_exists():
        cfg["setup_complete"] = "1"
    return cfg


def set_config(key, value):
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO config(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, "" if value is None else str(value)),
            )
    finally:
        conn.close()


def get_bool_config(key, default=False):
    fallback = "1" if default else "0"
    return get_config(key, fallback) == "1"


def is_setup_complete():
    return admin_exists()


def get_coinos_config():
    return {
        "api_key": get_config("coinos_api_key"),
        "webhook_secret": get_config("coinos_webhook_secret"),
        "enabled": get_bool_config("coinos_enabled", config.COINOS_ENABLED),
        "liquid": get_bool_config("coinos_liquid", False),
        "onchain": get_bool_config("coinos_onchain", False),
    }
