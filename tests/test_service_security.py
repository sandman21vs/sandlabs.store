"""Tests for PII encryption, blind indexes, and the users PII migration."""

import sqlite3


def test_encrypt_decrypt_roundtrip():
    from services.service_security import decrypt_value, encrypt_value

    token = encrypt_value("Bahnhofstrasse 1")
    assert token != "Bahnhofstrasse 1"
    assert decrypt_value(token) == "Bahnhofstrasse 1"


def test_encrypt_is_randomized_but_decrypts():
    from services.service_security import decrypt_value, encrypt_value

    a = encrypt_value("same value")
    b = encrypt_value("same value")
    assert a != b  # Fernet embeds a random IV/timestamp
    assert decrypt_value(a) == decrypt_value(b) == "same value"


def test_empty_values():
    from services.service_security import blind_index, decrypt_value, encrypt_value

    assert encrypt_value("") == ""
    assert encrypt_value(None) == ""
    assert decrypt_value("") == ""
    assert blind_index("") == ""


def test_decrypt_garbage_returns_empty():
    from services.service_security import decrypt_value

    assert decrypt_value("not-a-valid-token") == ""


def test_blind_index_deterministic_and_opaque():
    from services.service_security import blind_index

    idx = blind_index("hello@example.com")
    assert idx == blind_index("hello@example.com")
    assert idx != "hello@example.com"
    assert len(idx) == 64  # hex sha256


def test_email_blind_index_is_case_insensitive():
    from services.service_security import email_blind_index

    assert email_blind_index("USER@Example.com") == email_blind_index("user@example.com")
    assert email_blind_index("  user@example.com  ") == email_blind_index("user@example.com")


def test_legacy_ciphertext_still_decrypts():
    """Values encrypted with the previous (legacy) Fernet key must still be
    readable through the MultiFernet backward-compat path. We encrypt with the
    module's own cached legacy key to stay independent of import timing."""
    from services import service_security as sec

    legacy_fernet = sec._FERNET._fernets[1]  # index 0 = primary, 1 = legacy
    legacy_token = legacy_fernet.encrypt(b"legacy address").decode()

    assert sec.decrypt_value(legacy_token) == "legacy address"


def test_users_pii_migration_rebuilds_legacy_table(tmp_path):
    """A legacy users table (plaintext email) is rebuilt into the encrypted
    schema, preserving ids and enabling blind-index lookup."""
    from init_db import _migrate_users_pii
    from services.service_security import decrypt_value, email_blind_index

    db_file = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            display_name  TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            is_admin      INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash, is_admin) "
        "VALUES (7, 'legacy@example.com', 'Legacy', 'hash', 1)"
    )
    conn.commit()

    _migrate_users_pii(conn)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    assert "email" not in columns
    assert {"email_enc", "email_bidx", "display_name_enc"} <= columns

    row = conn.execute(
        "SELECT * FROM users WHERE email_bidx = ?",
        (email_blind_index("legacy@example.com"),),
    ).fetchone()
    assert row["id"] == 7
    assert decrypt_value(row["email_enc"]) == "legacy@example.com"
    assert decrypt_value(row["display_name_enc"]) == "Legacy"

    # Idempotent: running again is a no-op.
    _migrate_users_pii(conn)
    assert conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] == 1
    conn.close()


def test_create_user_stores_no_plaintext_email(tmp_db):
    """End-to-end: create_user encrypts email; DB holds no plaintext, but
    get_user_by_email still resolves it via the blind index."""
    import db as db_mod
    from models.model_users import create_user, get_user_by_email

    create_user("Person@Example.com", "pw12345", display_name="Person")

    user = get_user_by_email("person@example.com")
    assert user is not None
    assert user["email"] == "person@example.com"
    assert user["display_name"] == "Person"

    conn = db_mod.get_db()
    try:
        row = conn.execute("SELECT email_enc, email_bidx FROM users").fetchone()
    finally:
        conn.close()
    assert "example.com" not in row["email_enc"]
    assert row["email_bidx"] == email_bidx_of("person@example.com")


def email_bidx_of(email):
    from services.service_security import email_blind_index

    return email_blind_index(email)
