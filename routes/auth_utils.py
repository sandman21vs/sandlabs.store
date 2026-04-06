from functools import wraps

from flask import abort, redirect, request, session, url_for


def login_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.url))
        return func(*args, **kwargs)

    return decorated


def admin_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.url))
        if not session.get("is_admin"):
            abort(403)
        return func(*args, **kwargs)

    return decorated
