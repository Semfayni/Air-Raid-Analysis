"""Feature engineering for historical air alert analysis."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd


KYIV_TIMEZONE = "Europe/Kyiv"
UTC_DATETIME_COLUMNS = ("started_at", "finished_at", "updated_at")


class FeatureEngineeringError(ValueError):
    """Raised when required feature input columns are unavailable."""


def add_historical_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of historical alerts with analysis-ready columns.

    Source timestamps are UTC, which is the safest storage format. Daily, weekly,
    and holiday analysis must use Kyiv local time as Ukrainian holidays and
    important dates are local calendar dates, not UTC dates.
    """
    _require_columns(frame, {"started_at"})

    featured = frame.copy()
    _add_kyiv_time_columns(featured)
    _add_duration_columns(featured)
    _add_calendar_columns(featured)
    _add_grouping_region(featured)
    return featured


def daily_alert_count(
    frame: pd.DataFrame,
    region: str | None = None,
    *,
    include_unfinished: bool = False,
) -> pd.DataFrame:
    """Count alerts by Kyiv-local date.

    Unfinished alerts are excluded by default so historical summaries do not mix
    complete alert intervals with alerts that have no known end time.
    """
    filtered = _analysis_frame(frame, region, include_unfinished=include_unfinished)
    return (
        filtered.groupby("date", dropna=False)
        .size()
        .reset_index(name="alert_count")
        .sort_values("date", ignore_index=True)
    )


def daily_alert_duration(
    frame: pd.DataFrame,
    region: str | None = None,
    *,
    include_unfinished: bool = False,
) -> pd.DataFrame:
    """Sum alert duration by Kyiv-local date, splitting intervals across days."""
    filtered = _analysis_frame(frame, region, include_unfinished=include_unfinished)
    allocated = allocate_alert_duration_by_day(filtered)
    if allocated.empty:
        return pd.DataFrame(columns=["date", "total_duration_hours", "duration_minutes"])
    return (
        allocated.groupby("date", dropna=False)["duration_hours"]
        .sum()
        .reset_index(name="total_duration_hours")
        .sort_values("date", ignore_index=True)
        .assign(duration_minutes=lambda data: data["total_duration_hours"] * 60)
    )


def allocate_alert_duration_by_day(frame: pd.DataFrame) -> pd.DataFrame:
    """Allocate finished alert interval hours across overlapping Kyiv-local dates."""
    featured = (
        add_historical_features(frame)
        if not _has_required_features(frame)
        else frame.copy()
    )
    finished = featured[featured["is_finished"]].copy()
    rows = []
    for row in finished.itertuples(index=False):
        rows.extend(
            _split_interval_by_kyiv_day(
                getattr(row, "started_at_kyiv"),
                getattr(row, "finished_at_kyiv"),
                getattr(row, "region", None),
            )
        )
    return pd.DataFrame(
        rows,
        columns=["date", "region", "duration_seconds", "duration_hours"],
    )


def largest_raw_alert_durations(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return longest raw alert durations for spike diagnostics."""
    featured = (
        add_historical_features(frame)
        if not _has_required_features(frame)
        else frame.copy()
    )
    completed = featured[featured["is_finished"]].copy()
    columns = ["region", "started_at_kyiv", "finished_at_kyiv", "duration_hours"]
    if completed.empty:
        return pd.DataFrame(columns=columns)
    return completed.sort_values("duration_hours", ascending=False)[columns].head(limit)


def largest_daily_duration_values(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return largest split daily duration totals for spike diagnostics."""
    daily = daily_alert_duration(frame)
    if daily.empty:
        return daily
    return daily.sort_values("total_duration_hours", ascending=False).head(limit)


def regional_summary(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
) -> pd.DataFrame:
    """Summarize completed historical alerts by grouping region."""
    filtered = _analysis_frame(frame, None, include_unfinished=include_unfinished)
    summary = (
        filtered.groupby("region", dropna=False)
        .agg(
            alert_count=("started_at", "size"),
            total_duration_minutes=("duration_minutes", "sum"),
            mean_duration_minutes=("duration_minutes", "mean"),
            first_started_at_kyiv=("started_at_kyiv", "min"),
            last_started_at_kyiv=("started_at_kyiv", "max"),
        )
        .reset_index()
    )
    return summary.sort_values("alert_count", ascending=False, ignore_index=True)


def hourly_weekday_matrix(
    frame: pd.DataFrame,
    region: str | None = None,
    *,
    include_unfinished: bool = False,
) -> pd.DataFrame:
    """Return alert counts by Kyiv-local weekday and hour."""
    filtered = _analysis_frame(frame, region, include_unfinished=include_unfinished)
    matrix = filtered.pivot_table(
        index="weekday",
        columns="hour",
        values="started_at",
        aggfunc="size",
        fill_value=0,
    )
    return matrix.reindex(index=range(7), columns=range(24), fill_value=0)


def _analysis_frame(
    frame: pd.DataFrame,
    region: str | None,
    *,
    include_unfinished: bool,
) -> pd.DataFrame:
    featured = (
        add_historical_features(frame)
        if not _has_required_features(frame)
        else frame.copy()
    )
    if not include_unfinished:
        featured = featured[featured["is_finished"]]
    if region is not None:
        featured = featured[featured["region"] == region]
    return featured


def _has_required_features(frame: pd.DataFrame) -> bool:
    required = {
        "started_at_kyiv",
        "finished_at_kyiv",
        "duration_minutes",
        "duration_hours",
        "is_finished",
        "date",
        "hour",
        "weekday",
        "weekday_name",
        "month",
        "year",
        "region",
    }
    if "updated_at" in frame.columns:
        required.add("updated_at_kyiv")
    return required.issubset(frame.columns)


def _add_kyiv_time_columns(frame: pd.DataFrame) -> None:
    for column in UTC_DATETIME_COLUMNS:
        if column in frame.columns:
            frame[f"{column}_kyiv"] = pd.to_datetime(
                frame[column],
                errors="coerce",
                utc=True,
            ).dt.tz_convert(KYIV_TIMEZONE)


def _add_duration_columns(frame: pd.DataFrame) -> None:
    _require_columns(frame, {"started_at", "finished_at"})
    frame["is_finished"] = frame["finished_at"].notna()
    duration = frame["finished_at"] - frame["started_at"]
    negative_duration = frame["is_finished"] & (duration.dt.total_seconds() < 0)
    if negative_duration.any():
        raise FeatureEngineeringError("Alert duration must not be negative.")
    frame["duration_minutes"] = duration.dt.total_seconds() / 60
    frame.loc[~frame["is_finished"], "duration_minutes"] = pd.NA
    frame["duration_hours"] = frame["duration_minutes"] / 60


def _split_interval_by_kyiv_day(start, finish, region: object) -> list[dict[str, object]]:
    if pd.isna(start) or pd.isna(finish):
        return []
    if finish < start:
        raise FeatureEngineeringError("Alert duration must not be negative.")

    current = start
    rows = []
    while current < finish:
        next_date = current.date() + timedelta(days=1)
        next_midnight = pd.Timestamp(next_date).tz_localize(KYIV_TIMEZONE)
        segment_end = min(finish, next_midnight)
        duration_seconds = (segment_end - current).total_seconds()
        if duration_seconds > 0:
            rows.append(
                {
                    "date": current.date(),
                    "region": region,
                    "duration_seconds": duration_seconds,
                    "duration_hours": duration_seconds / 3600,
                }
            )
        current = segment_end
    return rows


def _add_calendar_columns(frame: pd.DataFrame) -> None:
    _require_columns(frame, {"started_at_kyiv"})
    started = frame["started_at_kyiv"].dt
    frame["date"] = started.date
    frame["hour"] = started.hour
    frame["weekday"] = started.weekday
    frame["weekday_name"] = started.day_name()
    frame["month"] = started.month
    frame["year"] = started.year


def _add_grouping_region(frame: pd.DataFrame) -> None:
    candidates = [
        column
        for column in ("region", "oblast", "location_title")
        if column in frame.columns
    ]
    if not candidates:
        raise FeatureEngineeringError(
            "Cannot create grouping region. Expected at least one of: region, oblast, "
            "location_title."
        )

    grouped_region = _clean_text_values(frame[candidates[0]])
    for column in candidates[1:]:
        grouped_region = grouped_region.combine_first(_clean_text_values(frame[column]))
    frame["region"] = grouped_region


def _clean_text_values(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned == "")


def _require_columns(frame: pd.DataFrame, columns: set[str]) -> None:
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise FeatureEngineeringError(
            f"Missing required column(s) for feature engineering: {', '.join(missing)}."
        )
