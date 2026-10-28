from app.extensions import db


ASSET_STATUSES = (
    "Available",
    "Assigned",
    "In_Repair",
    "Under_Maintenance",
    "Retired",
)


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(80), nullable=False, unique=True, index=True)
    serial_number = db.Column(db.String(120), nullable=False, unique=True, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    manufacturer = db.Column(db.String(120), nullable=False, index=True)
    model = db.Column(db.String(120), nullable=False, index=True)
    vendor = db.Column(db.String(160), nullable=True, index=True)
    purchase_date = db.Column(db.Date, nullable=False)
    purchase_cost = db.Column(db.Numeric(12, 2), nullable=False)
    salvage_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    useful_life_years = db.Column(db.Integer, nullable=False, default=5)
    warranty_expiry = db.Column(db.Date, nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="Available", index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    allocations = db.relationship("Allocation", back_populates="asset")
    maintenance_records = db.relationship("Maintenance", back_populates="asset")
    service_requests = db.relationship("ServiceRequest", back_populates="asset")

    __table_args__ = (
        db.CheckConstraint("purchase_cost >= 0", name="ck_asset_purchase_cost"),
        db.CheckConstraint(
            "salvage_value >= 0 AND salvage_value <= purchase_cost",
            name="ck_asset_salvage_value",
        ),
        db.CheckConstraint("useful_life_years > 0", name="ck_asset_useful_life"),
        db.CheckConstraint(
            "status IN ('Available', 'Assigned', 'In_Repair', "
            "'Under_Maintenance', 'Retired')",
            name="ck_asset_status",
        ),
    )
