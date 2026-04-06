from flask import Blueprint, abort, render_template, session

from models.model_orders import get_order, get_orders_by_user
from routes.auth_utils import login_required


account = Blueprint("account", __name__)


@account.route("/account/orders")
@login_required
def orders():
    user_orders = get_orders_by_user(session["user_id"])
    return render_template(
        "account/orders.html",
        active="orders",
        orders=user_orders,
    )


@account.route("/account/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = get_order(order_id)
    if order is None:
        abort(404)

    if not session.get("is_admin") and order.get("user_id") != session.get("user_id"):
        abort(403)

    return render_template(
        "account/order_detail.html",
        active="orders",
        order=order,
    )
