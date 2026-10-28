from app.models.asset import ASSET_STATUSES


class InvalidStateTransitionError(ValueError):
    pass


ALLOWED_TRANSITIONS = {
    "Available": {"Assigned", "In_Repair", "Under_Maintenance", "Retired"},
    "Assigned": {"Available", "In_Repair", "Under_Maintenance", "Retired"},
    "In_Repair": {"Available", "Under_Maintenance", "Retired"},
    "Under_Maintenance": {"Available", "In_Repair", "Retired"},
    "Retired": set(),
}


def validate_transition(current_status, new_status):
    if new_status not in ASSET_STATUSES:
        raise InvalidStateTransitionError(f"Unknown asset status: {new_status}")
    if new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise InvalidStateTransitionError(
            f"Cannot transition asset from {current_status} to {new_status}."
        )
