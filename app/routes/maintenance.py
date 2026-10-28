from datetime import datetime
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Asset, Maintenance, ServiceRequest
from app.services.audit_service import record_audit
from app.services.lifecycle import complete_maintenance, start_maintenance
from app.utils.decorators import it_manager_required, login_required, manager_required
from app.utils.validators import parse_money

bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")


@bp.get("")
@manager_required
def index():
    records = Maintenance.query.order_by(Maintenance.started_at.desc()).all()
    return render_template("maintenance/list.html", records=records)


@bp.route("/start/<int:asset_id>", methods=["GET", "POST"])
@it_manager_required
def start(asset_id):
    asset = db.session.get(Asset, asset_id)
    if not asset:
        abort(404)
    if request.method == "POST":
        try:
            issue_description = request.form.get("issue_description", "").strip()
            if not issue_description:
                raise ValueError("Issue description is required.")
            cost = parse_money(
                request.form.get("repair_cost", "0") or "0",
                "Repair cost",
            )
            start_maintenance(
                asset.id,
                g.current_user,
                issue_description,
                request.form.get("service_vendor", "").strip(),
                cost,
            )
            flash("Maintenance started.", "success")
            return redirect(url_for("maintenance.index"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
    return render_template("maintenance/start.html", asset=asset)


@bp.post("/<int:record_id>/complete")
@it_manager_required
def complete(record_id):
    try:
        complete_maintenance(
            record_id,
            g.current_user,
            request.form.get("outcome", "Available"),
            request.form.get("notes", "").strip() or None,
        )
        flash("Maintenance completed.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "danger")
    return redirect(url_for("maintenance.index"))


@bp.route("/requests", methods=["GET", "POST"])
@login_required
def requests_index():
    employee = g.current_user.employee
    if g.current_user.role == "Employee":
        if not employee:
            abort(403)
        if request.method == "POST":
            asset_id = request.form.get("asset_id", type=int)
            description = request.form.get("description", "").strip()
            owns_asset = any(
                item.asset_id == asset_id and item.return_date is None
                for item in employee.allocations
            )
            if not owns_asset or not description:
                flash("Choose one of your assigned assets and describe the issue.", "danger")
            else:
                service_request = ServiceRequest(
                    asset_id=asset_id, employee_id=employee.id, description=description
                )
                db.session.add(service_request)
                db.session.flush()
                record_audit(
                    "service_request.created",
                    "ServiceRequest",
                    service_request.id,
                    {"asset_id": asset_id},
                )
                db.session.commit()
                flash("Repair request submitted.", "success")
                return redirect(url_for("maintenance.requests_index"))
        requests = (
            ServiceRequest.query.filter_by(employee_id=employee.id)
            .order_by(ServiceRequest.created_at.desc())
            .all()
        )
        assigned_assets = [item.asset for item in employee.allocations if item.return_date is None]
        return render_template(
            "maintenance/requests.html", requests=requests, assigned_assets=assigned_assets
        )
    requests = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all()
    return render_template("maintenance/requests.html", requests=requests, assigned_assets=[])


@bp.post("/requests/<int:request_id>/update")
@it_manager_required
def update_request(request_id):
    service_request = db.session.get(ServiceRequest, request_id)
    if not service_request:
        abort(404)
    status = request.form.get("status", "")
    if service_request.status not in {"Open", "In Progress"}:
        flash("This service request is already closed.", "warning")
        return redirect(url_for("maintenance.requests_index"))
    if status not in {"In Progress", "Resolved", "Rejected"}:
        abort(400)
    service_request.status = status
    service_request.resolution_notes = request.form.get("resolution_notes", "").strip() or None
    service_request.resolved_at = datetime.utcnow() if status in {"Resolved", "Rejected"} else None
    record_audit(
        "service_request.updated",
        "ServiceRequest",
        service_request.id,
        {"status": status},
    )
    db.session.commit()
    flash("Repair request updated.", "success")
    return redirect(url_for("maintenance.requests_index"))
