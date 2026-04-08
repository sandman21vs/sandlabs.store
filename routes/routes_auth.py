from urllib.parse import urlsplit

from flask import Blueprint, redirect, render_template, request, session, url_for

from i18n import translate
from models.model_cart import merge_cart
from models.model_users import (
    cleanup_old_attempts,
    create_user,
    get_user_by_email,
    is_rate_limited,
    record_login_attempt,
    verify_user,
)


auth = Blueprint("auth", __name__)


def _client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _is_safe_next_url(target):
    if not target:
        return False
    parts = urlsplit(target)
    host = urlsplit(request.host_url)
    if not parts.netloc:
        return parts.path.startswith("/")
    return parts.scheme in {"http", "https"} and parts.netloc == host.netloc


def _redirect_target(target):
    if not _is_safe_next_url(target):
        return url_for("public.index")
    parts = urlsplit(target)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return path


def _login_user(user):
    session["user_id"] = user["id"]
    session["is_admin"] = bool(user["is_admin"])
    session["display_name"] = user.get("display_name", "")
    if "cart_session" in session:
        merge_cart(session["cart_session"], user["id"])


@auth.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(_redirect_target(request.args.get("next", "")))
        return render_template(
            "auth/login.html",
            active="login",
            next_url=request.args.get("next", ""),
        )

    cleanup_old_attempts()
    ip = _client_ip()
    next_url = request.form.get("next", "")
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if is_rate_limited(ip):
        return (
            render_template(
                "auth/login.html",
                active="login",
                error=translate("auth.login.errors.rate_limited"),
                next_url=next_url,
                form_data={"email": email},
            ),
            429,
        )

    user = verify_user(email, password)
    if user is None:
        record_login_attempt(ip)
        limited_now = is_rate_limited(ip)
        return (
            render_template(
                "auth/login.html",
                active="login",
                error=(
                    translate("auth.login.errors.rate_limited")
                    if limited_now
                    else translate("auth.login.errors.invalid_credentials")
                ),
                next_url=next_url,
                form_data={"email": email},
            ),
            429 if limited_now else 401,
        )

    _login_user(user)
    return redirect(_redirect_target(next_url))


@auth.route("/auth/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("public.index"))
        return render_template("auth/register.html", active="register")

    display_name = request.form.get("display_name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")
    form_data = {"display_name": display_name, "email": email}

    if not email or not password:
        return (
            render_template(
                "auth/register.html",
                active="register",
                error=translate("auth.register.errors.email_password_required"),
                form_data=form_data,
            ),
            400,
        )

    if password != password_confirm:
        return (
            render_template(
                "auth/register.html",
                active="register",
                error=translate("auth.register.errors.password_mismatch"),
                form_data=form_data,
            ),
            400,
        )

    if get_user_by_email(email):
        return (
            render_template(
                "auth/register.html",
                active="register",
                error=translate("auth.register.errors.email_exists"),
                form_data=form_data,
            ),
            400,
        )

    user_id = create_user(email, password, display_name)
    user = verify_user(email, password)
    if user is None:
        return (
            render_template(
                "auth/register.html",
                active="register",
                error=translate("auth.register.errors.create_failed"),
                form_data=form_data,
            ),
            500,
        )

    _login_user(user)
    return redirect(url_for("public.index"))


@auth.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("public.index"))
