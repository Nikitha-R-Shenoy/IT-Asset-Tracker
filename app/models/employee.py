from app.extensions import db


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    employee_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    first_name = db.Column(db.String(100), nullable=False, index=True)
    last_name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    department = db.Column(db.String(120), nullable=False, index=True)
    cost_center = db.Column(db.String(80), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    user = db.relationship("User", back_populates="employee", uselist=False)
    allocations = db.relationship("Allocation", back_populates="employee")
    service_requests = db.relationship("ServiceRequest", back_populates="employee")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
