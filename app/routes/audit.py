from flask import Blueprint, render_template, request

from app.models import AuditLog
from app.utils.decorators import admin_required

bp = Blueprint("audit", __name__, url_prefix="/admin")


@bp.get("/audit-logs")
@admin_required
def index():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int),
        per_page=50,
        error_out=False,
    )
    return render_template("audit/list.html", logs=logs)
