"""Admin panel routes for sandlabs.store.

All routes require an authenticated admin user (is_admin=1).
Use /admin/setup to create the first admin account.
"""
import json
import logging
import os
import secrets

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.utils import secure_filename

import db
from i18n import t as translate
from models.model_config import admin_exists, get_all_config, get_config, set_config
from models.model_users import create_user, get_user_by_email
from models.model_products import (create_product, delete_product,
                                    get_product_by_id, update_product)
from models.model_products import _PRODUCT_SELECT, _row_to_product, _load_related_records
from models.model_orders import (
    get_order as get_order_record,
    set_order_tracking,
    update_order_status,
)
from routes.auth_utils import admin_required
from services.service_images import ensure_thumbnail, get_images_base_dir

logger = logging.getLogger(__name__)
admin = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

_DEFAULT_SHIPPING_RATES = json.dumps({
    "CH":    {"2": 7.0, "10": 9.5, "30": 16.0},
    "EU":    {"2": 20.0, "5": 30.0, "10": 45.0, "30": 80.0},
    "WORLD": {"2": 30.0, "5": 50.0, "10": 75.0, "30": 120.0},
}, indent=2, ensure_ascii=False)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_all_products_admin():
    """All products including inactive."""
    conn = db.get_db()
    try:
        rows = conn.execute(
            f"{_PRODUCT_SELECT} ORDER BY sort_order, id"
        ).fetchall()
        products = [_row_to_product(row) for row in rows]
        return _load_related_records(conn, products)
    finally:
        conn.close()


def _get_order_stats():
    conn = db.get_db()
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS cnt, COALESCE(SUM(total_sats),0) AS sats "
            "FROM orders GROUP BY status"
        ).fetchall()
    finally:
        conn.close()

    by_status = {r["status"]: {"count": r["cnt"], "sats": r["sats"]} for r in rows}
    total_revenue = sum(
        v["sats"] for s, v in by_status.items()
        if s in ("paid", "processing", "shipped", "delivered")
    )
    pending_ship = sum(
        v["count"] for s, v in by_status.items()
        if s in ("paid", "processing")
    )
    total_orders = sum(v["count"] for v in by_status.values())
    return {
        "by_status": by_status,
        "total_revenue_sats": total_revenue,
        "pending_shipments": pending_ship,
        "total_orders": total_orders,
    }


def _get_recent_orders(limit=10):
    conn = db.get_db()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
    finally:
        conn.close()


def _get_all_orders(status_filter=None):
    conn = db.get_db()
    try:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM orders WHERE status=? ORDER BY id DESC", (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _get_order_with_items(order_id):
    conn = db.get_db()
    try:
        order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            return None, []
        items = conn.execute(
            """SELECT oi.*, p.name AS product_name
               FROM order_items oi
               LEFT JOIN products p ON p.id = oi.product_id
               WHERE oi.order_id = ?""",
            (order_id,),
        ).fetchall()
        return dict(order), [dict(i) for i in items]
    finally:
        conn.close()


def _parse_product_form(form):
    """Parse multipart form data into product dict."""
    prices = []
    try:
        prices = json.loads(form.get("prices_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        pass

    options = []
    try:
        options = json.loads(form.get("options_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "name": form.get("name", "").strip(),
        "summary": form.get("summary", "").strip(),
        "details_html": form.get("details_html", "").strip(),
        "weight_grams": int(form.get("weight_grams") or 200),
        "buy_button_text": form.get("buy_button_text", "Comprar").strip(),
        "allow_addon_seed": bool(form.get("allow_addon_seed")),
        "badge_text": form.get("badge_text", "").strip() or None,
        "badge_variant": form.get("badge_variant", "").strip() or None,
        "sort_order": int(form.get("sort_order") or 0),
        "active": "active" in form,
        "prices": prices,
        "options": options,
    }


def _save_uploaded_images(files, existing_images=None):
    images = list(existing_images or [])
    upload_dir = get_images_base_dir(current_app)
    os.makedirs(upload_dir, exist_ok=True)
    for file in files:
        if not file or not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            continue
        filename = secure_filename(file.filename)
        file.save(os.path.join(upload_dir, filename))
        ensure_thumbnail(upload_dir, f"images/{filename}")
        images.append({"filename": f"images/{filename}", "sort_order": len(images)})
    return images


def _ensure_local_thumbnails(images):
    upload_dir = get_images_base_dir(current_app)
    for image in images or []:
        filename = image.get("filename") if isinstance(image, dict) else image
        if not filename or not str(filename).startswith("images/"):
            continue
        ensure_thumbnail(upload_dir, filename)


# ── Routes ────────────────────────────────────────────────────────────────────

@admin.before_request
def enforce_initial_setup():
    if request.endpoint == "admin.setup":
        if admin_exists():
            if session.get("is_admin"):
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("auth.login", next=url_for("admin.dashboard")))
        return None

    if not admin_exists():
        return redirect(url_for("admin.setup"))

@admin.route("/setup", methods=["GET", "POST"])
def setup():
    """First-run wizard for the initial admin account and Coinos bootstrap."""
    default_email = f"{os.environ.get('ADMIN_USERNAME', 'admin')}@admin.local"
    form_data = {
        "name": "Admin",
        "email": default_email,
        "coinos_enabled": "0",
    }
    errors = []
    if request.method == "POST":
        name = request.form.get("name", "Admin").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        coinos_api_key = request.form.get("coinos_api_key", "").strip()
        coinos_webhook_secret = request.form.get("coinos_webhook_secret", "").strip()
        coinos_enabled = bool(request.form.get("coinos_enabled"))

        form_data.update({
            "name": name or "Admin",
            "email": email,
            "coinos_enabled": "1" if coinos_enabled else "0",
        })

        if not email or not password:
            errors.append(translate("admin.setup.errors.email_password_required"))
        elif password != confirm:
            errors.append(translate("admin.setup.errors.password_mismatch"))
        elif len(password) < 8:
            errors.append(translate("admin.setup.errors.password_min_length"))

        if coinos_enabled and not coinos_api_key:
            errors.append(translate("admin.setup.errors.coinos_api_key_required"))

        if errors:
            return render_template("admin/setup.html", errors=errors, form_data=form_data), 200

        if coinos_enabled and not coinos_webhook_secret:
            coinos_webhook_secret = secrets.token_urlsafe(24)

        try:
            create_user(email, password, name or "Admin", is_admin=True)
        except ValueError as exc:
            errors.append(str(exc))
            return render_template("admin/setup.html", errors=errors, form_data=form_data), 200

        if coinos_api_key:
            set_config("coinos_api_key", coinos_api_key)
        if coinos_webhook_secret:
            set_config("coinos_webhook_secret", coinos_webhook_secret)
        set_config("coinos_enabled", "1" if coinos_enabled else "0")
        set_config("setup_complete", "1")

        user = get_user_by_email(email)
        session["user_id"] = user["id"]
        session["is_admin"] = True
        session["display_name"] = user.get("display_name", "")
        logger.info("admin_setup_completed admin_user_id=%s email=%s", user["id"], email)
        flash(translate("admin.setup.flash.completed"), "success")
        if coinos_enabled and request.form.get("coinos_webhook_secret", "").strip() == "":
            flash(translate("admin.setup.flash.webhook_generated"), "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/setup.html", errors=errors, form_data=form_data)


@admin.route("/")
@admin_required
def dashboard():
    stats = _get_order_stats()
    recent = _get_recent_orders(10)
    product_count = len(_get_all_products_admin())
    return render_template("admin/dashboard.html",
                           stats=stats,
                           recent_orders=recent,
                           product_count=product_count)


@admin.route("/products")
@admin_required
def products():
    prods = _get_all_products_admin()
    return render_template("admin/products.html", products=prods)


@admin.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    error = None
    if request.method == "POST":
        product_id = request.form.get("id", "").strip()
        if not product_id:
            error = translate("admin.products.errors.id_required")
        else:
            data = _parse_product_form(request.form)
            data["id"] = product_id
            data["images"] = _save_uploaded_images(request.files.getlist("product_images"))
            # Also accept newline-separated image paths in textarea
            for line in request.form.get("image_paths", "").splitlines():
                p = line.strip()
                if p:
                    data["images"].append({"filename": p, "sort_order": len(data["images"])})
            _ensure_local_thumbnails(data["images"])
            try:
                create_product(data)
                logger.info("admin_product_created product_id=%s admin_user_id=%s", product_id, session.get("user_id"))
                flash(translate("admin.products.flash.created"), "success")
                return redirect(url_for("admin.products"))
            except Exception as exc:
                logger.exception("admin_product_create_failed product_id=%s", product_id)
                error = str(exc)

    return render_template("admin/product_form.html", product=None, error=error, action="new")


@admin.route("/products/<product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = get_product_by_id(product_id)
    if not product:
        flash(translate("admin.products.flash.not_found"), "error")
        return redirect(url_for("admin.products"))

    error = None
    if request.method == "POST":
        data = _parse_product_form(request.form)

        # Keep existing images unless explicitly cleared
        try:
            existing = json.loads(request.form.get("existing_images_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            existing = []

        data["images"] = _save_uploaded_images(
            request.files.getlist("product_images"), existing
        )
        for line in request.form.get("image_paths", "").splitlines():
            p = line.strip()
            if p:
                data["images"].append({"filename": p, "sort_order": len(data["images"])})
        _ensure_local_thumbnails(data["images"])

        try:
            update_product(product_id, data)
            logger.info("admin_product_updated product_id=%s admin_user_id=%s", product_id, session.get("user_id"))
            flash(translate("admin.products.flash.updated"), "success")
            return redirect(url_for("admin.products"))
        except Exception as exc:
            logger.exception("admin_product_update_failed product_id=%s", product_id)
            error = str(exc)

    return render_template("admin/product_form.html",
                           product=product, error=error, action="edit")


@admin.route("/products/<product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    if delete_product(product_id):
        logger.info("admin_product_deleted product_id=%s admin_user_id=%s", product_id, session.get("user_id"))
        flash(translate("admin.products.flash.deleted"), "success")
    else:
        logger.warning("admin_product_delete_not_found product_id=%s", product_id)
        flash(translate("admin.products.flash.not_found"), "error")
    return redirect(url_for("admin.products"))


VALID_STATUSES = {"pending", "paid", "processing", "shipped", "delivered", "cancelled"}


@admin.route("/orders")
@admin_required
def orders():
    status_filter = request.args.get("status", "")
    order_list = _get_all_orders(status_filter or None)
    return render_template("admin/orders.html",
                           orders=order_list,
                           status_filter=status_filter,
                           valid_statuses=sorted(VALID_STATUSES))


@admin.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = get_order_record(order_id)
    if not order:
        flash(translate("admin.orders.flash.not_found"), "error")
        return redirect(url_for("admin.orders"))
    items = order.get("items", [])
    return render_template("admin/order_detail.html",
                           order=order,
                           items=items,
                           valid_statuses=sorted(VALID_STATUSES))


@admin.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_status(order_id):
    new_status = request.form.get("status", "").strip()
    tracking = request.form.get("tracking", "").strip()

    if new_status not in VALID_STATUSES:
        flash(translate("admin.orders.flash.invalid_status"), "error")
        return redirect(url_for("admin.order_detail", order_id=order_id))

    update_order_status(order_id, new_status)
    if tracking:
        set_order_tracking(order_id, tracking)
    logger.info(
        "admin_order_status_updated order_id=%s status=%s tracking=%s admin_user_id=%s",
        order_id,
        new_status,
        tracking or "",
        session.get("user_id"),
    )

    flash(translate("admin.orders.flash.status_updated", status=new_status), "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    current_cfg = get_all_config()
    if request.method == "POST":
        for key in ("whatsapp", "telegram"):
            val = request.form.get(key, "").strip()
            if val:
                set_config(key, val)

        coinos_api_key_input = request.form.get("coinos_api_key", "").strip()
        coinos_webhook_secret_input = request.form.get("coinos_webhook_secret", "").strip()
        coinos_enabled_requested = bool(request.form.get("coinos_enabled"))

        effective_api_key = coinos_api_key_input or current_cfg.get("coinos_api_key", "")
        effective_webhook_secret = (
            coinos_webhook_secret_input
            or current_cfg.get("coinos_webhook_secret", "")
        )

        if coinos_api_key_input:
            set_config("coinos_api_key", coinos_api_key_input)
        if coinos_webhook_secret_input:
            set_config("coinos_webhook_secret", coinos_webhook_secret_input)
        elif coinos_enabled_requested and not effective_webhook_secret:
            effective_webhook_secret = secrets.token_urlsafe(24)
            set_config("coinos_webhook_secret", effective_webhook_secret)
            flash(translate("admin.settings.flash.webhook_generated"), "success")

        if coinos_enabled_requested and not effective_api_key:
            set_config("coinos_enabled", "0")
            logger.warning("admin_settings_missing_coinos_api_key admin_user_id=%s", session.get("user_id"))
            flash(translate("admin.settings.errors.coinos_api_key_required"), "error")
        else:
            set_config("coinos_enabled", "1" if coinos_enabled_requested else "0")

        shipping_json = request.form.get("shipping_rates", "").strip()
        settings_saved = False
        try:
            json.loads(shipping_json)
            set_config("shipping_rates", shipping_json)
            settings_saved = True
        except json.JSONDecodeError:
            logger.warning("admin_settings_invalid_shipping_json admin_user_id=%s", session.get("user_id"))
            flash(translate("admin.settings.errors.invalid_shipping_json"), "error")

        logger.info(
            "admin_settings_updated admin_user_id=%s coinos_enabled=%s",
            session.get("user_id"),
            "1" if coinos_enabled_requested and effective_api_key else "0",
        )
        if settings_saved:
            flash(translate("admin.settings.flash.saved"), "success")
        return redirect(url_for("admin.settings"))

    cfg = current_cfg
    cfg["shipping_rates"] = get_config("shipping_rates", _DEFAULT_SHIPPING_RATES)
    return render_template("admin/settings.html", cfg=cfg)
