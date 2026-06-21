"""Anomaly lab page."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the anomaly lab placeholder."""
    st.title("Anomaly Lab")
    st.caption("Future exploratory workflows for alerts around holidays and important dates.")

    st.info(
        "Planned: compare historical alert patterns around Ukrainian holidays, memorial dates, "
        "and major public events without claiming predictive power."
    )
