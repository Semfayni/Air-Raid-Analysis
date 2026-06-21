"""Live map page."""

from __future__ import annotations

import streamlit as st

from air_alerts.config import load_settings


def render() -> None:
    """Render the live map placeholder."""
    settings = load_settings()

    st.title("Live Alerts Map")
    st.caption("Live status visualization scaffold. No API calls are made yet.")

    if settings.alerts_api_token:
        st.success("Alerts API token detected in environment configuration.")
    else:
        st.warning("No Alerts API token found. Add ALERTS_API_TOKEN to your local .env file.")

    st.empty().info("Future work: fetch live regional alert status and render an interactive map.")
