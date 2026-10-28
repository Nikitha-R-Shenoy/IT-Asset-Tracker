from app.extensions import db


class ServiceRequest(db.Model):
    __tablename__ = "service_requests"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, index=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True
    )
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Open", index=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    asset = db.relationship("Asset", back_populates="service_requests")
    employee = db.relationship("Employee", back_populates="service_requests")

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('Open', 'In Progress', 'Resolved', 'Rejected')",
            name="ck_service_request_status",
        ),
    )
