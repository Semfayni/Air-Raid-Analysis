"""Holiday and important-date proximity features for exploratory analysis."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

import pandas as pd

try:
    import holidays as holidays_package
except ImportError:  # pragma: no cover - requirements.txt includes this dependency.
    holidays_package = None


DEFAULT_HOLIDAY_WINDOW_DAYS = 2
MANUAL_IMPORTANT_DATES = {
    "01-01": "New Year",
    "02-24": "Full-Scale Invasion Anniversary",
    "05-09": "Symbolic May Date",
    "06-28": "Constitution Day",
    "08-24": "Independence Day",
    "10-14": "Defenders Day Historical Date",
    "12-25": "Christmas",
}


class HolidayFeatureError(ValueError):
    """Raised when holiday proximity features cannot be created."""


def build_holiday_calendar(start_year: int, end_year: int | None = None) -> pd.DataFrame:
    """Build a calendar of Ukrainian public holidays and manual important dates."""
    if end_year is None:
        end_year = start_year
    if start_year > end_year:
        raise HolidayFeatureError("start_year must be less than or equal to end_year.")

    years = range(start_year, end_year + 1)
    rows = _public_holiday_rows(years) + _manual_important_date_rows(years)
    calendar = pd.DataFrame(rows, columns=["holiday_date", "holiday_name", "holiday_type"])
    calendar = calendar.drop_duplicates(ignore_index=True)
    return calendar.sort_values(["holiday_date", "holiday_name"], ignore_index=True)


def find_nearest_holiday(
    dates: Iterable[date] | pd.Series,
    holiday_calendar: pd.DataFrame,
    *,
    holiday_window_days: int = DEFAULT_HOLIDAY_WINDOW_DAYS,
) -> pd.DataFrame:
    """Find the nearest holiday or important date for each input date."""
    _validate_window(holiday_window_days)
    _require_calendar_columns(holiday_calendar)

    calendar = holiday_calendar.copy()
    calendar["holiday_date"] = pd.to_datetime(calendar["holiday_date"]).dt.date

    rows = []
    for value in dates:
        current_date = _to_date(value)
        nearest = _nearest_calendar_row(current_date, calendar)
        days_to_nearest = (nearest["holiday_date"] - current_date).days
        rows.append(
            {
                "nearest_holiday_name": nearest["holiday_name"],
                "nearest_holiday_date": nearest["holiday_date"],
                "days_to_nearest_holiday": days_to_nearest,
                "is_holiday_window": abs(days_to_nearest) <= holiday_window_days,
            }
        )

    return pd.DataFrame(rows)


def add_holiday_proximity_features(
    frame: pd.DataFrame,
    *,
    date_column: str = "date",
    holiday_window_days: int = DEFAULT_HOLIDAY_WINDOW_DAYS,
    holiday_calendar: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add exploratory holiday-window features to a daily dataframe.

    Holiday proximity is a context feature for exploring whether alert activity
    falls near Ukrainian public holidays or selected important dates. It is not
    evidence that one event explains another.
    """
    if date_column not in frame.columns:
        raise HolidayFeatureError(f"Missing required date column: {date_column}.")
    _validate_window(holiday_window_days)

    featured = frame.copy()
    dates = featured[date_column].map(_to_date)
    if holiday_calendar is None:
        holiday_calendar = _calendar_for_dates(dates)

    proximity = find_nearest_holiday(
        dates,
        holiday_calendar,
        holiday_window_days=holiday_window_days,
    )
    for column in proximity.columns:
        featured[column] = proximity[column].values
    return featured


def _public_holiday_rows(years: Iterable[int]) -> list[dict[str, object]]:
    if holidays_package is None:
        return []

    public_holidays = holidays_package.country_holidays("UA", years=list(years))
    return [
        {
            "holiday_date": holiday_date,
            "holiday_name": str(holiday_name),
            "holiday_type": "public_holiday",
        }
        for holiday_date, holiday_name in public_holidays.items()
    ]


def _manual_important_date_rows(years: Iterable[int]) -> list[dict[str, object]]:
    rows = []
    for year in years:
        for month_day, name in MANUAL_IMPORTANT_DATES.items():
            month, day = month_day.split("-")
            rows.append(
                {
                    "holiday_date": date(year, int(month), int(day)),
                    "holiday_name": name,
                    "holiday_type": "important_date",
                }
            )
    return rows


def _calendar_for_dates(dates: pd.Series) -> pd.DataFrame:
    valid_dates = dates.dropna()
    if valid_dates.empty:
        raise HolidayFeatureError("Cannot build a holiday calendar from empty dates.")

    start_year = min(value.year for value in valid_dates)
    end_year = max(value.year for value in valid_dates)
    return build_holiday_calendar(start_year, end_year)


def _nearest_calendar_row(current_date: date, calendar: pd.DataFrame) -> pd.Series:
    if pd.isna(current_date):
        raise HolidayFeatureError("Date values must not be empty.")

    distances = calendar["holiday_date"].map(lambda holiday_date: holiday_date - current_date)
    nearest_index = distances.map(lambda delta: abs(delta.days)).idxmin()
    return calendar.loc[nearest_index]


def _to_date(value: object) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if pd.isna(value):
        raise HolidayFeatureError("Date values must not be empty.")
    return pd.to_datetime(value).date()


def _validate_window(holiday_window_days: int) -> None:
    if holiday_window_days < 0:
        raise HolidayFeatureError("holiday_window_days must be zero or greater.")


def _require_calendar_columns(calendar: pd.DataFrame) -> None:
    required = {"holiday_date", "holiday_name"}
    missing = sorted(required.difference(calendar.columns))
    if missing:
        raise HolidayFeatureError(
            f"Holiday calendar is missing required column(s): {', '.join(missing)}."
        )
