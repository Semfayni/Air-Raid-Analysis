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


def render() -> None:
    """Render the historical dashboard overview."""
    st.title("Ukraine Air Alert Intelligence Dashboard")
    st.caption("Exploratory analysis and visualization. Not an attack prediction tool.")
    st.info("Historical views use the CSV dataset, not the live alerts API.")

    try:
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

    daily_counts = daily_alert_count(featured)
    daily_duration = daily_alert_duration(featured)
    daily_duration["duration_hours"] = daily_duration["duration_minutes"] / 60

    st.subheader("National Daily Alert Count")
    st.plotly_chart(
        px.line(daily_counts, x="date", y="alert_count", labels={"alert_count": "Alerts"}),
        width="stretch",
    )

    st.subheader("National Daily Alert Duration")
    st.plotly_chart(
        px.line(
            daily_duration,
            x="date",
            y="duration_hours",
            labels={"duration_hours": "Alert hours"},
        ),
        width="stretch",
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Top Regions by Alert Count")
        top_count = top_regions_by_alert_count(featured)
        st.plotly_chart(
            px.bar(
                top_count,
                x="alert_count",
                y="region",
                orientation="h",
                labels={"alert_count": "Alerts", "region": "Region"},
            ).update_layout(yaxis={"categoryorder": "total ascending"}),
            width="stretch",
        )
    with right:
        st.subheader("Top Regions by Total Duration")
        top_duration = top_regions_by_duration(featured)
        st.plotly_chart(
            px.bar(
                top_duration,
                x="total_duration_hours",
                y="region",
                orientation="h",
                labels={"total_duration_hours": "Alert hours", "region": "Region"},
            ).update_layout(yaxis={"categoryorder": "total ascending"}),
            width="stretch",
        )
