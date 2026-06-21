"""Shared Streamlit cache helpers for historical pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from air_alerts.data import load_historical_alerts
from air_alerts.features import add_historical_features


@st.cache_data(show_spinner="Loading historical alert data...")
def load_featured_historical_data() -> pd.DataFrame:
    """Load historical alerts and add analysis features once per Streamlit session."""
    raw = load_historical_alerts()
    return add_historical_features(raw)
