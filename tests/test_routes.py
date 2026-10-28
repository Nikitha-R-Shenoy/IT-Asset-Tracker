import io
from datetime import date

import pytest

from app.extensions import db
from app.models import Allocation, Asset, AuditLog, Employee, Maintenance, ServiceRequest
from app import create_app
from tests.conftest import login


def test_login_redirects_to_dashboard_and_establishes_session(client):
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    with client.session_transaction() as session:
        assert session.get("user_id") is not None


def test_bad_password_does_not_authenticate(client):
    response = client.post(
        "/auth/login", data={"email": "manager@example.test", "password": "wrong"}
    )
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_employee_cannot_open_admin_audit_endpoint(client):
    login(client, "asha@example.test", "Employee-Test-Password-123!")
    response = client.get("/admin/audit-logs")
    assert response.status_code == 403


def test_admin_can_inspect_audit_endpoint(client):
    login(client, "admin@example.test", "Admin-Test-Password-123!")
    assert client.get("/admin/audit-logs").status_code == 200


def test_duplicate_asset_tag_is_rejected(client):
    login(client)
    response = client.post(
        "/assets/create",
        data={
            "asset_tag": "NSTAR-LP-0100",
            "serial_number": "ANOTHER-SERIAL",
            "category": "Laptop",
            "manufacturer": "Northstar",
            "model": "ProBook",
            "purchase_date": "2024-01-01",
            "purchase_cost": "50000",
            "salvage_value": "5000",
            "useful_life_years": "5",
        },
    )
    assert response.status_code == 400
    assert b"Tag or serial number already exists" in response.data


def test_asset_assignment_adds_allocation_and_audit(client, app):
    login(client)
    with app.app_context():
        asset_id = Asset.query.filter_by(asset_tag="NSTAR-LP-0100").one().id
        employee_id = Employee.query.filter_by(employee_number="EMP-001").one().id
    response = client.post(
        "/assets/assign", data={"asset_id": asset_id, "employee_id": employee_id}
    )
    assert response.status_code == 302
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.status == "Assigned"
        assert Allocation.query.filter_by(asset_id=asset_id, return_date=None).count() == 1
        assert AuditLog.query.filter_by(action="asset.checkout").count() == 1


def test_admin_cannot_perform_it_manager_only_assignment(client):
    login(client, "admin@example.test", "Admin-Test-Password-123!")
    response = client.post("/assets/assign", data={"asset_id": 1, "employee_id": 1})
    assert response.status_code == 403


def test_manager_dashboard_and_inventory_pages_render(client):
    login(client)
    assert client.get("/dashboard").status_code == 200
    assert client.get("/assets").status_code == 200
    assert client.get("/assets/1").status_code == 200
    assert client.get("/employees").status_code == 200
    assert client.get("/reports?type=inventory").status_code == 200


@pytest.mark.parametrize(
    ("email", "password", "asset_tag", "can_assign"),
    [
        ("admin@example.test", "Admin-Test-Password-123!", "NSTAR-ADMIN-0001", False),
        ("manager@example.test", "Manager-Test-Password-123!", "NSTAR-MANAGER-0001", True),
    ],
)
def test_admin_and_manager_can_register_assets(
    client, app, email, password, asset_tag, can_assign
):
    login(client, email, password)

    inventory = client.get("/assets")
    assert inventory.status_code == 200
    assert b'href="/assets/create"' in inventory.data
    assert b"Register asset" in inventory.data
    assert (b"Assign asset" in inventory.data) is can_assign

    dashboard = client.get("/dashboard")
    assert b'href="/assets/create"' in dashboard.data

    assert client.get("/assets/create").status_code == 200
    response = client.post(
        "/assets/create",
        data={
            "asset_tag": asset_tag,
            "serial_number": f"SN-{asset_tag}",
            "category": "Laptop",
            "manufacturer": "Northstar",
            "model": "ProBook",
            "purchase_date": "2024-01-01",
            "purchase_cost": "50000",
            "salvage_value": "5000",
            "useful_life_years": "5",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        assert Asset.query.filter_by(asset_tag=asset_tag).one()


def test_employee_cannot_open_asset_creation_endpoint(client):
    login(client, "asha@example.test", "Employee-Test-Password-123!")
    assert client.get("/assets/create").status_code == 403


def test_report_csv_export_preserves_filters(client):
    login(client)
    response = client.get("/reports/export.csv?type=inventory&status=Available")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"NSTAR-LP-0100" in response.data
    assert "attachment;" in response.headers["Content-Disposition"]


def test_employee_portal_pages_render(client):
    login(client, "asha@example.test", "Employee-Test-Password-123!")
    assert client.get("/dashboard").status_code == 200
    assert client.get("/maintenance/requests").status_code == 200


def test_invalid_csv_import_rolls_back_all_rows(client, app):
    login(client)
    payload = (
        "asset_tag,serial_number,category,manufacturer,model,purchase_date,"
        "purchase_cost,salvage_value,useful_life_years\n"
        "NSTAR-LP-0101,SN-101,Laptop,Northstar,ModelX,2024-01-01,1000,100,5\n"
        "NSTAR-LP-0102,SN-102,Laptop,Northstar,ModelY,invalid,1000,100,5\n"
    )
    response = client.post(
        "/assets/import",
        data={"file": (io.BytesIO(payload.encode("utf-8")), "assets.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Import rolled back" in response.data
    with app.app_context():
        assert Asset.query.filter(Asset.asset_tag.like("NSTAR-LP-010%")).count() == 1


def test_employee_can_request_repair_only_for_assigned_asset(client, app):
    login(client)
    with app.app_context():
        asset_id = Asset.query.filter_by(asset_tag="NSTAR-LP-0100").one().id
        employee_id = Employee.query.filter_by(employee_number="EMP-001").one().id
    client.post("/assets/assign", data={"asset_id": asset_id, "employee_id": employee_id})
    client.post("/auth/logout")
    login(client, "asha@example.test", "Employee-Test-Password-123!")
    response = client.post(
        "/maintenance/requests",
        data={"asset_id": asset_id, "description": "Battery is not charging"},
        follow_redirects=True,
    )
    assert b"Repair request submitted" in response.data
    with app.app_context():
        assert ServiceRequest.query.filter_by(asset_id=asset_id).count() == 1


def test_admin_cannot_update_service_request(client, app):
    with app.app_context():
        employee_id = Employee.query.filter_by(employee_number="EMP-001").one().id
        service_request = ServiceRequest(
            asset_id=1, employee_id=employee_id, description="Test request"
        )
        db.session.add(service_request)
        db.session.commit()
        request_id = service_request.id

    login(client, "admin@example.test", "Admin-Test-Password-123!")
    page = client.get("/maintenance/requests")
    assert page.status_code == 200
    assert b"Test request" in page.data
    assert f'action="/maintenance/requests/{request_id}/update"'.encode() not in page.data
    response = client.post(
        f"/maintenance/requests/{request_id}/update",
        data={"status": "Resolved", "resolution_notes": "Not authorized"},
    )
    assert response.status_code == 403
    with app.app_context():
        assert db.session.get(ServiceRequest, request_id).status == "Open"


def test_it_manager_can_update_service_request(client, app):
    with app.app_context():
        employee_id = Employee.query.filter_by(employee_number="EMP-001").one().id
        service_request = ServiceRequest(
            asset_id=1, employee_id=employee_id, description="Test request"
        )
        db.session.add(service_request)
        db.session.commit()
        request_id = service_request.id

    login(client)
    response = client.post(
        f"/maintenance/requests/{request_id}/update",
        data={"status": "Rejected", "resolution_notes": "Not repairable"},
    )
    assert response.status_code == 302
    with app.app_context():
        service_request = db.session.get(ServiceRequest, request_id)
        assert service_request.status == "Rejected"
        assert service_request.resolution_notes == "Not repairable"


def test_employee_sees_only_own_requests_and_no_forbidden_asset_link(client, app):
    with app.app_context():
        other_employee = Employee(
            employee_number="EMP-OTHER",
            first_name="Other",
            last_name="Employee",
            email="other@example.test",
            department="Engineering",
            cost_center="ENG-200",
        )
        other_asset = Asset(
            asset_tag="NSTAR-LP-OTHER",
            serial_number="SN-TEST-OTHER",
            category="Laptop",
            manufacturer="Northstar",
            model="ProBook",
            purchase_date=date(2023, 1, 1),
            purchase_cost=50000,
            salvage_value=5000,
            useful_life_years=5,
            status="Available",
        )
        db.session.add_all([other_employee, other_asset])
        db.session.flush()
        own_request = ServiceRequest(
            asset_id=1, employee_id=Employee.query.filter_by(employee_number="EMP-001").one().id,
            description="My battery issue",
        )
        other_request = ServiceRequest(
            asset_id=other_asset.id,
            employee_id=other_employee.id,
            description="Another employee's issue",
        )
        db.session.add_all([own_request, other_request])
        other_asset_id = other_asset.id
        db.session.commit()

    login(client, "asha@example.test", "Employee-Test-Password-123!")
    response = client.get("/maintenance/requests")
    assert response.status_code == 200
    assert b"My battery issue" in response.data
    assert b"Another employee's issue" not in response.data
    assert b"NSTAR-LP-0100</a>" not in response.data
    assert f'href="/assets/{other_asset_id}"'.encode() not in response.data


def test_maintenance_start_updates_asset_and_is_audited(client, app):
    login(client)
    response = client.post(
        "/maintenance/start/1",
        data={
            "issue_description": "Fan noise",
            "service_vendor": "Northstar Service",
            "repair_cost": "125.50",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        asset = db.session.get(Asset, 1)
        assert asset.status == "Under_Maintenance"
        assert Maintenance.query.filter_by(asset_id=1).count() == 1
        assert AuditLog.query.filter_by(action="maintenance.started").count() == 1


def test_admin_retirement_is_soft_and_logged(client, app):
    login(client, "admin@example.test", "Admin-Test-Password-123!")
    response = client.post("/assets/1/retire")
    assert response.status_code == 302
    with app.app_context():
        asset = db.session.get(Asset, 1)
        assert asset.status == "Retired"
        assert AuditLog.query.filter_by(action="asset.retired").count() == 1


def test_employee_manager_account_is_created_only_by_admin(client, app):
    login(client, "admin@example.test", "Admin-Test-Password-123!")
    response = client.post(
        "/employees/create",
        data={
            "employee_number": "EMP-002",
            "first_name": "Mina",
            "last_name": "Shah",
            "email": "mina@example.test",
            "department": "IT",
            "cost_center": "IT-200",
            "account_role": "IT Manager",
            "password": "Manager-Initial-Password-123!",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        from app.models import User

        user = User.query.filter_by(email="mina@example.test").one()
        assert user.role == "IT Manager"
        assert user.check_password("Manager-Initial-Password-123!")


def test_csrf_is_required_for_post_forms():
    application = create_app(
        {
            "SECRET_KEY": "csrf-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    response = application.test_client().post(
        "/auth/login",
        data={"email": "admin@example.test", "password": "irrelevant"},
    )
    assert response.status_code == 400
