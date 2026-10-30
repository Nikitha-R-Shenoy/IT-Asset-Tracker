from datetime import date, timedelta

from flask import Blueprint, g, render_template

from app.models import Allocation, Asset, ServiceRequest
from app.utils.decorators import login_required

bp = Blueprint("dashboard", __name__)


@bp.get("/")
@bp.get("/dashboard")
@login_required
def index():
    if g.current_user.role == "Employee":
        employee = g.current_user.employee
        allocations = (
            Allocation.query.filter_by(employee_id=employee.id, return_date=None)
            .order_by(Allocation.checkout_date.desc())
            .all()
            if employee
            else []
        )
        requests = (
            ServiceRequest.query.filter_by(employee_id=employee.id)
            .order_by(ServiceRequest.created_at.desc())
            .limit(10)
            .all()
            if employee
            else []
        )
        return render_template(
            "dashboard/employee.html",
            allocations=allocations,
            requests=requests,
        )

    counts = {
        "total": Asset.query.count(),
        "available": Asset.query.filter_by(status="Available").count(),
        "assigned": Asset.query.filter_by(status="Assigned").count(),
        "maintenance": Asset.query.filter(
            Asset.status.in_(("In_Repair", "Under_Maintenance"))
        ).count(),
        "retired": Asset.query.filter_by(status="Retired").count(),
    }
    recent_assets = Asset.query.order_by(Asset.created_at.desc()).limit(6).all()
    open_requests = ServiceRequest.query.filter(
        ServiceRequest.status.in_(("Open", "In Progress"))
    ).count()
    expiring = Asset.query.filter(
        Asset.warranty_expiry.between(date.today(), date.today() + timedelta(days=30)),
        Asset.status != "Retired",
    ).count()
    return render_template(
        "dashboard/index.html",
        counts=counts,
        assets=recent_assets,
        open_requests=open_requests,
        expiring=expiring,
    )
