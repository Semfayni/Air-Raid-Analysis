"""Regional explorer page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from air_alerts.dashboard import (
    filter_featured_alerts,
    monthly_alert_trend,
    region_interpretation,
)
from air_alerts.data import HistoricalDataError, HistoricalSchemaError
from air_alerts.features import (
    daily_alert_count,
    daily_alert_duration,
    hourly_weekday_matrix,
    regional_summary,
)
from air_alerts.pages.data_cache import load_featured_historical_data


def render() -> None:
    """Render the regional historical explorer."""
    st.title("Regional Explorer")
    st.caption("Explore historical alert patterns by region, date range, and source.")

    try:
        featured = load_featured_historical_data()
    except (HistoricalDataError, HistoricalSchemaError, ValueError) as exc:
        st.error(f"Historical data could not be loaded: {exc}")
        return

    if featured.empty:
        st.warning("No historical alerts are available.")
        return

    regions = sorted(region for region in featured["region"].dropna().unique())
    default_region = _default_region(featured, regions)
    selected_region = st.selectbox(
        "Region",
        regions,
        index=regions.index(default_region) if default_region in regions else 0,
    )

    min_date = featured["date"].min()
    max_date = featured["date"].max()
    selected_dates = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    date_range = _normalize_date_range(selected_dates, min_date, max_date)

    selected_sources = None
    if "source" in featured.columns:
        sources = sorted(source for source in featured["source"].dropna().unique())
        selected_sources = st.multiselect("Source", sources, default=sources)

    filtered = filter_featured_alerts(
        featured,
        region=selected_region,
        date_range=date_range,
        sources=selected_sources,
    )

    if filtered.empty:
        st.warning("No alerts match the current filters.")
        return

    st.write(region_interpretation(selected_region, filtered))

    daily_counts = daily_alert_count(filtered)
    daily_duration = daily_alert_duration(filtered)
    daily_duration["duration_hours"] = daily_duration["duration_minutes"] / 60

    st.subheader("Daily Alert Count")
    st.plotly_chart(
        px.line(daily_counts, x="date", y="alert_count", labels={"alert_count": "Alerts"}),
        width="stretch",
    )

    st.subheader("Daily Total Duration")
    st.plotly_chart(
        px.line(
            daily_duration,
            x="date",
            y="duration_hours",
            labels={"duration_hours": "Alert hours"},
        ),
        width="stretch",
    )

    st.subheader("Hour by Weekday")
    matrix = hourly_weekday_matrix(filtered)
    heatmap_data = matrix.rename(
        index={
            0: "Monday",
            1: "Tuesday",
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday",
        }
    )
    st.plotly_chart(
        px.imshow(
            heatmap_data,
            labels={"x": "Hour", "y": "Weekday", "color": "Alerts"},
            aspect="auto",
            color_continuous_scale="Reds",
        ),
        width="stretch",
    )

    st.subheader("Monthly Trend")
    monthly = monthly_alert_trend(filtered)
    st.plotly_chart(
        px.bar(
            monthly,
            x="month",
            y="alert_count",
            hover_data=["total_duration_hours"],
            labels={"alert_count": "Alerts", "month": "Month"},
        ),
        width="stretch",
    )


def _default_region(featured: pd.DataFrame, regions: list[str]) -> str:
    summary = regional_summary(featured)
    if not summary.empty:
        return str(summary.loc[0, "region"])
    return regions[0]


def _normalize_date_range(selected_dates, min_date, max_date):
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        return selected_dates
    if not isinstance(selected_dates, (tuple, list)):
        return (selected_dates, selected_dates)
    return (min_date, max_date)
