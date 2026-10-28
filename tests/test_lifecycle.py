import pytest

from app.models import Allocation, Asset, AuditLog, Employee, User
from app.services.lifecycle import checkout_asset, return_asset
from app.services.lifecycle_engine import (
    InvalidStateTransitionError,
    validate_transition,
)


def test_checkout_and_inspected_return_are_atomic(app):
    with app.app_context():
        asset = Asset.query.filter_by(asset_tag="NSTAR-LP-0100").one()
        employee = Employee.query.filter_by(employee_number="EMP-001").one()
        manager = User.query.filter_by(role="IT Manager").one()
        allocation = checkout_asset(asset.id, employee.id, manager)
        assert asset.status == "Assigned"
        assert Allocation.query.filter_by(asset_id=asset.id, return_date=None).count() == 1
        assert AuditLog.query.filter_by(action="asset.checkout").count() == 1
        return_asset(allocation.id, "Damaged", manager, "Cracked hinge")
        assert allocation.return_condition == "Damaged"
        assert allocation.return_date is not None
        assert asset.status == "In_Repair"
        assert AuditLog.query.filter_by(action="asset.return").count() == 1


def test_checkout_rejects_repair_status(app):
    with app.app_context():
        asset = Asset.query.filter_by(asset_tag="NSTAR-LP-0100").one()
        asset.status = "In_Repair"
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(asset.status, "Assigned")


def test_retired_assets_cannot_transition(app):
    with app.app_context():
        with pytest.raises(InvalidStateTransitionError):
            validate_transition("Retired", "Assigned")
