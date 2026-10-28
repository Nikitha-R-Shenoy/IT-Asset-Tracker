from datetime import datetime

from sqlalchemy import select

from app.extensions import db
from app.models import Allocation, Asset, Employee, Maintenance
from app.services.audit_service import record_audit
from app.services.lifecycle_engine import validate_transition


def checkout_asset(asset_id, employee_id, actor, notes=None):
    asset = db.session.execute(
        select(Asset).where(Asset.id == asset_id).with_for_update()
    ).scalar_one_or_none()
    employee = db.session.get(Employee, employee_id)
    if not asset:
        raise ValueError("Asset not found.")
    if not employee or not employee.is_active:
        raise ValueError("Select an active employee.")
    validate_transition(asset.status, "Assigned")
    if any(item.return_date is None for item in asset.allocations):
        raise ValueError("Asset already has an active allocation.")

    try:
        allocation = Allocation(
            asset=asset,
            employee=employee,
            assigned_by=actor,
            checkout_notes=notes,
        )
        asset.status = "Assigned"
        db.session.add(allocation)
        record_audit(
            "asset.checkout",
            "Asset",
            asset.id,
            {"asset_tag": asset.asset_tag, "employee": employee.employee_number},
            actor=actor,
        )
        db.session.commit()
        return allocation
    except Exception:
        db.session.rollback()
        raise


def return_asset(allocation_id, condition, actor, notes=None):
    if condition not in {"Good", "Damaged", "Defective"}:
        raise ValueError("Return condition must be Good, Damaged, or Defective.")
    allocation = db.session.execute(
        select(Allocation).where(Allocation.id == allocation_id).with_for_update()
    ).scalar_one_or_none()
    if not allocation or allocation.return_date is not None:
        raise ValueError("Active allocation not found.")
    asset = db.session.execute(
        select(Asset).where(Asset.id == allocation.asset_id).with_for_update()
    ).scalar_one()
    new_status = "Available" if condition == "Good" else "In_Repair"
    validate_transition(asset.status, new_status)

    try:
        allocation.return_date = datetime.utcnow()
        allocation.return_condition = condition
        allocation.return_notes = notes
        asset.status = new_status
        record_audit(
            "asset.return",
            "Asset",
            asset.id,
            {"allocation_id": allocation.id, "condition": condition, "status": new_status},
            actor=actor,
        )
        db.session.commit()
        return allocation
    except Exception:
        db.session.rollback()
        raise


def start_maintenance(asset_id, actor, issue_description, service_vendor=None, repair_cost=0):
    asset = db.session.execute(
        select(Asset).where(Asset.id == asset_id).with_for_update()
    ).scalar_one_or_none()
    if not asset:
        raise ValueError("Asset not found.")
    if any(item.return_date is None for item in asset.allocations):
        raise ValueError("Return the asset before starting maintenance.")
    validate_transition(asset.status, "Under_Maintenance")
    try:
        record = Maintenance(
            asset=asset,
            created_by=actor,
            issue_description=issue_description,
            service_vendor=service_vendor or None,
            repair_cost=repair_cost,
        )
        asset.status = "Under_Maintenance"
        db.session.add(record)
        record_audit(
            "maintenance.started",
            "Asset",
            asset.id,
            {"issue": issue_description},
            actor=actor,
        )
        db.session.commit()
        return record
    except Exception:
        db.session.rollback()
        raise


def complete_maintenance(record_id, actor, outcome="Available", notes=None):
    record = db.session.execute(
        select(Maintenance).where(Maintenance.id == record_id).with_for_update()
    ).scalar_one_or_none()
    if not record or record.completed_at is not None:
        raise ValueError("Open maintenance record not found.")
    if outcome not in {"Available", "In_Repair"}:
        raise ValueError("Maintenance outcome must be Available or In_Repair.")
    asset = db.session.execute(
        select(Asset).where(Asset.id == record.asset_id).with_for_update()
    ).scalar_one()
    validate_transition(asset.status, outcome)
    try:
        record.completed_at = datetime.utcnow()
        record.completion_notes = notes
        asset.status = outcome
        record_audit(
            "maintenance.completed",
            "Asset",
            asset.id,
            {"maintenance_id": record.id, "status": outcome},
            actor=actor,
        )
        db.session.commit()
        return record
    except Exception:
        db.session.rollback()
        raise
