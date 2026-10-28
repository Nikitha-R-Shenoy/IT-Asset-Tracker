from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.models import Asset, Employee, User


@pytest.fixture()
def app():
    application = create_app("config.TestConfig")
    with application.app_context():
        db.create_all()
        admin = User(email="admin@example.test", role="Admin")
        admin.set_password("Admin-Test-Password-123!")
        manager = User(email="manager@example.test", role="IT Manager")
        manager.set_password("Manager-Test-Password-123!")
        employee = Employee(
            employee_number="EMP-001",
            first_name="Asha",
            last_name="Rao",
            email="asha@example.test",
            department="Engineering",
            cost_center="ENG-100",
        )
        db.session.add_all([admin, manager, employee])
        db.session.flush()
        portal_user = User(
            email=employee.email, role="Employee", employee_id=employee.id
        )
        portal_user.set_password("Employee-Test-Password-123!")
        asset = Asset(
            asset_tag="NSTAR-LP-0100",
            serial_number="SN-TEST-100",
            category="Laptop",
            manufacturer="Northstar",
            model="ProBook",
            purchase_date=date(2023, 1, 1),
            purchase_cost=50000,
            salvage_value=5000,
            useful_life_years=5,
            status="Available",
        )
        db.session.add_all([portal_user, asset])
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def manager_id(app):
    with app.app_context():
        return User.query.filter_by(role="IT Manager").first().id


@pytest.fixture()
def asset_id(app):
    with app.app_context():
        return Asset.query.filter_by(asset_tag="NSTAR-LP-0100").first().id


def login(client, email="manager@example.test", password="Manager-Test-Password-123!"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
