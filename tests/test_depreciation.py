from datetime import date
from decimal import Decimal

import pytest

from app.services.depreciation import calculate_depreciation


def test_straight_line_value_at_two_years():
    value = calculate_depreciation(50000, 5000, 5, age_years=2)
    assert value == Decimal("32000.00")


def test_depreciation_stops_at_salvage_value():
    value = calculate_depreciation(50000, 5000, 5, age_years=6)
    assert value == Decimal("5000.00")


def test_date_based_age_uses_365_25_day_year():
    value = calculate_depreciation(
        50000, 5000, 5, date(2020, 1, 1), calculation_date=date(2021, 1, 1)
    )
    assert value == Decimal("40981.52")


@pytest.mark.parametrize(
    "values",
    [
        (100, 101, 5, date(2020, 1, 1)),
        (100, 0, 0, date(2020, 1, 1)),
    ],
)
def test_invalid_depreciation_inputs_raise(values):
    with pytest.raises(ValueError):
        calculate_depreciation(*values)
