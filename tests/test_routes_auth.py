"""Tests for authentication and account routes."""

from models.model_users import create_user


class TestRegister:
    def test_register_logs_user_in(self, client, csrf_token):
        response = client.post(
            "/auth/register",
            data={
                "csrf_token": csrf_token,
                "display_name": "New User",
                "email": "new@example.com",
                "password": "supersecret",
                "password_confirm": "supersecret",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["Location"] == "/"
        with client.session_transaction() as sess:
            assert sess.get("user_id")
            assert sess.get("display_name") == "New User"


class TestLogin:
    def test_login_merges_anonymous_cart(self, client, csrf_token, csrf_headers, seeded_product):
        pid = seeded_product["id"]
        price_id = seeded_product["prices"][0]["id"]
        create_user("merge@example.com", "supersecret", "Merge User")

        add_resp = client.post(
            "/api/cart/add",
            json={"product_id": pid, "price_id": price_id, "quantity": 1, "options": {}},
            headers=csrf_headers,
        )
        assert add_resp.status_code == 200

        response = client.post(
            "/auth/login",
            data={
                "csrf_token": csrf_token,
                "email": "merge@example.com",
                "password": "supersecret",
                "next": "http://localhost/account/orders",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["Location"] == "/account/orders"
        with client.session_transaction() as sess:
            assert sess.get("user_id")

        cart = client.get("/api/cart").get_json()
        assert cart["count"] == 1

    def test_wrong_password_rate_limits_on_fifth_attempt(self, client, csrf_token):
        create_user("ratelimit@example.com", "supersecret", "Limit User")

        for attempt in range(1, 6):
            response = client.post(
                "/auth/login",
                data={
                    "csrf_token": csrf_token,
                    "email": "ratelimit@example.com",
                    "password": "wrong",
                },
                environ_overrides={"REMOTE_ADDR": "10.8.8.8"},
            )
            expected = 429 if attempt == 5 else 401
            assert response.status_code == expected

    def test_invalid_csrf_returns_403(self, client, csrf_token):
        create_user("csrf@example.com", "supersecret", "Csrf User")

        response = client.post(
            "/auth/login",
            data={
                "csrf_token": "invalid-token",
                "email": "csrf@example.com",
                "password": "supersecret",
            },
        )
        assert response.status_code == 403


class TestLogout:
    def test_logout_clears_session(self, client, csrf_token):
        create_user("logout@example.com", "supersecret", "Logout User")
        client.post(
            "/auth/login",
            data={
                "csrf_token": csrf_token,
                "email": "logout@example.com",
                "password": "supersecret",
            },
        )

        with client.session_transaction() as sess:
            logout_token = sess["csrf_token"]
            assert sess.get("user_id")

        response = client.post(
            "/auth/logout",
            data={"csrf_token": logout_token},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["Location"] == "/"
        with client.session_transaction() as sess:
            assert "user_id" not in sess


class TestAccountRoutes:
    def test_orders_requires_login(self, client):
        response = client.get("/account/orders", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login?next=" in response.headers["Location"]
