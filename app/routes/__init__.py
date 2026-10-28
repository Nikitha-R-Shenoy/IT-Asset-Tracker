from app.routes.allocations import bp as allocations_bp
from app.routes.assets import bp as assets_bp
from app.routes.audit import bp as audit_bp
from app.routes.auth import bp as auth_bp
from app.routes.dashboard import bp as dashboard_bp
from app.routes.employees import bp as employees_bp
from app.routes.maintenance import bp as maintenance_bp
from app.routes.reports import bp as reports_bp


def register_blueprints(app):
    for blueprint in (
        auth_bp,
        dashboard_bp,
        assets_bp,
        employees_bp,
        allocations_bp,
        maintenance_bp,
        reports_bp,
        audit_bp,
    ):
        app.register_blueprint(blueprint)
