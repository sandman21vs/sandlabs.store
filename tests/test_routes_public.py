"""Tests for public routes — pages, static files, legacy redirects."""


class TestPublicPages:
    """All public pages return 200 and contain expected content."""

    def test_home_page(self, client, seeded_product):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Sandlabs" in resp.data
        assert b"PRODUTOS" in resp.data  # window.PRODUTOS injected

    def test_produtos_page(self, client, seeded_product):
        resp = client.get("/produtos")
        assert resp.status_code == 200
        assert b"PRODUTOS" in resp.data
        assert b"lightbox" in resp.data

    def test_sobre_page(self, client):
        resp = client.get("/sobre")
        assert resp.status_code == 200
        assert b"Sobre" in resp.data

    def test_termos_page(self, client):
        resp = client.get("/termos")
        assert resp.status_code == 200
        assert b"Termos" in resp.data

    def test_suporte_page(self, client):
        resp = client.get("/suporte")
        assert resp.status_code == 200
        assert b"Suporte" in resp.data

    def test_config_page(self, client):
        resp = client.get("/config")
        assert resp.status_code == 200

    def test_carrinho_page(self, client):
        resp = client.get("/carrinho")
        assert resp.status_code == 200


class TestLegacyHtmlRedirects:
    """Old .html URLs redirect to clean URLs with 301."""

    def test_index_html_redirects_to_root(self, client):
        resp = client.get("/index.html")
        assert resp.status_code == 301
        assert resp.headers["Location"].endswith("/")

    def test_produtos_html_redirects(self, client):
        resp = client.get("/produtos.html")
        assert resp.status_code == 301
        assert "/produtos" in resp.headers["Location"]

    def test_sobre_html_redirects(self, client):
        resp = client.get("/sobre.html")
        assert resp.status_code == 301
        assert "/sobre" in resp.headers["Location"]

    def test_termos_html_redirects(self, client):
        resp = client.get("/termos.html")
        assert resp.status_code == 301

    def test_suporte_html_redirects(self, client):
        resp = client.get("/suporte.html")
        assert resp.status_code == 301

    def test_config_html_redirects(self, client):
        resp = client.get("/config.html")
        assert resp.status_code == 301

    def test_query_string_preserved(self, client):
        resp = client.get("/produtos.html?cupom=TEST123")
        assert resp.status_code == 301
        assert "cupom=TEST123" in resp.headers["Location"]

    def test_unknown_html_returns_404(self, client):
        resp = client.get("/nonexistent.html")
        assert resp.status_code == 404


class TestStaticFiles:
    """Static assets are served at root paths (no /static/ prefix)."""

    def test_css_served(self, client):
        resp = client.get("/css/style.css")
        assert resp.status_code == 200
        assert b"--bg:" in resp.data or b"root" in resp.data

    def test_js_served(self, client):
        resp = client.get("/js/config.js")
        assert resp.status_code == 200

    def test_image_served(self, client):
        resp = client.get("/images/logo.png")
        assert resp.status_code == 200
        assert resp.content_type.startswith("image/")


class TestProductInjection:
    """Products from DB are injected as window.PRODUTOS in templates."""

    def test_product_data_in_home(self, client, seeded_product):
        resp = client.get("/")
        html = resp.data.decode()
        assert "window.PRODUTOS" in html
        assert "test-product" in html
        assert "Test Product" in html

    def test_product_data_in_produtos(self, client, seeded_product):
        resp = client.get("/produtos")
        html = resp.data.decode()
        assert "window.PRODUTOS" in html
        assert "test-product" in html

    def test_empty_produtos_array_when_no_products(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert "window.PRODUTOS = []" in html


class TestNavigation:
    """Navigation links and active states."""

    def test_home_has_active_inicio(self, client, seeded_product):
        html = client.get("/").data.decode()
        assert 'nav-link active" href="/"' in html or "active" in html

    def test_all_nav_links_present(self, client, seeded_product):
        html = client.get("/").data.decode()
        for page in ["Sobre", "Produtos", "Termos", "Suporte"]:
            assert page in html
