from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=False, index=True)
    entity_id = db.Column(db.String(80), nullable=True, index=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])

    @classmethod
    def _immutable(cls, _mapper, _connection, _target):
        raise RuntimeError("Audit log entries are append-only.")


db.event.listen(AuditLog, "before_update", AuditLog._immutable)
db.event.listen(AuditLog, "before_delete", AuditLog._immutable)
