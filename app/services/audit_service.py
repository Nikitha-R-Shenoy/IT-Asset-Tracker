import json

from flask import has_request_context, request, session

from app.extensions import db
from app.models import AuditLog


def record_audit(action, entity_type, entity_id=None, details=None, actor=None):
    actor_id = actor.id if actor is not None else None
    if actor_id is None and has_request_context():
        actor_id = session.get("user_id")
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=json.dumps(details, default=str, sort_keys=True) if details is not None else None,
        ip_address=request.remote_addr if has_request_context() else None,
    )
    db.session.add(log)
    return log
