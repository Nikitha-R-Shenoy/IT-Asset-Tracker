from app.extensions import db


class Allocation(db.Model):
    __tablename__ = "allocations"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, index=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True
    )
    assigned_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    checkout_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    return_date = db.Column(db.DateTime, nullable=True, index=True)
    return_condition = db.Column(db.String(20), nullable=True)
    checkout_notes = db.Column(db.Text, nullable=True)
    return_notes = db.Column(db.Text, nullable=True)

    asset = db.relationship("Asset", back_populates="allocations")
    employee = db.relationship("Employee", back_populates="allocations")
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])

    __table_args__ = (
        db.CheckConstraint(
            "return_condition IS NULL OR return_condition IN ('Good', 'Damaged', 'Defective')",
            name="ck_allocation_return_condition",
        ),
    )
