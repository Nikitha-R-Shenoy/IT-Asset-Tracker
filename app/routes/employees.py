from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Employee, User
from app.services.audit_service import record_audit
from app.utils.decorators import manager_required
from app.utils.validators import validate_email

bp = Blueprint("employees", __name__, url_prefix="/employees")


@bp.get("")
@manager_required
def index():
    query = request.args.get("q", "").strip()
    employees = Employee.query
    if query:
        pattern = f"%{query}%"
        employees = employees.filter(
            or_(
                Employee.employee_number.ilike(pattern),
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                Employee.email.ilike(pattern),
                Employee.department.ilike(pattern),
            )
        )
    return render_template(
        "employees/list.html",
        employees=employees.order_by(Employee.last_name).all(),
        query=query,
    )


@bp.route("/create", methods=["GET", "POST"])
@manager_required
def create():
    if request.method == "POST":
        employee_number = request.form.get("employee_number", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        cost_center = request.form.get("cost_center", "").strip()
        password = request.form.get("password", "")
        account_role = request.form.get("account_role", "Employee")
        try:
            if not all(
                (employee_number, first_name, last_name, email, department, cost_center)
            ):
                raise ValueError(
                    "Employee number, name, email, department, and cost center are required."
                )
            validate_email(email)
            if account_role not in {"Employee", "IT Manager"}:
                raise ValueError("Invalid employee portal role.")
            if account_role == "IT Manager" and g.current_user.role != "Admin":
                raise ValueError("Only an administrator can create IT Manager accounts.")
            if Employee.query.filter(
                or_(Employee.employee_number == employee_number, Employee.email == email)
            ).first() or User.query.filter_by(email=email).first():
                raise ValueError("Employee number or email already exists.")
            employee = Employee(
                employee_number=employee_number,
                first_name=first_name,
                last_name=last_name,
                email=email,
                department=department,
                cost_center=cost_center,
            )
            db.session.add(employee)
            db.session.flush()
            if password:
                if len(password) < 12:
                    raise ValueError("Employee account passwords must be at least 12 characters.")
                account = User(email=email, role=account_role, employee=employee)
                account.set_password(password)
                db.session.add(account)
            record_audit(
                "employee.created",
                "Employee",
                employee.id,
                {
                    "employee_number": employee.employee_number,
                    "account_created": bool(password),
                    "account_role": account_role if password else None,
                },
            )
            db.session.commit()
            flash("Employee created successfully.", "success")
            return redirect(url_for("employees.index"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")
        except IntegrityError:
            db.session.rollback()
            flash("Employee number or email already exists.", "danger")
            return render_template("employees/form.html"), 400
        except Exception:
            db.session.rollback()
            raise
    return render_template("employees/form.html")


@bp.post("/<int:employee_id>/toggle")
@manager_required
def toggle(employee_id):
    employee = db.session.get(Employee, employee_id)
    if not employee:
        abort(404)
    employee.is_active = not employee.is_active
    if employee.user:
        employee.user.is_active = employee.is_active
    record_audit(
        "employee.activated" if employee.is_active else "employee.deactivated",
        "Employee",
        employee.id,
        {"employee_number": employee.employee_number},
    )
    db.session.commit()
    flash(
        f"{employee.full_name} is now "
        f"{'active' if employee.is_active else 'inactive'}.",
        "success",
    )
    return redirect(url_for("employees.index"))
