from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=True, unique=True
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    employee = db.relationship("Employee", back_populates="user", foreign_keys=[employee_id])

    __table_args__ = (
        db.CheckConstraint("role IN ('Admin', 'IT Manager', 'Employee')", name="ck_user_role"),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password, method="pbkdf2:sha256:600000"
        )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
