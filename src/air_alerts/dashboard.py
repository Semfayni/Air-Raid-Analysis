"""Pure dashboard helpers for historical overview and regional pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class OverviewKpis:
    """Top-level metrics for the overview page."""

    total_alerts: int
    total_alert_hours: float
    date_range: str
    most_affected_region: str


def filter_featured_alerts(
    frame: pd.DataFrame,
    *,
    region: str | None = None,
    date_range: tuple[date, date] | None = None,
    sources: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Filter a featured historical dataframe without mutating it."""
    filtered = frame.copy()
    if region:
        filtered = filtered[filtered["region"] == region]
    if date_range is not None:
        start_date, end_date = date_range
        filtered = filtered[(filtered["date"] >= start_date) & (filtered["date"] <= end_date)]
    if sources is not None and "source" in filtered.columns:
        selected_sources = set(sources)
        filtered = filtered[filtered["source"].isin(selected_sources)]
    return filtered


def overview_kpis(featured: pd.DataFrame) -> OverviewKpis:
    """Calculate overview KPI values from featured historical alerts."""
    completed = _completed_alerts(featured)
    date_range = _format_date_range(featured)

    if completed.empty:
        return OverviewKpis(
            total_alerts=0,
            total_alert_hours=0.0,
            date_range=date_range,
            most_affected_region="No completed alerts",
        )

    region_counts = completed.groupby("region", dropna=False).size().sort_values(ascending=False)
    most_affected_region = str(region_counts.index[0])
    return OverviewKpis(
        total_alerts=int(len(completed)),
        total_alert_hours=float(completed["duration_hours"].sum()),
        date_range=date_range,
        most_affected_region=most_affected_region,
    )


def top_regions_by_alert_count(featured: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return top regions by completed alert count."""
    completed = _completed_alerts(featured)
    if completed.empty:
        return pd.DataFrame(columns=["region", "alert_count"])
    return (
        completed.groupby("region", dropna=False)
        .size()
        .reset_index(name="alert_count")
        .sort_values("alert_count", ascending=False, ignore_index=True)
        .head(limit)
    )


def top_regions_by_duration(featured: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return top regions by completed alert duration."""
    completed = _completed_alerts(featured)
    if completed.empty:
        return pd.DataFrame(columns=["region", "total_duration_hours"])
    return (
        completed.groupby("region", dropna=False)["duration_hours"]
        .sum()
        .reset_index(name="total_duration_hours")
        .sort_values("total_duration_hours", ascending=False, ignore_index=True)
        .head(limit)
    )


def monthly_alert_trend(featured: pd.DataFrame) -> pd.DataFrame:
    """Aggregate completed alerts by month for the selected region view."""
    completed = _completed_alerts(featured)
    if completed.empty:
        return pd.DataFrame(columns=["month", "alert_count", "total_duration_hours"])
    monthly = completed.copy()
    monthly["month"] = pd.to_datetime(monthly["date"]).dt.to_period("M").astype(str)
    return (
        monthly.groupby("month", dropna=False)
        .agg(
            alert_count=("started_at", "size"),
            total_duration_hours=("duration_hours", "sum"),
        )
        .reset_index()
        .sort_values("month", ignore_index=True)
    )


def region_interpretation(region: str, featured: pd.DataFrame) -> str:
    """Build deterministic summary text for a selected region."""
    completed = _completed_alerts(featured)
    if completed.empty:
        return f"{region}: no completed alerts in the current selection."

    alert_count = len(completed)
    total_hours = completed["duration_hours"].sum()
    average_hours = completed["duration_hours"].mean()
    first_date = completed["date"].min()
    last_date = completed["date"].max()
    return (
        f"{region}: {alert_count:,} completed alerts from {first_date} to {last_date}, "
        f"with {total_hours:,.1f} total alert hours and an average duration of "
        f"{average_hours:.2f} hours."
    )


def _completed_alerts(frame: pd.DataFrame) -> pd.DataFrame:
    if "is_finished" not in frame.columns:
        return frame.copy()
    return frame[frame["is_finished"]].copy()


def _format_date_range(frame: pd.DataFrame) -> str:
    if frame.empty or "date" not in frame.columns:
        return "No dates"
    return f"{frame['date'].min()} to {frame['date'].max()}"
