from urllib.parse import urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next_url(target):
    if not target:
        return False
    ref = urlparse(urljoin(request.host_url, target))
    return ref.scheme in {"http", "https"} and ref.netloc == request.host


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.execute(
            db.select(User).where(db.func.lower(User.email) == email)
        ).scalar_one_or_none()
        if user and user.is_active and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            session.permanent = True
            target = request.args.get("next") or request.form.get("next")
            return redirect(target if _safe_next_url(target) else url_for("dashboard.index"))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")


@bp.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
