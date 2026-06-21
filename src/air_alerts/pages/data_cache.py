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
    return build_metric_tables(featured)
