"""Tests for account order pages."""

from db import get_db
from models.model_users import create_user


def test_order_detail_renders_for_owner(client, csrf_token):
    user_id = create_user("orders@example.com", "supersecret", "Orders User")

    conn = get_db()
    try:
        price = conn.execute(
            "SELECT id, amount_sats FROM product_prices WHERE product_id = 'sandseed' ORDER BY sort_order, id LIMIT 1"
        ).fetchone()
        if price is None:
            conn.execute(
                """
                INSERT INTO products (id, name, summary, details_html, buy_button_text, active)
                VALUES ('sandseed', 'SandSeed', 'Seed backup', '<p>Details</p>', 'Comprar', 1)
                """
            )
            conn.execute(
                """
                INSERT INTO product_prices (product_id, label, amount_sats, display_text, sort_order)
                VALUES ('sandseed', 'Placa avulsa', 2000, '2 000 sats', 0)
                """
            )
            conn.commit()
            price = conn.execute(
                "SELECT id, amount_sats FROM product_prices WHERE product_id = 'sandseed' ORDER BY sort_order, id LIMIT 1"
            ).fetchone()

        cursor = conn.execute(
            """
            INSERT INTO orders (user_id, session_id, status, total_sats, shipping_sats, shipping_country, created_at, updated_at)
            VALUES (?, ?, 'pending', ?, 0, 'CH', datetime('now'), datetime('now'))
            """,
            (user_id, "test-session", int(price["amount_sats"])),
        )
        order_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO order_items (order_id, product_id, price_id, quantity, unit_sats, options_json)
            VALUES (?, 'sandseed', ?, 1, ?, '{}')
            """,
            (order_id, price["id"], int(price["amount_sats"])),
        )
        conn.commit()
    finally:
        conn.close()

    client.post(
        "/auth/login",
        data={
            "csrf_token": csrf_token,
            "email": "orders@example.com",
            "password": "supersecret",
        },
    )
    response = client.get(f"/account/orders/{order_id}")
    html = response.data.decode()

    assert response.status_code == 200
    assert f"Pedido #{order_id}" in html
    assert "SandSeed" in html
