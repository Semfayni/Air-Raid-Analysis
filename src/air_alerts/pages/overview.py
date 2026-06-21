"""Overview page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from air_alerts.data import HistoricalDataError, HistoricalSchemaError
from air_alerts.pages.data_cache import (
    load_featured_historical_data,
    load_historical_metric_tables,
)
from air_alerts.ui import PRIMARY_COLOR, SECONDARY_COLOR, compact_note, page_header, section, style_figure


def render() -> None:
    """Render the historical dashboard overview."""
    page_header(
        "Overview",
        "National historical patterns and regional concentration from official oblast-level metrics.",
    )
    compact_note("Historical pages use the CSV dataset. Live API calls are limited to the Live Map.")

    try:
        with st.spinner("Loading historical alert data..."):
            featured = load_featured_historical_data()
            _, national_daily, regional_summary = load_historical_metric_tables()
    except (HistoricalDataError, HistoricalSchemaError, ValueError) as exc:
        st.error(f"Historical data could not be loaded: {exc}")
        return

    if national_daily.empty:
        st.warning("No completed oblast-level alert intervals are available for overview metrics.")
        return

    date_range = f"{featured['date'].min()} to {featured['date'].max()}"
    most_affected_region = (
        str(regional_summary.loc[0, "region"]) if not regional_summary.empty else "No region"
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "National Alert Waves",
        f"{int(national_daily['national_alert_wave_count'].sum()):,}",
    )
    col2.metric(
        "Affected Oblast Hours",
        f"{national_daily['affected_oblast_hours'].sum():,.0f}",
    )
    col3.metric("Date Range", date_range)
    col4.metric("Most Affected Region", most_affected_region)

    with st.expander("Methodology note"):
        st.write(
            "Timestamps are converted from UTC to Kyiv local time for daily aggregation. "
            "Duration metrics merge overlapping intervals inside each oblast before daily "
            "summation. The overview count chart merges simultaneous oblast episodes into "
            "national alert waves, so a broad alert window is not counted once per raw row. "
            "Visible changes over time can reflect official dataset coverage or granularity changes."
        )

    section("National Trends", "Daily national alert waves and affected oblast hours.")
    trend_left, trend_right = st.columns(2)
    with trend_left:
        count_figure = px.line(
            national_daily,
            x="date",
            y="national_alert_wave_count",
            title="Daily National Alert Waves",
            labels={
                "national_alert_wave_count": "National alert waves",
                "date": "Date",
                "national_oblast_episode_count": "Oblast episode starts",
                "active_oblasts_count": "Active oblasts",
            },
            hover_data=["national_oblast_episode_count", "active_oblasts_count"],
            color_discrete_sequence=[PRIMARY_COLOR],
        )
        st.plotly_chart(style_figure(count_figure, height=360), width="stretch")
    with trend_right:
        duration_figure = px.line(
            national_daily,
            x="date",
            y="affected_oblast_hours",
            title="Daily Affected Oblast Hours",
            labels={"affected_oblast_hours": "Affected oblast hours", "date": "Date"},
            color_discrete_sequence=[SECONDARY_COLOR],
        )
        st.plotly_chart(style_figure(duration_figure, height=360), width="stretch")

    section("Regional Concentration", "Regions with the largest historical alert load.")
    left, right = st.columns(2)
    with left:
        top_count = (
            regional_summary.sort_values("oblast_episode_count", ascending=False)
            .head(10)
            .copy()
        )
        figure = px.bar(
            top_count,
            x="oblast_episode_count",
            y="region",
            title="Top Regions by Episode Starts",
            orientation="h",
            labels={"oblast_episode_count": "Episode starts", "region": "Region"},
            color_discrete_sequence=[PRIMARY_COLOR],
        ).update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(style_figure(figure, height=420), width="stretch")
    with right:
        top_duration = regional_summary.head(10).copy()
        figure = px.bar(
            top_duration,
            x="affected_oblast_hours",
            y="region",
            title="Top Regions by Affected Hours",
            orientation="h",
            labels={"affected_oblast_hours": "Affected oblast hours", "region": "Region"},
            color_discrete_sequence=[SECONDARY_COLOR],
        ).update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(style_figure(figure, height=420), width="stretch")
