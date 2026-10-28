from flask import Flask, g, render_template

from config import Config
from app.extensions import csrf, db


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    if isinstance(config_object, dict):
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object or Config)
    if not app.config.get("SECRET_KEY"):
        if app.config.get("TESTING"):
            app.config["SECRET_KEY"] = "test-only-secret"
        else:
            raise RuntimeError("SECRET_KEY must be configured in the environment.")

    db.init_app(app)
    csrf.init_app(app)

    from app.routes import register_blueprints

    register_blueprints(app)

    @app.context_processor
    def inject_current_user():
        return {"current_user": getattr(g, "current_user", None)}

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables."""
        db.create_all()
        print("Database tables created.")

    return app
