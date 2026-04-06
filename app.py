import logging

from flask import Flask, redirect, request

import config
from routes.routes_public import public

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


app = Flask(__name__, static_url_path="")
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

app.register_blueprint(public)


# Legacy .html redirects so existing JS links (e.g. location.href='produtos.html') keep working
_HTML_ROUTES = {
    "index.html": "public.index",
    "produtos.html": "public.produtos",
    "sobre.html": "public.sobre",
    "termos.html": "public.termos",
    "suporte.html": "public.suporte",
    "config.html": "public.config_page",
}


@app.route("/<page>.html")
def legacy_html_redirect(page):
    endpoint = _HTML_ROUTES.get(f"{page}.html")
    if endpoint:
        qs = request.query_string.decode()
        target = redirect(f"/{page if page != 'index' else ''}" + (f"?{qs}" if qs else ""), code=301)
        return target
    return "Not found", 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
