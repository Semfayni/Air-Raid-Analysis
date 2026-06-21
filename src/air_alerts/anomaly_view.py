"""Pure helpers for the Streamlit anomaly lab page."""

from __future__ import annotations

import pandas as pd


TOP_ANOMALY_COLUMNS = [
    "date",
    "region",
    "oblast_episode_count",
    "affected_oblast_hours",
    "z_score",
    "nearest_holiday_name",
    "days_to_nearest_holiday",
    "explanation",
]


def top_anomalies(anomalies: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    """Return the highest-scoring anomaly rows for display."""
    if anomalies.empty:
        return pd.DataFrame(columns=TOP_ANOMALY_COLUMNS)
    top = anomalies[anomalies["is_anomaly"]].copy()
    if top.empty:
        return pd.DataFrame(columns=TOP_ANOMALY_COLUMNS)
    top = top.sort_values(["z_score", "oblast_episode_count"], ascending=False).head(limit)
    return top[TOP_ANOMALY_COLUMNS].reset_index(drop=True)


def holiday_window_comparison(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Count anomaly rows inside and outside the selected holiday window."""
    anomaly_rows = anomalies[anomalies["is_anomaly"]].copy()
    if anomaly_rows.empty:
        return pd.DataFrame(columns=["holiday_window", "anomaly_count"])

    anomaly_rows["holiday_window"] = anomaly_rows["is_holiday_window"].map(
        {True: "Inside holiday window", False: "Outside holiday window"}
    )
    return (
        anomaly_rows.groupby("holiday_window", dropna=False)
        .size()
        .reset_index(name="anomaly_count")
        .sort_values("holiday_window", ignore_index=True)
    )


def nearby_holiday_frequency(anomalies: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Count the most frequent nearest holidays among anomaly rows."""
    anomaly_rows = anomalies[anomalies["is_anomaly"]].copy()
    if anomaly_rows.empty:
        return pd.DataFrame(columns=["nearest_holiday_name", "anomaly_count"])

    return (
        anomaly_rows.groupby("nearest_holiday_name", dropna=False)
        .size()
        .reset_index(name="anomaly_count")
        .sort_values("anomaly_count", ascending=False, ignore_index=True)
        .head(limit)
    )
