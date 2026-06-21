"""Analytical alert metrics built from oblast-level interval unions."""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable

import pandas as pd

from air_alerts.features import KYIV_TIMEZONE, add_historical_features


DEFAULT_METRIC_SOURCES = ("official",)
DEFAULT_MERGE_GAP_TOLERANCE = pd.Timedelta(minutes=5)
EVENT_COLUMNS = [
    "analytical_region",
    "region",
    "started_at_kyiv",
    "finished_at_kyiv",
    "source",
    "level",
]
MERGED_COLUMNS = [
    "analytical_region",
    "region",
    "started_at_kyiv",
    "finished_at_kyiv",
    "duration_seconds",
    "affected_oblast_hours",
]
SPLIT_COLUMNS = ["analytical_region", "region", "date", "affected_hours"]
DAILY_COLUMNS = [
    "region",
    "date",
    "oblast_episode_count",
    "alert_start_count",
    "affected_oblast_hours",
]
NATIONAL_COLUMNS = [
    "date",
    "national_alert_wave_count",
    "national_oblast_episode_count",
    "alert_start_count",
    "affected_oblast_hours",
    "active_oblasts_count",
]
SUMMARY_COLUMNS = [
    "region",
    "oblast_episode_count",
    "alert_start_count",
    "affected_oblast_hours",
    "active_days",
    "first_date",
    "last_date",
]


def prepare_metric_events(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
    sources: str | Iterable[str] | None = DEFAULT_METRIC_SOURCES,
) -> pd.DataFrame:
    """Return clean oblast-level alert intervals for analytical metrics.

    Raw rows can include raion or hromada records that overlap inside the same
    oblast. Dashboard duration metrics therefore start from oblast-normalized
    intervals and later merge overlaps before any daily summation.
    """
    featured = _ensure_featured(frame)
    events = featured.copy()
    events = _drop_duplicate_raw_records(events)
    events["analytical_region"] = _oblast_region(events)
    events["region"] = events["analytical_region"]
    events = _filter_sources(events, sources)

    if not include_unfinished:
        events = events[events["finished_at_kyiv"].notna()].copy()

    finished = events["finished_at_kyiv"].notna()
    if (finished & (events["finished_at_kyiv"] < events["started_at_kyiv"])).any():
        raise ValueError("Alert metric intervals must not have negative duration.")

    for column in ("source", "level"):
        if column not in events.columns:
            events[column] = pd.NA

    events = events[
        events["analytical_region"].notna() & events["started_at_kyiv"].notna()
    ].copy()
    return (
        events[EVENT_COLUMNS]
        .sort_values(
            ["analytical_region", "started_at_kyiv", "finished_at_kyiv"],
            ignore_index=True,
        )
    )


def merge_overlapping_intervals(
    events: pd.DataFrame,
    *,
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> pd.DataFrame:
    """Merge overlapping or near-touching finished intervals within each oblast."""
    if events.empty:
        return pd.DataFrame(columns=MERGED_COLUMNS)

    tolerance = _as_timedelta(merge_gap_tolerance)
    finished = events[events["finished_at_kyiv"].notna()].copy()
    if finished.empty:
        return pd.DataFrame(columns=MERGED_COLUMNS)

    rows = []
    for region, region_events in finished.groupby("analytical_region", dropna=False):
        ordered = region_events.sort_values(["started_at_kyiv", "finished_at_kyiv"])
        current_start = None
        current_end = None

        for event in ordered.itertuples(index=False):
            start = event.started_at_kyiv
            end = event.finished_at_kyiv
            if current_start is None:
                current_start = start
                current_end = end
                continue

            if start <= current_end + tolerance:
                current_end = max(current_end, end)
            else:
                rows.append(_merged_row(region, current_start, current_end))
                current_start = start
                current_end = end

        if current_start is not None:
            rows.append(_merged_row(region, current_start, current_end))

    return pd.DataFrame(rows, columns=MERGED_COLUMNS)


def split_intervals_by_day(merged_intervals: pd.DataFrame) -> pd.DataFrame:
    """Split merged intervals across Kyiv-local calendar dates."""
    if merged_intervals.empty:
        return pd.DataFrame(columns=SPLIT_COLUMNS)

    rows = []
    for interval in merged_intervals.itertuples(index=False):
        rows.extend(
            _split_interval(
                interval.region,
                interval.started_at_kyiv,
                interval.finished_at_kyiv,
            )
        )
    return pd.DataFrame(rows, columns=SPLIT_COLUMNS)


def hourly_weekday_episode_matrix(
    frame: pd.DataFrame,
    region: str | None = None,
    *,
    sources: str | Iterable[str] | None = DEFAULT_METRIC_SOURCES,
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> pd.DataFrame:
    """Return merged episode starts by Kyiv-local weekday and hour."""
    events = prepare_metric_events(frame, sources=sources)
    merged = merge_overlapping_intervals(
        events,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    if region is not None:
        merged = merged[merged["region"] == region].copy()
    if merged.empty:
        return pd.DataFrame(0, index=range(7), columns=range(24))

    starts = merged.copy()
    starts["weekday"] = starts["started_at_kyiv"].dt.weekday
    starts["hour"] = starts["started_at_kyiv"].dt.hour
    matrix = starts.pivot_table(
        index="weekday",
        columns="hour",
        values="started_at_kyiv",
        aggfunc="size",
        fill_value=0,
    )
    return matrix.reindex(index=range(7), columns=range(24), fill_value=0)


def daily_oblast_metrics(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
    sources: str | Iterable[str] | None = DEFAULT_METRIC_SOURCES,
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> pd.DataFrame:
    """Return daily oblast metrics based on starts and merged alert coverage."""
    events = prepare_metric_events(
        frame,
        include_unfinished=include_unfinished,
        sources=sources,
    )
    if events.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    merged = merge_overlapping_intervals(
        events,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    return _daily_oblast_from_merged(
        merged,
        events,
        include_unfinished=include_unfinished,
    )


def _daily_oblast_from_merged(
    merged: pd.DataFrame,
    events: pd.DataFrame,
    *,
    include_unfinished: bool,
) -> pd.DataFrame:
    if merged.empty and events.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    start_counts = _episode_start_counts(merged)
    if include_unfinished:
        unfinished = events[events["finished_at_kyiv"].isna()].copy()
        if not unfinished.empty:
            unfinished["date"] = unfinished["started_at_kyiv"].dt.date
            unfinished_counts = (
                unfinished.groupby(["region", "date"], dropna=False)
                .size()
                .reset_index(name="oblast_episode_count")
            )
            start_counts = pd.concat(
                [start_counts, unfinished_counts],
                ignore_index=True,
            )
            start_counts = (
                start_counts.groupby(["region", "date"], dropna=False)[
                    "oblast_episode_count"
                ]
                .sum()
                .reset_index()
            )

    split = split_intervals_by_day(merged)
    if split.empty:
        duration = pd.DataFrame(columns=["region", "date", "affected_oblast_hours"])
    else:
        duration = (
            split.groupby(["region", "date"], dropna=False)["affected_hours"]
            .sum()
            .reset_index(name="affected_oblast_hours")
        )

    daily = start_counts.merge(duration, on=["region", "date"], how="outer")
    daily["oblast_episode_count"] = daily["oblast_episode_count"].fillna(0).astype(int)
    daily["alert_start_count"] = daily["oblast_episode_count"]
    daily["affected_oblast_hours"] = daily["affected_oblast_hours"].fillna(0.0)
    return daily[DAILY_COLUMNS].sort_values(["region", "date"], ignore_index=True)


def national_daily_metrics(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
    sources: str | Iterable[str] | None = DEFAULT_METRIC_SOURCES,
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> pd.DataFrame:
    """Return national daily totals plus merged national alert waves."""
    events = prepare_metric_events(
        frame,
        include_unfinished=include_unfinished,
        sources=sources,
    )
    if events.empty:
        return pd.DataFrame(columns=NATIONAL_COLUMNS)

    merged = merge_overlapping_intervals(
        events,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    daily = _daily_oblast_from_merged(merged, events, include_unfinished=include_unfinished)
    return _national_from_daily(daily, merged, merge_gap_tolerance=merge_gap_tolerance)


def regional_metric_summary(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
    sources: str | Iterable[str] | None = DEFAULT_METRIC_SOURCES,
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> pd.DataFrame:
    """Return region-level totals based on alert starts and merged coverage."""
    daily = daily_oblast_metrics(
        frame,
        include_unfinished=include_unfinished,
        sources=sources,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    return _regional_summary_from_daily(daily)


def build_metric_tables(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
    sources: str | Iterable[str] | None = DEFAULT_METRIC_SOURCES,
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build daily oblast, national daily, and regional summary tables once."""
    events = prepare_metric_events(
        frame,
        include_unfinished=include_unfinished,
        sources=sources,
    )
    merged = merge_overlapping_intervals(
        events,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    daily = _daily_oblast_from_merged(merged, events, include_unfinished=include_unfinished)
    return (
        daily,
        _national_from_daily(daily, merged, merge_gap_tolerance=merge_gap_tolerance),
        _regional_summary_from_daily(daily),
    )


def debug_region_day_metrics(
    frame: pd.DataFrame,
    region: str,
    date,
    *,
    source: str | Iterable[str] | None = "official",
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> dict[str, object]:
    """Return compact diagnostics for one oblast/date metric calculation."""
    target_date = pd.to_datetime(date).date()
    day_start = pd.Timestamp(target_date).tz_localize(KYIV_TIMEZONE)
    day_end = pd.Timestamp(target_date + timedelta(days=1)).tz_localize(KYIV_TIMEZONE)
    featured = _ensure_featured(frame)
    source_values = _normalize_sources(source)
    raw = featured.copy()
    if source_values is not None and "source" in raw.columns:
        raw = raw[raw["source"].isin(source_values)].copy()
    raw["analytical_region"] = _oblast_region(raw)
    raw_overlaps_day = (raw["started_at_kyiv"] < day_end) & (
        raw["finished_at_kyiv"].isna() | (raw["finished_at_kyiv"] > day_start)
    )
    raw_day = raw[
        (raw["analytical_region"] == region)
        & raw_overlaps_day
    ].copy()
    duplicate_raw_records_count = _duplicate_raw_records_count(raw_day)

    events = prepare_metric_events(featured, sources=source_values)
    region_events = events[events["region"] == region].copy()
    event_overlaps_day = (region_events["started_at_kyiv"] < day_end) & (
        region_events["finished_at_kyiv"].isna()
        | (region_events["finished_at_kyiv"] > day_start)
    )
    merged = merge_overlapping_intervals(
        region_events,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    merged_for_day = merged[
        (merged["started_at_kyiv"] < day_end)
        & (merged["finished_at_kyiv"] > day_start)
    ].copy()
    daily = daily_oblast_metrics(
        featured,
        sources=source_values,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    daily_row = daily[(daily["region"] == region) & (daily["date"] == target_date)]

    if daily_row.empty:
        alert_start_count = 0
        affected_hours = 0.0
    else:
        alert_start_count = int(daily_row["alert_start_count"].sum())
        affected_hours = float(daily_row["affected_oblast_hours"].sum())

    return {
        "raw_records_count": int(len(raw_day)),
        "duplicate_raw_records_count": duplicate_raw_records_count,
        "prepared_intervals_count": int(
            len(region_events[event_overlaps_day])
        ),
        "merged_intervals_count": int(len(merged_for_day)),
        "alert_start_count": alert_start_count,
        "oblast_episode_count": alert_start_count,
        "affected_oblast_hours": affected_hours,
        "sources_present": sorted(raw_day["source"].dropna().astype(str).unique().tolist())
        if "source" in raw_day.columns
        else [],
        "levels_present": sorted(raw_day["level"].dropna().astype(str).unique().tolist())
        if "level" in raw_day.columns
        else [],
        "first_raw_rows": raw_day.head(5).to_dict("records"),
        "merged_intervals_for_that_day": merged_for_day.to_dict("records"),
    }


def debug_national_day_metrics(
    frame: pd.DataFrame,
    date,
    *,
    source: str | Iterable[str] | None = "official",
    merge_gap_tolerance: pd.Timedelta | str | int | float = DEFAULT_MERGE_GAP_TOLERANCE,
) -> dict[str, object]:
    """Return compact national diagnostics for one Kyiv-local date."""
    target_date = pd.to_datetime(date).date()
    featured = _ensure_featured(frame)
    source_values = _normalize_sources(source)
    raw = featured.copy()
    if source_values is not None and "source" in raw.columns:
        raw = raw[raw["source"].isin(source_values)].copy()
    day_start = pd.Timestamp(target_date).tz_localize(KYIV_TIMEZONE)
    day_end = pd.Timestamp(target_date + timedelta(days=1)).tz_localize(KYIV_TIMEZONE)
    raw_day = raw[
        (raw["started_at_kyiv"] < day_end)
        & (raw["finished_at_kyiv"].isna() | (raw["finished_at_kyiv"] > day_start))
    ].copy()

    events = prepare_metric_events(featured, sources=source_values)
    merged = merge_overlapping_intervals(
        events,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    daily = _daily_oblast_from_merged(merged, events, include_unfinished=False)
    national = _national_from_daily(
        daily,
        merged,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    row = national[national["date"] == target_date]

    if row.empty:
        values = {
            "national_oblast_episode_count": 0,
            "national_alert_wave_count": 0,
            "affected_oblast_hours": 0.0,
            "active_oblasts_count": 0,
        }
    else:
        values = row.iloc[0].to_dict()

    return {
        "date": target_date,
        "raw_records_count": int(len(raw_day)),
        "duplicate_raw_records_count": _duplicate_raw_records_count(raw_day),
        "oblast_episode_starts": int(values["national_oblast_episode_count"]),
        "national_alert_waves": int(values["national_alert_wave_count"]),
        "affected_oblast_hours": float(values["affected_oblast_hours"]),
        "active_oblasts_count": int(values["active_oblasts_count"]),
    }


def _national_from_daily(
    daily: pd.DataFrame,
    merged: pd.DataFrame,
    *,
    merge_gap_tolerance: pd.Timedelta | str | int | float,
) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=NATIONAL_COLUMNS)
    national = (
        daily.groupby("date", dropna=False)
        .agg(
            national_oblast_episode_count=("oblast_episode_count", "sum"),
            affected_oblast_hours=("affected_oblast_hours", "sum"),
            active_oblasts_count=("region", "nunique"),
        )
        .reset_index()
        .sort_values("date", ignore_index=True)
    )
    national_waves = _national_alert_wave_counts(
        merged,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    national = national.merge(national_waves, on="date", how="outer")
    national["national_oblast_episode_count"] = (
        national["national_oblast_episode_count"].fillna(0).astype(int)
    )
    national["national_alert_wave_count"] = (
        national["national_alert_wave_count"].fillna(0).astype(int)
    )
    national["alert_start_count"] = national["national_oblast_episode_count"]
    national["affected_oblast_hours"] = national["affected_oblast_hours"].fillna(0.0)
    national["active_oblasts_count"] = national["active_oblasts_count"].fillna(0).astype(int)
    return national[NATIONAL_COLUMNS].sort_values("date", ignore_index=True)


def _regional_summary_from_daily(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    summary = (
        daily.groupby("region", dropna=False)
        .agg(
            oblast_episode_count=("oblast_episode_count", "sum"),
            affected_oblast_hours=("affected_oblast_hours", "sum"),
            active_days=("date", "nunique"),
            first_date=("date", "min"),
            last_date=("date", "max"),
        )
        .reset_index()
    )
    summary["alert_start_count"] = summary["oblast_episode_count"]
    return summary[SUMMARY_COLUMNS].sort_values(
        "affected_oblast_hours",
        ascending=False,
        ignore_index=True,
    )


def _episode_start_counts(merged: pd.DataFrame) -> pd.DataFrame:
    if merged.empty:
        return pd.DataFrame(columns=["region", "date", "oblast_episode_count"])
    starts = merged.copy()
    starts["date"] = starts["started_at_kyiv"].dt.date
    return (
        starts.groupby(["region", "date"], dropna=False)
        .size()
        .reset_index(name="oblast_episode_count")
    )


def _national_alert_wave_counts(
    merged: pd.DataFrame,
    *,
    merge_gap_tolerance: pd.Timedelta | str | int | float,
) -> pd.DataFrame:
    if merged.empty:
        return pd.DataFrame(columns=["date", "national_alert_wave_count"])
    national_events = merged.copy()
    national_events["analytical_region"] = "National"
    national_events["region"] = "National"
    national_merged = merge_overlapping_intervals(
        national_events,
        merge_gap_tolerance=merge_gap_tolerance,
    )
    if national_merged.empty:
        return pd.DataFrame(columns=["date", "national_alert_wave_count"])
    national_merged["date"] = national_merged["started_at_kyiv"].dt.date
    return (
        national_merged.groupby("date", dropna=False)
        .size()
        .reset_index(name="national_alert_wave_count")
    )


def _drop_duplicate_raw_records(frame: pd.DataFrame) -> pd.DataFrame:
    duplicate_columns = _duplicate_columns(frame)
    if not duplicate_columns:
        return frame.copy()
    return frame.drop_duplicates(subset=duplicate_columns, keep="first").copy()


def _duplicate_raw_records_count(frame: pd.DataFrame) -> int:
    duplicate_columns = _duplicate_columns(frame)
    if not duplicate_columns:
        return 0
    return int(frame.duplicated(subset=duplicate_columns, keep="first").sum())


def _duplicate_columns(frame: pd.DataFrame) -> list[str]:
    stable_columns = ["source", "oblast", "raion", "hromada", "level", "started_at", "finished_at"]
    if "oblast" not in frame.columns:
        stable_columns.insert(1, "region")
    return [column for column in stable_columns if column in frame.columns]


def _ensure_featured(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"started_at_kyiv", "finished_at_kyiv", "region", "is_finished"}
    return frame.copy() if required.issubset(frame.columns) else add_historical_features(frame)


def _filter_sources(
    frame: pd.DataFrame,
    sources: str | Iterable[str] | None,
) -> pd.DataFrame:
    source_values = _normalize_sources(sources)
    if source_values is None or "source" not in frame.columns:
        return frame.copy()
    return frame[frame["source"].isin(source_values)].copy()


def _normalize_sources(sources: str | Iterable[str] | None) -> tuple[str, ...] | None:
    if sources is None:
        return None
    if isinstance(sources, str):
        return (sources,)
    return tuple(sources)


def _as_timedelta(value: pd.Timedelta | str | int | float) -> pd.Timedelta:
    if isinstance(value, pd.Timedelta):
        return value
    if isinstance(value, (int, float)):
        return pd.Timedelta(minutes=value)
    return pd.Timedelta(value)


def _oblast_region(frame: pd.DataFrame) -> pd.Series:
    candidates = [
        column
        for column in ("oblast", "region", "location_title")
        if column in frame.columns
    ]
    if not candidates:
        return frame["region"].astype("string").str.strip()

    region = _clean_text(frame[candidates[0]])
    for column in candidates[1:]:
        region = region.combine_first(_clean_text(frame[column]))
    return region


def _clean_text(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned == "")


def _merged_row(region: object, start, end) -> dict[str, object]:
    duration_seconds = (end - start).total_seconds()
    return {
        "analytical_region": region,
        "region": region,
        "started_at_kyiv": start,
        "finished_at_kyiv": end,
        "duration_seconds": duration_seconds,
        "affected_oblast_hours": duration_seconds / 3600,
    }


def _split_interval(region: object, start, end) -> list[dict[str, object]]:
    rows = []
    current = start
    while current < end:
        next_date = current.date() + timedelta(days=1)
        next_midnight = pd.Timestamp(next_date).tz_localize(KYIV_TIMEZONE)
        segment_end = min(end, next_midnight)
        seconds = (segment_end - current).total_seconds()
        if seconds > 0:
            rows.append(
                {
                    "analytical_region": region,
                    "region": region,
                    "date": current.date(),
                    "affected_hours": seconds / 3600,
                }
            )
        current = segment_end
    return rows
