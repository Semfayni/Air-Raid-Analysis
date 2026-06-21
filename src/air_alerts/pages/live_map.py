"""Live map page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from air_alerts.live_api import AlertsApiError, get_air_raid_statuses_by_oblast
from air_alerts.map_viz import (
    DEFAULT_GEOJSON_PATH,
    build_live_status_choropleth,
    prepare_live_map_data,
    status_summary,
)
from air_alerts.ui import compact_note, page_header, section


@st.cache_data(ttl=60, show_spinner=False)
def _load_live_statuses() -> pd.DataFrame:
    return get_air_raid_statuses_by_oblast()


def render() -> None:
    """Render the live alerts map page."""
    page_header(
        "Live Alerts Map",
        "Current alerts.in.ua oblast status for map monitoring.",
    )
    compact_note("Use official channels for safety decisions. Status data is cached for about 60 seconds.")

    try:
        statuses = _load_live_statuses()
    except AlertsApiError as exc:
        st.error(f"Live alert status is unavailable: {exc}")
        return

    map_result = prepare_live_map_data(statuses)
    summary = status_summary(statuses)
    summary_lookup = dict(zip(summary["status_label"], summary["oblast_count"]))

    if map_result.geojson_missing:
        with st.container(border=True):
            compact_note(
                "Map geometry is unavailable. Live statuses are shown in the table below.",
                kind="warning",
            )
            st.caption(f"Expected GeoJSON path: `{DEFAULT_GEOJSON_PATH}`")
            metric_cols = st.columns(4)
            metric_cols[0].metric("Active", int(summary_lookup.get("Active alert", 0)))
            metric_cols[1].metric("Partial", int(summary_lookup.get("Partial alert", 0)))
            metric_cols[2].metric("No Alert", int(summary_lookup.get("No alert", 0)))
            metric_cols[3].metric("Unknown", int(summary_lookup.get("Unknown", 0)))
            st.dataframe(
                map_result.statuses[["oblast", "status_label", "status_code", "is_active"]],
                width="stretch",
                hide_index=True,
            )
        return

    section("Current Status Map", "Red and amber regions have active or partial alert status.")
    figure = build_live_status_choropleth(map_result)
    st.plotly_chart(figure, width="stretch")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Active", int(summary_lookup.get("Active alert", 0)))
    metric_cols[1].metric("Partial", int(summary_lookup.get("Partial alert", 0)))
    metric_cols[2].metric("No Alert", int(summary_lookup.get("No alert", 0)))
    metric_cols[3].metric("Unknown", int(summary_lookup.get("Unknown", 0)))

    if map_result.unmatched_geojson_regions:
        st.warning(
            "Some GeoJSON region names did not match live status names: "
            + ", ".join(map_result.unmatched_geojson_regions)
        )

    section("Status Summary")
    st.dataframe(summary, width="stretch", hide_index=True)
