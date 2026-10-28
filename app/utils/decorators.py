from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from app.extensions import db
from app.models import User


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if not user or not user.is_active:
            session.clear()
            return redirect(url_for("auth.login", next=request.full_path))
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


admin_required = role_required("Admin")
manager_required = role_required("Admin", "IT Manager")
it_manager_required = role_required("IT Manager")
