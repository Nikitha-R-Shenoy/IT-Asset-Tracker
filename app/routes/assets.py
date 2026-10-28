import csv
import io
from flask import (
    Blueprint,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from app.extensions import db
from app.models import Allocation, Asset
from app.services.audit_service import record_audit
from app.services.depreciation import calculate_depreciation
from app.services.lifecycle_engine import validate_transition
from app.utils.decorators import it_manager_required, manager_required
from app.utils.validators import parse_asset_csv, parse_date, parse_money

bp = Blueprint("assets", __name__, url_prefix="/assets")


def _asset_values(form):
    purchase_cost = parse_money(form.get("purchase_cost"), "Purchase cost")
    salvage_value = parse_money(form.get("salvage_value", "0") or "0", "Salvage value")
    life = int(form.get("useful_life_years", "5"))
    if life < 1:
        raise ValueError("Useful life must be greater than zero.")
    if salvage_value > purchase_cost:
        raise ValueError("Salvage value cannot exceed purchase cost.")
    values = {
        "asset_tag": form.get("asset_tag", "").strip(),
        "serial_number": form.get("serial_number", "").strip(),
        "category": form.get("category", "").strip(),
        "manufacturer": form.get("manufacturer", "").strip(),
        "model": form.get("model", "").strip(),
        "vendor": form.get("vendor", "").strip() or None,
        "purchase_date": parse_date(form.get("purchase_date"), "Purchase date"),
        "purchase_cost": purchase_cost,
        "salvage_value": salvage_value,
        "useful_life_years": life,
        "warranty_expiry": parse_date(
            form.get("warranty_expiry"), "Warranty expiry", required=False
        ),
        "notes": form.get("notes", "").strip() or None,
    }
    required = ("asset_tag", "serial_number", "category", "manufacturer", "model")
    if not all(values[key] for key in required):
        raise ValueError(
            "Asset tag, serial number, category, manufacturer, and model are required."
        )
    return values


@bp.get("")
@manager_required
def index():
    page = request.args.get("page", 1, type=int)
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    inventory = Asset.query
    if query:
        pattern = f"%{query}%"
        inventory = inventory.filter(
            or_(
                Asset.asset_tag.ilike(pattern),
                Asset.serial_number.ilike(pattern),
                Asset.model.ilike(pattern),
                Asset.manufacturer.ilike(pattern),
                Asset.vendor.ilike(pattern),
            )
        )
    if status:
        inventory = inventory.filter(Asset.status == status)
    assets = (
        inventory.order_by(Asset.asset_tag)
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("assets/list.html", assets=assets, query=query, status=status)


@bp.route("/create", methods=["GET", "POST"])
@manager_required
def create():
    if request.method == "POST":
        try:
            values = _asset_values(request.form)
            duplicate = Asset.query.filter(
                or_(
                    Asset.asset_tag == values["asset_tag"],
                    Asset.serial_number == values["serial_number"],
                )
            ).first()
            if duplicate:
                raise ValueError("Tag or serial number already exists.")
            asset = Asset(**values)
            db.session.add(asset)
            db.session.flush()
            record_audit("asset.created", "Asset", asset.id, {"asset_tag": asset.asset_tag})
            db.session.commit()
            flash("Asset created successfully.", "success")
            return redirect(url_for("assets.detail", asset_id=asset.id))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error), "danger")
            return render_template("assets/form.html", asset=None), 400
        except IntegrityError:
            db.session.rollback()
            flash("Tag or serial number already exists.", "danger")
            return render_template("assets/form.html", asset=None), 400
        except Exception:
            db.session.rollback()
            raise
    return render_template("assets/form.html", asset=None)


@bp.post("/import")
@it_manager_required
def import_csv():
    upload = request.files.get("file")
    if not upload or not (upload.filename or "").lower().endswith(".csv"):
        flash("Choose a CSV file to import.", "danger")
        return redirect(url_for("assets.index"))
    try:
        rows, errors = parse_asset_csv(upload.stream)
        if errors:
            raise ValueError("; ".join(errors[:10]))
        tags = [row["asset_tag"] for row in rows]
        serials = [row["serial_number"] for row in rows]
        if len(tags) != len(set(tags)) or len(serials) != len(set(serials)):
            raise ValueError("CSV contains duplicate asset tags or serial numbers.")
        if rows and Asset.query.filter(
            or_(Asset.asset_tag.in_(tags), Asset.serial_number.in_(serials))
        ).first():
            raise ValueError("An asset tag or serial number already exists in inventory.")
        for values in rows:
            asset = Asset(**values)
            db.session.add(asset)
            db.session.flush()
            record_audit(
                "asset.created",
                "Asset",
                asset.id,
                {"asset_tag": asset.asset_tag, "source": "csv"},
            )
        db.session.commit()
        flash(f"Imported {len(rows)} asset(s).", "success")
    except ValueError as error:
        db.session.rollback()
        flash(f"Import rolled back: {error}", "danger")
    except IntegrityError:
        db.session.rollback()
        flash("Import rolled back: a tag or serial number already exists.", "danger")
    except Exception:
        db.session.rollback()
        raise
    return redirect(url_for("assets.index"))


@bp.get("/<int:asset_id>")
@manager_required
def detail(asset_id):
    asset = db.session.get(Asset, asset_id)
    if not asset:
        abort(404)
    book_value = calculate_depreciation(
        asset.purchase_cost,
        asset.salvage_value,
        asset.useful_life_years,
        asset.purchase_date,
    )
    history = (
        Allocation.query.filter_by(asset_id=asset.id)
        .order_by(Allocation.checkout_date.desc())
        .all()
    )
    return render_template(
        "assets/detail.html",
        asset=asset,
        book_value=book_value,
        history=history,
    )


@bp.route("/<int:asset_id>/edit", methods=["GET", "POST"])
@it_manager_required
def edit(asset_id):
    asset = db.session.get(Asset, asset_id)
    if not asset:
        abort(404)
    if asset.status == "Retired":
        flash("Retired assets cannot be edited.", "warning")
        return redirect(url_for("assets.detail", asset_id=asset.id))
    if request.method == "POST":
        try:
            values = _asset_values(request.form)
            conflict = Asset.query.filter(
                Asset.id != asset.id,
                or_(
                    Asset.asset_tag == values["asset_tag"],
                    Asset.serial_number == values["serial_number"],
                ),
            ).first()
            if conflict:
                raise ValueError("Tag or serial number already exists.")
            for key, value in values.items():
                setattr(asset, key, value)
            record_audit("asset.updated", "Asset", asset.id, {"asset_tag": asset.asset_tag})
            db.session.commit()
            flash("Asset updated.", "success")
            return redirect(url_for("assets.detail", asset_id=asset.id))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error), "danger")
            return render_template("assets/form.html", asset=asset), 400
        except IntegrityError:
            db.session.rollback()
            flash("Tag or serial number already exists.", "danger")
            return render_template("assets/form.html", asset=asset), 400
        except Exception:
            db.session.rollback()
            raise
    return render_template("assets/form.html", asset=asset)


@bp.post("/<int:asset_id>/retire")
@manager_required
def retire(asset_id):
    asset = db.session.get(Asset, asset_id)
    if not asset:
        record_audit("asset.delete_attempt", "Asset", asset_id, {"result": "not_found"})
        db.session.commit()
        abort(404)
    try:
        if any(allocation.return_date is None for allocation in asset.allocations):
            raise ValueError("Return the asset before retiring it.")
        validate_transition(asset.status, "Retired")
        asset.status = "Retired"
        record_audit(
            "asset.retired",
            "Asset",
            asset.id,
            {"asset_tag": asset.asset_tag, "delete_attempt": True},
        )
        db.session.commit()
        flash("Asset retired. Its history has been retained.", "success")
    except ValueError as error:
        db.session.rollback()
        record_audit("asset.delete_attempt", "Asset", asset.id, {"reason": str(error)})
        db.session.commit()
        flash(str(error), "danger")
    return redirect(url_for("assets.detail", asset_id=asset_id))


@bp.get("/<int:asset_id>/history.csv")
@manager_required
def history_csv(asset_id):
    asset = db.session.get(Asset, asset_id)
    if not asset:
        abort(404)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Employee", "Checkout", "Return", "Condition", "Checkout notes", "Return notes"]
    )
    for allocation in asset.allocations:
        writer.writerow(
            [
                allocation.employee.full_name,
                allocation.checkout_date.isoformat(),
                allocation.return_date.isoformat() if allocation.return_date else "",
                allocation.return_condition or "",
                allocation.checkout_notes or "",
                allocation.return_notes or "",
            ]
        )
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{asset.asset_tag}-history.csv"'
    )
    return response
