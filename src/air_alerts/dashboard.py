"""Pure dashboard helpers for historical overview and regional pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd

from air_alerts.metrics import (
    daily_oblast_metrics,
    national_daily_metrics,
    regional_metric_summary,
)


@dataclass(frozen=True)
class OverviewKpis:
    """Top-level metrics for the overview page."""

    national_alert_wave_count: int
    national_oblast_episode_count: int
    alert_start_count: int
    affected_oblast_hours: float
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
    national = national_daily_metrics(featured)
    regional = regional_metric_summary(featured)
    date_range = _format_date_range(featured)

    if national.empty:
        return OverviewKpis(
            national_alert_wave_count=0,
            national_oblast_episode_count=0,
            alert_start_count=0,
            affected_oblast_hours=0.0,
            date_range=date_range,
            most_affected_region="No oblast metrics",
        )

    most_affected_region = (
        str(regional.loc[0, "region"]) if not regional.empty else "No oblast metrics"
    )
    return OverviewKpis(
        national_alert_wave_count=int(national["national_alert_wave_count"].sum()),
        national_oblast_episode_count=int(national["national_oblast_episode_count"].sum()),
        alert_start_count=int(national["national_oblast_episode_count"].sum()),
        affected_oblast_hours=float(national["affected_oblast_hours"].sum()),
        date_range=date_range,
        most_affected_region=most_affected_region,
    )


def top_regions_by_alert_count(featured: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return top regions by oblast-level alert start count."""
    summary = regional_metric_summary(featured)
    if summary.empty:
        return pd.DataFrame(columns=["region", "oblast_episode_count"])
    return (
        summary[["region", "oblast_episode_count"]]
        .sort_values("oblast_episode_count", ascending=False, ignore_index=True)
        .head(limit)
    )


def top_regions_by_duration(featured: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return top regions by merged affected oblast hours."""
    summary = regional_metric_summary(featured)
    if summary.empty:
        return pd.DataFrame(columns=["region", "affected_oblast_hours"])
    return (
        summary[["region", "affected_oblast_hours"]]
        .sort_values("affected_oblast_hours", ascending=False, ignore_index=True)
        .head(limit)
    )


def monthly_alert_trend(featured: pd.DataFrame) -> pd.DataFrame:
    """Aggregate oblast-level metrics by month for the selected region view."""
    daily = daily_oblast_metrics(featured)
    if daily.empty:
        return pd.DataFrame(
            columns=["month", "oblast_episode_count", "affected_oblast_hours"]
        )
    monthly = daily.copy()
    monthly["month"] = pd.to_datetime(monthly["date"]).dt.to_period("M").astype(str)
    return (
        monthly.groupby("month", dropna=False)
        .agg(
            oblast_episode_count=("oblast_episode_count", "sum"),
            affected_oblast_hours=("affected_oblast_hours", "sum"),
        )
        .reset_index()
        .sort_values("month", ignore_index=True)
    )


def region_interpretation(region: str, featured: pd.DataFrame) -> str:
    """Build deterministic summary text for a selected region."""
    summary = regional_metric_summary(featured)
    if summary.empty:
        return f"{region}: no completed oblast-level alert intervals in the current selection."

    row = summary.iloc[0]
    alert_count = int(row["oblast_episode_count"])
    total_hours = float(row["affected_oblast_hours"])
    active_days = int(row["active_days"])
    return (
        f"{region}: {alert_count:,} merged oblast episode starts from {row['first_date']} "
        f"to {row['last_date']}, with {total_hours:,.1f} affected oblast hours "
        f"across {active_days:,} active days."
    )


def _format_date_range(frame: pd.DataFrame) -> str:
    if frame.empty or "date" not in frame.columns:
        return "No dates"
    return f"{frame['date'].min()} to {frame['date'].max()}"
