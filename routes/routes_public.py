from flask import Blueprint, render_template

public = Blueprint("public", __name__)


@public.route("/")
def index():
    return render_template("index.html", active="inicio")


@public.route("/produtos")
def produtos():
    return render_template("produtos.html", active="produtos")


@public.route("/sobre")
def sobre():
    return render_template("sobre.html", active="sobre")


@public.route("/termos")
def termos():
    return render_template("termos.html", active="termos")


@public.route("/suporte")
def suporte():
    return render_template("suporte.html", active="suporte")


@public.route("/config")
def config_page():
    return render_template("config.html", active="config")


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500
