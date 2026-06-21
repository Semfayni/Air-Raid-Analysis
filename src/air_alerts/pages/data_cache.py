"""Shared Streamlit cache helpers for historical pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from air_alerts.data import load_historical_alerts
from air_alerts.features import add_historical_features
from air_alerts.metrics import build_metric_tables


METRIC_CACHE_SCHEMA_VERSION = "metric-schema-v2-national-waves"


@st.cache_data(show_spinner="Loading historical alert data...")
def load_featured_historical_data() -> pd.DataFrame:
    """Load historical alerts and add analysis features once per Streamlit session."""
    raw = load_historical_alerts()
    return add_historical_features(raw)


@st.cache_data(show_spinner="Computing oblast-level alert metrics...")
def load_historical_metric_tables(
    schema_version: str = METRIC_CACHE_SCHEMA_VERSION,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return cached daily oblast, national daily, and regional metric tables."""
    _ = schema_version
    featured = load_featured_historical_data()
    daily, national, regional = build_metric_tables(featured)

    # Ensure returned tables have stable schemas so downstream pages don't KeyError
    # when an older cache or partial computation omitted newly added columns.
    if not daily.empty:
        for col in ("region", "date", "oblast_episode_count", "alert_start_count", "affected_oblast_hours"):
            if col not in daily.columns:
                if col in ("oblast_episode_count", "alert_start_count"):
                    daily[col] = 0
                elif col == "affected_oblast_hours":
                    daily[col] = 0.0
                else:
                    daily[col] = pd.NA
        daily = daily[["region", "date", "oblast_episode_count", "alert_start_count", "affected_oblast_hours"]]

    if not national.empty:
        for col in (
            "date",
            "national_alert_wave_count",
            "national_oblast_episode_count",
            "alert_start_count",
            "affected_oblast_hours",
            "active_oblasts_count",
        ):
            if col not in national.columns:
                if col in ("national_alert_wave_count", "national_oblast_episode_count", "alert_start_count", "active_oblasts_count"):
                    national[col] = 0
                elif col == "affected_oblast_hours":
                    national[col] = 0.0
                else:
                    national[col] = pd.NA
        national = national[["date", "national_alert_wave_count", "national_oblast_episode_count", "alert_start_count", "affected_oblast_hours", "active_oblasts_count"]]

    if not regional.empty:
        for col in ("region", "oblast_episode_count", "alert_start_count", "affected_oblast_hours", "active_days", "first_date", "last_date"):
            if col not in regional.columns:
                if col in ("oblast_episode_count", "alert_start_count", "active_days"):
                    regional[col] = 0
                elif col == "affected_oblast_hours":
                    regional[col] = 0.0
                else:
                    regional[col] = pd.NA
        regional = regional[["region", "oblast_episode_count", "alert_start_count", "affected_oblast_hours", "active_days", "first_date", "last_date"]]

    return daily, national, regional
