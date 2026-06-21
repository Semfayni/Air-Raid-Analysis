"""Overview page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from air_alerts.dashboard import (
    overview_kpis,
    top_regions_by_alert_count,
    top_regions_by_duration,
)
from air_alerts.data import HistoricalDataError, HistoricalSchemaError
from air_alerts.features import daily_alert_count, daily_alert_duration
from air_alerts.pages.data_cache import load_featured_historical_data
from air_alerts.ui import PRIMARY_COLOR, compact_note, page_header, section, style_figure


def render() -> None:
    """Render the historical dashboard overview."""
    page_header(
        "Ukraine Air Alert Intelligence Dashboard",
        "Historical air alert patterns, regional comparisons, and exploratory signals.",
    )
    compact_note("Historical views use the CSV dataset. Live API calls are limited to the Live Map page.")

    try:
        with st.spinner("Loading historical alert data..."):
            featured = load_featured_historical_data()
    except (HistoricalDataError, HistoricalSchemaError, ValueError) as exc:
        st.error(f"Historical data could not be loaded: {exc}")
        return

    completed = featured[featured["is_finished"]]
    if completed.empty:
        st.warning("No completed historical alerts are available for overview metrics.")
        return

    kpis = overview_kpis(featured)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Alerts", f"{kpis.total_alerts:,}")
    col2.metric("Total Alert Hours", f"{kpis.total_alert_hours:,.0f}")
    col3.metric("Date Range", kpis.date_range)
    col4.metric("Most Affected Region", kpis.most_affected_region)

    with st.expander("Methodology note"):
        st.write(
            "Timestamps are converted from UTC to Kyiv local time for daily aggregation. "
            "Default summaries use completed alerts, so rows without a finish time do not "
            "inflate duration-based metrics."
        )

    daily_counts = daily_alert_count(featured)
    daily_duration = daily_alert_duration(featured)
    daily_duration["duration_hours"] = daily_duration["duration_minutes"] / 60

    section("National Trends", "Daily count and total duration across all regions.")
    trend_left, trend_right = st.columns(2)
    with trend_left:
        count_figure = px.line(
            daily_counts,
            x="date",
            y="alert_count",
            title="Daily Alert Count",
            labels={"alert_count": "Alerts", "date": "Date"},
            color_discrete_sequence=[PRIMARY_COLOR],
        )
        st.plotly_chart(style_figure(count_figure, height=360), width="stretch")
    with trend_right:
        duration_figure = px.line(
            daily_duration,
            x="date",
            y="duration_hours",
            title="Daily Alert Hours",
            labels={"duration_hours": "Alert hours", "date": "Date"},
            color_discrete_sequence=["#8a3ffc"],
        )
        st.plotly_chart(style_figure(duration_figure, height=360), width="stretch")

    section("Regional Concentration", "Regions with the largest historical alert load.")
    left, right = st.columns(2)
    with left:
        top_count = top_regions_by_alert_count(featured)
        figure = px.bar(
            top_count,
            x="alert_count",
            y="region",
            title="Top Regions by Alert Count",
            orientation="h",
            labels={"alert_count": "Alerts", "region": "Region"},
            color_discrete_sequence=[PRIMARY_COLOR],
        ).update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(style_figure(figure, height=420), width="stretch")
    with right:
        top_duration = top_regions_by_duration(featured)
        figure = px.bar(
            top_duration,
            x="total_duration_hours",
            y="region",
            title="Top Regions by Total Duration",
            orientation="h",
            labels={"total_duration_hours": "Alert hours", "region": "Region"},
            color_discrete_sequence=["#6f4e37"],
        ).update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(style_figure(figure, height=420), width="stretch")
