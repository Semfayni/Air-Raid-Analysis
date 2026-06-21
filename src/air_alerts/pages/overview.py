"""Overview page."""

from __future__ import annotations

import streamlit as st

from air_alerts.data.sources import HISTORICAL_DATASET_URL, LIVE_ALERTS_API_URL


def render() -> None:
    """Render the dashboard overview placeholder."""
    st.title("Ukraine Air Alert Intelligence Dashboard")
    st.caption("Exploratory analysis and visualization. Not an attack prediction tool.")

    st.info(
        "This scaffold is ready for historical time-series analysis, live status display, "
        "and holiday/date-aware anomaly exploration."
    )

    st.subheader("Planned sources")
    st.markdown(
        f"- Historical dataset: [{HISTORICAL_DATASET_URL}]({HISTORICAL_DATASET_URL})\n"
        f"- Live alerts API: [{LIVE_ALERTS_API_URL}]({LIVE_ALERTS_API_URL})"
    )

    st.subheader("Planned modules")
    st.write(
        "Overview metrics, live map status, regional time-series exploration, anomaly lab, "
        "and a transparent AI process page."
    )
