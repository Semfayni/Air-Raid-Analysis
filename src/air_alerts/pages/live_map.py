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


@st.cache_data(ttl=60, show_spinner=False)
def _load_live_statuses() -> pd.DataFrame:
    return get_air_raid_statuses_by_oblast()


def render() -> None:
    """Render the live alerts map page."""
    st.title("Live Alerts Map")
    st.caption("Current alerts.in.ua oblast status. Use official channels for safety decisions.")
    st.info("Refresh the page to request the latest status. Results are cached for about 60 seconds.")

    try:
        statuses = _load_live_statuses()
    except AlertsApiError as exc:
        st.error(f"Live alert status is unavailable: {exc}")
        return

    map_result = prepare_live_map_data(statuses)

    if map_result.geojson_missing:
        st.warning(
            "Map geometry is not available yet. Place a Ukraine oblast GeoJSON file at "
            f"`{DEFAULT_GEOJSON_PATH}` to enable the choropleth map."
        )
        st.dataframe(
            map_result.statuses[["oblast", "status_label", "status_code", "is_active"]],
            width="stretch",
            hide_index=True,
        )
        return

    figure = build_live_status_choropleth(map_result)
    st.plotly_chart(figure, width="stretch")

    if map_result.unmatched_geojson_regions:
        st.warning(
            "Some GeoJSON region names did not match live status names: "
            + ", ".join(map_result.unmatched_geojson_regions)
        )

    st.subheader("Status Summary")
    st.dataframe(status_summary(statuses), width="stretch", hide_index=True)
