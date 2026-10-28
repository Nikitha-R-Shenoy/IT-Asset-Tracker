from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Allocation, Asset, Employee
from app.services.lifecycle import checkout_asset, return_asset
from app.utils.decorators import it_manager_required, manager_required

bp = Blueprint("allocations", __name__)


@bp.get("/allocations")
@manager_required
def index():
    active = (
        Allocation.query.filter_by(return_date=None)
        .order_by(Allocation.checkout_date.desc())
        .all()
    )
    return render_template("allocations/list.html", allocations=active)


@bp.route("/allocations/assign", methods=["GET", "POST"])
@bp.route("/assets/assign", methods=["POST"])
@it_manager_required
def assign():
    if request.method == "POST":
        try:
            allocation = checkout_asset(
                int(request.form.get("asset_id", "")),
                int(request.form.get("employee_id", "")),
                g.current_user,
                request.form.get("notes", "").strip() or None,
            )
            flash("Asset assigned successfully.", "success")
            return redirect(url_for("assets.detail", asset_id=allocation.asset_id))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error), "danger")
    assets = Asset.query.filter_by(status="Available").order_by(Asset.asset_tag).all()
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.last_name).all()
    return render_template("allocations/checkout.html", assets=assets, employees=employees)


@bp.route("/allocations/<int:allocation_id>/return", methods=["GET", "POST"])
@bp.route("/assets/allocation/<int:allocation_id>/return", methods=["POST"])
@it_manager_required
def return_item(allocation_id):
    allocation = db.session.get(Allocation, allocation_id)
    if not allocation or allocation.return_date is not None:
        flash("Active allocation not found.", "danger")
        return redirect(url_for("allocations.index"))
    if request.method == "POST":
        try:
            return_asset(
                allocation.id,
                request.form.get("condition", ""),
                g.current_user,
                request.form.get("notes", "").strip() or None,
            )
            flash("Asset return recorded.", "success")
            return redirect(url_for("assets.detail", asset_id=allocation.asset_id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
    return render_template("allocations/checkin.html", allocation=allocation)
