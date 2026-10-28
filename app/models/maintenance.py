from app.extensions import db


class Maintenance(db.Model):
    __tablename__ = "maintenance_records"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False, index=True)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    issue_description = db.Column(db.Text, nullable=False)
    service_vendor = db.Column(db.String(160), nullable=True)
    repair_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    started_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    completed_at = db.Column(db.DateTime, nullable=True)
    completion_notes = db.Column(db.Text, nullable=True)

    asset = db.relationship("Asset", back_populates="maintenance_records")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        db.CheckConstraint("repair_cost >= 0", name="ck_maintenance_repair_cost"),
    )
