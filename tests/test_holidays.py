from __future__ import annotations

from datetime import date

import pandas as pd

from air_alerts.holidays import (
    add_holiday_proximity_features,
    build_holiday_calendar,
    find_nearest_holiday,
)


def test_build_holiday_calendar_includes_fixed_important_dates() -> None:
    calendar = build_holiday_calendar(2024, 2024)
    dates = set(calendar["holiday_date"])

    assert date(2024, 8, 24) in dates
    assert date(2024, 2, 24) in dates


def test_day_before_independence_day_is_inside_default_window() -> None:
    calendar = build_holiday_calendar(2024, 2024)

    result = find_nearest_holiday([date(2024, 8, 23)], calendar)

    assert result.loc[0, "nearest_holiday_name"] == "Independence Day"
    assert result.loc[0, "days_to_nearest_holiday"] == 1
    assert bool(result.loc[0, "is_holiday_window"]) is True


def test_date_far_from_important_dates_is_outside_small_window() -> None:
    calendar = build_holiday_calendar(2024, 2024)

    result = find_nearest_holiday(
        [date(2024, 3, 15)],
        calendar,
        holiday_window_days=1,
    )

    assert bool(result.loc[0, "is_holiday_window"]) is False


def test_custom_holiday_window_size() -> None:
    calendar = build_holiday_calendar(2024, 2024)

    small_window = find_nearest_holiday(
        [date(2024, 8, 21)],
        calendar,
        holiday_window_days=2,
    )
    wider_window = find_nearest_holiday(
        [date(2024, 8, 21)],
        calendar,
        holiday_window_days=3,
    )

    assert bool(small_window.loc[0, "is_holiday_window"]) is False
    assert bool(wider_window.loc[0, "is_holiday_window"]) is True


def test_add_holiday_proximity_features_works_with_date_column() -> None:
    frame = pd.DataFrame(
        {
            "date": [date(2024, 8, 23), date(2024, 3, 15)],
            "alert_count": [5, 2],
        }
    )
    calendar = build_holiday_calendar(2024, 2024)

    result = add_holiday_proximity_features(
        frame,
        holiday_calendar=calendar,
        holiday_window_days=2,
    )

    assert "nearest_holiday_name" in result.columns
    assert "nearest_holiday_date" in result.columns
    assert "days_to_nearest_holiday" in result.columns
    assert "is_holiday_window" in result.columns
    assert result.loc[0, "nearest_holiday_name"] == "Independence Day"
    assert bool(result.loc[0, "is_holiday_window"]) is True
