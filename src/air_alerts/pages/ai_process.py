"""AI process transparency page."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render AI-assisted development process notes."""
    st.title("AI Process")
    st.caption("How the project was planned, tested, corrected, and kept exploratory.")

    st.warning(
        "This project supports exploratory analysis and visualization. It is not an "
        "operational warning tool and does not attempt to predict attacks."
    )

    st.subheader("Data Boundary")
    st.write(
        "Historical analysis uses the public CSV dataset because it is reproducible, testable, "
        "and appropriate for time-series exploration. The alerts.in.ua API is used only for "
        "current live status, where freshness matters and an API token can be kept outside code."
    )

    st.subheader("Exploratory Framing")
    st.write(
        "The anomaly lab looks for unusual daily alert activity relative to a rolling baseline. "
        "Holiday proximity is added as context for inspection, not as evidence that one event "
        "explains another."
    )

    st.subheader("Pipeline")
    st.markdown(
        "- Historical data loading: read official and volunteer CSV files, validate schema, and parse UTC timestamps.\n"
        "- Kyiv timezone feature engineering: preserve UTC columns and add Kyiv-local calendar fields for daily analysis.\n"
        "- Holiday proximity features: build Ukrainian public holiday and important-date calendars by year.\n"
        "- Rolling anomaly detection: score daily region activity with count and duration against a rolling baseline.\n"
        "- Live map status: read compact current oblast statuses from alerts.in.ua through a token-safe client.\n"
        "- Streamlit dashboard: expose overview, regional explorer, live map, anomaly lab, and process notes."
    )

    st.subheader("AI Mistakes and Corrections")
    st.markdown(
        "- Streamlit navigation initially generated duplicate page paths because each page callable was named `render`. "
        "The crash exposed the issue, and explicit `url_path` values made every page route stable.\n"
        "- A historical loader test expected exactly `datetime64[ns, UTC]`. Local pandas returned another valid precision, "
        "so the test was changed to check timezone-aware UTC datetime behavior instead of a brittle string.\n"
        "- The anomaly backend lost `region` after a pandas `groupby.apply` step. Failing tests found the missing column, "
        "and the fix changed scoring to an explicit per-region loop that preserves the region value.\n"
        "- The map layer assumed optional `oblast_index` existed, then represented unmatched GeoJSON rows with `NaN` "
        "where `None` was expected. Tests drove a schema-tolerant join and explicit missing-value normalization."
    )

    st.subheader("Prompt Log")
    st.write(
        "The `prompts/` directory contains short stage summaries and placeholders where real prompts, outputs, "
        "or screenshots can be added for KSE submission. It is support material, not a full chat export."
    )
