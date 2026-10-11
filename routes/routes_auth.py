import hmac
import logging
from urllib.parse import urlsplit

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

import config

from i18n import translate
from models.model_cart import merge_cart
from models.model_users import (
    cleanup_old_attempts,
    create_google_user,
    create_user,
    get_user_by_email,
    get_user_by_google_sub,
    get_user_by_id,
    is_rate_limited,
    link_google_account,
    record_login_attempt,
    verify_user,
)
from services import service_google_auth

logger = logging.getLogger(__name__)

auth = Blueprint("auth", __name__)

_GOOGLE_SESSION_KEY = "google_oauth"


@auth.context_processor
def inject_google_login():
    return {"google_login_enabled": service_google_auth.is_enabled()}


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


def google_redirect_uri():
    """Callback URL registered with Google.

    Uses ``PUBLIC_BASE_URL`` when set, because behind a proxy or tunnel the
    request host and scheme may not be the public ones Google must match.
    """
    path = url_for("auth.google_callback")
    if config.PUBLIC_BASE_URL:
        return f"{config.PUBLIC_BASE_URL}{path}"
    return url_for("auth.google_callback", _external=True)


def _google_login_failed(message_key, status=400):
    return (
        render_template("auth/login.html", active="login", error=translate(message_key)),
        status,
    )


@auth.route("/auth/google")
def google_start():
    if not service_google_auth.is_enabled():
        abort(404)
    attempt = service_google_auth.new_login_attempt()
    session[_GOOGLE_SESSION_KEY] = {**attempt, "next": request.args.get("next", "")}
    return redirect(service_google_auth.authorization_url(google_redirect_uri(), attempt))


@auth.route("/auth/google/callback")
def google_callback():
    if not service_google_auth.is_enabled():
        abort(404)

    # One attempt per round trip: the stored secrets are consumed here.
    attempt = session.pop(_GOOGLE_SESSION_KEY, None)
    state = request.args.get("state", "")
    if not attempt or not state or not hmac.compare_digest(str(attempt.get("state", "")), state):
        return _google_login_failed("auth.google.errors.failed")
    if request.args.get("error"):
        # The visitor cancelled or Google refused; nothing to exchange.
        return _google_login_failed("auth.google.errors.failed")

    identity = service_google_auth.exchange_code(
        request.args.get("code", ""), google_redirect_uri(), attempt
    )
    if identity is None:
        return _google_login_failed("auth.google.errors.failed")

    user = get_user_by_google_sub(identity["sub"])
    if user is None:
        existing = get_user_by_email(identity["email"])
        if existing is None:
            user_id = create_google_user(identity["email"], identity["sub"], identity["name"])
        elif existing["is_admin"]:
            # Admin access must not hinge on a third-party account.
            logger.warning("google_login_refused_admin user_id=%s", existing["id"])
            return _google_login_failed("auth.google.errors.admin_password", 403)
        else:
            # Google vouches for the email, so this is its owner. The old
            # password is dropped: it may have been set by someone else.
            if not link_google_account(existing["id"], identity["sub"], replace_password=True):
                return _google_login_failed("auth.google.errors.failed")
            user_id = existing["id"]
        user = get_user_by_id(user_id)
    elif user["is_admin"]:
        logger.warning("google_login_refused_admin user_id=%s", user["id"])
        return _google_login_failed("auth.google.errors.admin_password", 403)

    logger.info("google_login user_id=%s", user["id"])
    _login_user(user)
    return redirect(_redirect_target(attempt.get("next", "")))


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
