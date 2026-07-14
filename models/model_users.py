import sqlite3

import db
from services.service_security import (
    decrypt_value,
    email_blind_index,
    encrypt_value,
)
from werkzeug.security import check_password_hash, generate_password_hash

_USER_SELECT = (
    "SELECT id, email_enc, display_name_enc, password_hash, is_admin, created_at "
    "FROM users"
)


def _normalize_email(email):
    return (email or "").strip().lower()


def _row_to_user(row):
    if row is None:
        return None
    raw = dict(row)
    return {
        "id": raw["id"],
        "email": decrypt_value(raw.get("email_enc")),
        "display_name": decrypt_value(raw.get("display_name_enc")),
        "password_hash": raw["password_hash"],
        "is_admin": bool(raw["is_admin"]),
        "created_at": raw.get("created_at"),
    }


def _cleanup_old_attempts_conn(conn):
    conn.execute(
        "DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-15 minutes')"
    )


def create_user(email, password, display_name="", is_admin=False):
    """Insere usuario. Hash da senha com generate_password_hash(). Retorna user_id."""
    normalized_email = _normalize_email(email)
    if not normalized_email or not password:
        raise ValueError("Email and password are required.")

    conn = db.get_db()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email_enc, email_bidx, display_name_enc, password_hash, is_admin)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    encrypt_value(normalized_email),
                    email_blind_index(normalized_email),
                    encrypt_value((display_name or "").strip()),
                    generate_password_hash(password),
                    1 if is_admin else 0,
                ),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("Email already registered.") from exc
    finally:
        conn.close()


def verify_user(email, password):
    """Busca usuario por email, verifica senha com check_password_hash().
    Retorna dict do usuario ou None.
    """
    user = get_user_by_email(email)
    if not user:
        return None
    if not check_password_hash(user["password_hash"], password or ""):
        return None
    return user


def get_user_by_id(user_id):
    """SELECT por id."""
    conn = db.get_db()
    try:
        row = conn.execute(
            f"{_USER_SELECT} WHERE id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        return _row_to_user(row)
    finally:
        conn.close()


def get_user_by_email(email):
    """SELECT pelo indice cego do email (email nunca fica em texto puro)."""
    conn = db.get_db()
    try:
        row = conn.execute(
            f"{_USER_SELECT} WHERE email_bidx = ? LIMIT 1",
            (email_blind_index(_normalize_email(email)),),
        ).fetchone()
        return _row_to_user(row)
    finally:
        conn.close()


def is_rate_limited(ip):
    """Conta tentativas de login do IP nos ultimos 15 minutos.
    Retorna True se >= 5 tentativas.
    """
    conn = db.get_db()
    try:
        with conn:
            _cleanup_old_attempts_conn(conn)
            row = conn.execute(
                """
                SELECT COUNT(*) AS attempts
                FROM login_attempts
                WHERE ip = ? AND attempted_at >= datetime('now', '-15 minutes')
                """,
                (ip,),
            ).fetchone()
        return int(row["attempts"] or 0) >= 5
    finally:
        conn.close()


def record_login_attempt(ip):
    """INSERT em login_attempts."""
    conn = db.get_db()
    try:
        with conn:
            _cleanup_old_attempts_conn(conn)
            conn.execute(
                "INSERT INTO login_attempts (ip) VALUES (?)",
                ((ip or "").strip(),),
            )
    finally:
        conn.close()


def cleanup_old_attempts():
    """DELETE de tentativas com mais de 15 minutos."""
    conn = db.get_db()
    try:
        with conn:
            _cleanup_old_attempts_conn(conn)
    finally:
        conn.close()
