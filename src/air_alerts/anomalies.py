"""Explainable anomaly backend for daily regional alert activity."""

from __future__ import annotations

import math

import pandas as pd

from air_alerts.features import add_historical_features
from air_alerts.holidays import add_holiday_proximity_features


DEFAULT_ROLLING_WINDOW_DAYS = 30
DEFAULT_MIN_PERIODS = 14
DEFAULT_Z_THRESHOLD = 2.0
ROBUST_Z_SCALE = 1.4826
OUTPUT_COLUMNS = [
    "date",
    "region",
    "alert_count",
    "total_duration_hours",
    "average_duration_hours",
    "anomaly_score",
    "z_score",
    "is_anomaly",
    "nearest_holiday_name",
    "nearest_holiday_date",
    "days_to_nearest_holiday",
    "is_holiday_window",
    "explanation",
]


class AnomalyAnalysisError(ValueError):
    """Raised when anomaly analysis inputs are incomplete."""


def build_daily_region_timeseries(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
) -> pd.DataFrame:
    """Build a daily region-level activity table from historical alert rows."""
    featured = _ensure_featured(frame)
    if not include_unfinished:
        featured = featured[featured["is_finished"]]

    if featured.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "region",
                "alert_count",
                "total_duration_hours",
                "average_duration_hours",
            ]
        )

    daily = (
        featured.groupby(["date", "region"], dropna=False)
        .agg(
            alert_count=("started_at", "size"),
            total_duration_hours=("duration_hours", "sum"),
            average_duration_hours=("duration_hours", "mean"),
        )
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"]).dt.date
    daily["total_duration_hours"] = daily["total_duration_hours"].fillna(0.0)
    daily["average_duration_hours"] = daily["average_duration_hours"].fillna(0.0)

    return _fill_missing_region_dates(daily)


def detect_daily_anomalies(
    frame: pd.DataFrame,
    *,
    include_unfinished: bool = False,
    rolling_window: int = DEFAULT_ROLLING_WINDOW_DAYS,
    min_periods: int = DEFAULT_MIN_PERIODS,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
    holiday_window_days: int = 2,
) -> pd.DataFrame:
    """Score unusual daily regional activity and add nearby holiday context.

    Scores are transparent exploratory signals for review. They are not forecasts
    and should be interpreted as records worth inspecting alongside the source data.
    """
    _validate_scoring_parameters(rolling_window, min_periods, z_threshold)

    daily = build_daily_region_timeseries(
        frame,
        include_unfinished=include_unfinished,
    )
    if daily.empty:
        empty = daily.copy()
        for column in OUTPUT_COLUMNS:
            if column not in empty.columns:
                empty[column] = pd.Series(dtype="object")
        return empty[OUTPUT_COLUMNS]

    scored = _score_regions(
        daily,
        rolling_window=rolling_window,
        min_periods=min_periods,
    )
    scored["is_anomaly"] = scored["z_score"] >= z_threshold

    with_holidays = add_holiday_proximity_features(
        scored,
        date_column="date",
        holiday_window_days=holiday_window_days,
    )
    with_holidays["explanation"] = with_holidays.apply(_build_explanation, axis=1)
    return with_holidays[OUTPUT_COLUMNS]


def _ensure_featured(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "date",
        "region",
        "duration_hours",
        "is_finished",
        "started_at",
    }
    return frame.copy() if required.issubset(frame.columns) else add_historical_features(frame)


def _fill_missing_region_dates(daily: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for region, region_frame in daily.groupby("region", dropna=False):
        indexed = region_frame.set_index(pd.to_datetime(region_frame["date"]))
        date_index = pd.date_range(indexed.index.min(), indexed.index.max(), freq="D")
        filled = indexed.reindex(date_index)
        filled["date"] = date_index.date
        filled["region"] = region
        filled["alert_count"] = filled["alert_count"].fillna(0).astype(int)
        filled["total_duration_hours"] = filled["total_duration_hours"].fillna(0.0)
        filled["average_duration_hours"] = filled["average_duration_hours"].fillna(0.0)
        frames.append(filled.reset_index(drop=True))

    return pd.concat(frames, ignore_index=True).sort_values(
        ["region", "date"],
        ignore_index=True,
    )


def _score_regions(
    daily: pd.DataFrame,
    *,
    rolling_window: int,
    min_periods: int,
) -> pd.DataFrame:
    scored_frames = []
    for region, region_frame in daily.groupby("region", dropna=False):
        scored = _score_region(
            region_frame,
            rolling_window=rolling_window,
            min_periods=min_periods,
        )
        scored["region"] = region
        scored_frames.append(scored)

    return pd.concat(scored_frames, ignore_index=True)


def _score_region(
    region_frame: pd.DataFrame,
    *,
    rolling_window: int,
    min_periods: int,
) -> pd.DataFrame:
    scored = region_frame.sort_values("date").copy()
    count_signal = _normalize_series(scored["alert_count"])
    duration_signal = _normalize_series(scored["total_duration_hours"])
    scored["anomaly_score"] = (count_signal + duration_signal) / 2
    scored["z_score"] = _rolling_z_score(
        scored["anomaly_score"],
        rolling_window=rolling_window,
        min_periods=min_periods,
    )
    return scored


def _normalize_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)
    median = numeric.median()
    mad = (numeric - median).abs().median()
    if _is_stable_scale(mad):
        return (numeric - median) / (ROBUST_Z_SCALE * mad)

    mean = numeric.mean()
    std = numeric.std(ddof=0)
    if _is_stable_scale(std):
        return (numeric - mean) / std

    return pd.Series(0.0, index=series.index)


def _rolling_z_score(
    series: pd.Series,
    *,
    rolling_window: int,
    min_periods: int,
) -> pd.Series:
    baseline = series.shift(1)
    rolling = baseline.rolling(
        window=rolling_window,
        min_periods=min_periods,
    )
    median = rolling.median()
    mad = rolling.apply(_median_absolute_deviation, raw=False)
    mean = rolling.mean()
    std = rolling.std(ddof=0)

    robust_scale = ROBUST_Z_SCALE * mad
    robust_z = (series - median) / robust_scale
    standard_z = (series - mean) / std
    flat_baseline_z = (series - median).abs() / _fallback_scale(series)

    z_score = robust_z.where(_stable_scale_mask(robust_scale), standard_z)
    z_score = z_score.where(
        _stable_scale_mask(robust_scale) | _stable_scale_mask(std),
        flat_baseline_z,
    )
    return z_score.replace([float("inf"), float("-inf")], 0.0).fillna(0.0).clip(lower=0.0)


def _median_absolute_deviation(series: pd.Series) -> float:
    median = series.median()
    return float((series - median).abs().median())


def _stable_scale_mask(series: pd.Series) -> pd.Series:
    return series.notna() & (series > 1e-12)


def _is_stable_scale(value: float) -> bool:
    return value is not None and not math.isnan(value) and value > 1e-12


def _fallback_scale(series: pd.Series) -> float:
    nonzero_values = pd.to_numeric(series, errors="coerce").abs()
    nonzero_values = nonzero_values[nonzero_values > 1e-12]
    if nonzero_values.empty:
        return 1.0
    return max(float(nonzero_values.median()), 1.0)


def _build_explanation(row: pd.Series) -> str:
    status = "unusual activity" if row["is_anomaly"] else "typical activity"
    inspection = "worth inspecting" if row["is_anomaly"] else "baseline context"
    holiday_text = (
        f"coincides with the holiday window for {row['nearest_holiday_name']}"
        if row["is_holiday_window"]
        else f"nearest date marker is {row['nearest_holiday_name']}"
    )
    return (
        f"{row['region']} on {row['date']}: {status} "
        f"(score {row['z_score']:.2f}); {holiday_text}; {inspection}."
    )


def _validate_scoring_parameters(
    rolling_window: int,
    min_periods: int,
    z_threshold: float,
) -> None:
    if rolling_window < 2:
        raise AnomalyAnalysisError("rolling_window must be at least 2.")
    if min_periods < 1:
        raise AnomalyAnalysisError("min_periods must be at least 1.")
    if min_periods > rolling_window:
        raise AnomalyAnalysisError("min_periods must be less than or equal to rolling_window.")
    if z_threshold < 0:
        raise AnomalyAnalysisError("z_threshold must be zero or greater.")
