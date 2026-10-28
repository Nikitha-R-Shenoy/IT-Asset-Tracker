import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, Response, render_template, request, stream_with_context
from sqlalchemy import or_

from app.extensions import db
from app.models import Asset, Maintenance
from app.utils.decorators import manager_required

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _report_source(report_type):
    if report_type == "warranty":
        end = date.today() + timedelta(days=30)
        query = Asset.query.filter(
            Asset.warranty_expiry.between(date.today(), end), Asset.status != "Retired"
        ).order_by(Asset.warranty_expiry)
        return ["Asset Tag", "Model", "Warranty Expiry", "Status"], query
    if report_type == "repairs":
        query = (
            db.session.query(
                Asset.asset_tag,
                db.func.count(Maintenance.id),
                db.func.coalesce(db.func.sum(Maintenance.repair_cost), 0),
            )
            .join(Maintenance, Maintenance.asset_id == Asset.id)
            .group_by(Asset.id, Asset.asset_tag)
            .order_by(Asset.asset_tag)
        )
        return ["Asset Tag", "Repair Count", "Total Repair Cost"], query
    inventory = Asset.query
    status = request.args.get("status", "").strip()
    query = request.args.get("q", "").strip()
    if status:
        inventory = inventory.filter(Asset.status == status)
    if query:
        pattern = f"%{query}%"
        inventory = inventory.filter(
            or_(
                Asset.asset_tag.ilike(pattern),
                Asset.serial_number.ilike(pattern),
                Asset.model.ilike(pattern),
                Asset.vendor.ilike(pattern),
            )
        )
    return [
        "Asset Tag",
        "Serial Number",
        "Category",
        "Model",
        "Status",
        "Vendor",
    ], inventory.order_by(Asset.asset_tag)


def _formatted_rows(report_type, query):
    if report_type == "warranty":
        for asset in query.yield_per(500):
            yield [
                asset.asset_tag,
                asset.model,
                asset.warranty_expiry.isoformat(),
                asset.status,
            ]
    elif report_type == "repairs":
        for tag, count, cost in query.yield_per(500):
            yield [tag, count, f"{Decimal(cost):.2f}"]
    else:
        for asset in query.yield_per(500):
            yield [
                asset.asset_tag,
                asset.serial_number,
                asset.category,
                asset.model,
                asset.status,
                asset.vendor or "",
            ]


def _report_rows(report_type):
    headers, query = _report_source(report_type)
    return headers, list(_formatted_rows(report_type, query))


@bp.get("")
@manager_required
def index():
    report_type = request.args.get("type", "inventory")
    if report_type not in {"inventory", "warranty", "repairs"}:
        report_type = "inventory"
    headers, rows = _report_rows(report_type)
    return render_template(
        "reports/index.html", report_type=report_type, headers=headers, rows=rows
    )


@bp.get("/export.csv")
@manager_required
def export():
    report_type = request.args.get("type", "inventory")
    if report_type not in {"inventory", "warranty", "repairs"}:
        report_type = "inventory"
    headers, query = _report_source(report_type)

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        yield output.getvalue()
        for row in _formatted_rows(report_type, query):
            output.seek(0)
            output.truncate(0)
            writer.writerow(row)
            yield output.getvalue()

    return Response(
        stream_with_context(generate_csv()),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="itams-{report_type}-report.csv"'
        },
    )
