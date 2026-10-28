from datetime import date
from decimal import Decimal


def calculate_depreciation(
    purchase_cost,
    salvage_value,
    useful_life_years,
    purchase_date=None,
    calculation_date=None,
    age_years=None,
):
    """Return straight-line current book value, capped at the salvage value."""
    cost = Decimal(str(purchase_cost))
    salvage = Decimal(str(salvage_value))
    if useful_life_years <= 0:
        raise ValueError("Useful life must be greater than zero.")
    if cost < 0 or salvage < 0 or salvage > cost:
        raise ValueError("Cost and salvage value are invalid.")
    if age_years is None:
        if purchase_date is None:
            raise ValueError("Provide either an asset age or purchase date.")
        if isinstance(purchase_date, str):
            purchase_date = date.fromisoformat(purchase_date)
        calculation_date = calculation_date or date.today()
        age_years = Decimal(str((calculation_date - purchase_date).days)) / Decimal("365.25")
    else:
        age_years = Decimal(str(age_years))
    if age_years <= 0:
        return cost.quantize(Decimal("0.01"))
    if age_years >= useful_life_years:
        return salvage.quantize(Decimal("0.01"))
    annual_depreciation = (cost - salvage) / Decimal(useful_life_years)
    book_value = cost - annual_depreciation * age_years
    return max(salvage, book_value).quantize(Decimal("0.01"))
