import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation


REQUIRED_ASSET_COLUMNS = {
    "asset_tag",
    "serial_number",
    "category",
    "manufacturer",
    "model",
    "purchase_date",
    "purchase_cost",
    "salvage_value",
    "useful_life_years",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email):
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid work email address.")


def parse_date(value, field_name, required=True):
    if not value and not required:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid date (YYYY-MM-DD).")
    return parsed


def parse_money(value, field_name, minimum=Decimal("0")):
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValueError(f"{field_name} must be a valid amount.")
    if not amount.is_finite() or amount < minimum:
        raise ValueError(f"{field_name} must be at least {minimum}.")
    if amount > Decimal("9999999999.99"):
        raise ValueError(f"{field_name} exceeds the supported maximum.")
    rounded = amount.quantize(Decimal("0.01"))
    if rounded != amount:
        raise ValueError(f"{field_name} must have no more than two decimal places.")
    return rounded


def parse_asset_csv(stream):
    text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text)
    fields = {name.strip() for name in (reader.fieldnames or [])}
    missing = REQUIRED_ASSET_COLUMNS - fields
    if missing:
        raise ValueError("CSV is missing required columns: " + ", ".join(sorted(missing)))
    rows = []
    errors = []
    for line_number, raw in enumerate(reader, start=2):
        row = {str(key).strip(): (value or "").strip() for key, value in raw.items() if key}
        try:
            asset = {
                "asset_tag": row["asset_tag"],
                "serial_number": row["serial_number"],
                "category": row["category"],
                "manufacturer": row["manufacturer"],
                "model": row["model"],
                "vendor": row.get("vendor") or None,
                "purchase_date": parse_date(row["purchase_date"], "Purchase date"),
                "purchase_cost": parse_money(row["purchase_cost"], "Purchase cost"),
                "salvage_value": parse_money(row["salvage_value"], "Salvage value"),
                "useful_life_years": int(row["useful_life_years"]),
                "warranty_expiry": parse_date(
                    row.get("warranty_expiry"), "Warranty expiry", required=False
                ),
                "notes": row.get("notes") or None,
            }
            required = ("asset_tag", "serial_number", "category", "manufacturer", "model")
            if not all(asset[key] for key in required):
                raise ValueError("Tag, serial, category, manufacturer, and model are required.")
            if asset["useful_life_years"] < 1:
                raise ValueError("Useful life must be greater than zero.")
            if asset["salvage_value"] > asset["purchase_cost"]:
                raise ValueError("Salvage value cannot exceed purchase cost.")
            rows.append(asset)
        except (ValueError, KeyError) as error:
            errors.append(f"Row {line_number}: {error}")
    return rows, errors
