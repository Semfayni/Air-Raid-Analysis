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
from air_alerts.ui import PRIMARY_COLOR, page_header, section, style_figure


def render() -> None:
    """Render the regional historical explorer."""
    page_header(
        "Regional Explorer",
        "Filter historical alerts by region, date range, and source.",
    )

    try:
        with st.spinner("Loading featured historical data..."):
            featured = load_featured_historical_data()
    except (HistoricalDataError, HistoricalSchemaError, ValueError) as exc:
        st.error(f"Historical data could not be loaded: {exc}")
        return

    if featured.empty:
        st.warning("No historical alerts are available.")
        return

    regions = sorted(region for region in featured["region"].dropna().unique())
    default_region = _default_region(featured, regions)
    min_date = featured["date"].min()
    max_date = featured["date"].max()

    with st.sidebar:
        st.header("Filters")
        selected_region = st.selectbox(
            "Region",
            regions,
            index=regions.index(default_region) if default_region in regions else 0,
        )
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

    completed = filtered[filtered["is_finished"]]
    summary_cols = st.columns(4)
    summary_cols[0].metric("Region", selected_region)
    summary_cols[1].metric("Completed Alerts", f"{len(completed):,}")
    summary_cols[2].metric("Alert Hours", f"{completed['duration_hours'].sum():,.0f}")
    summary_cols[3].metric("Selected Dates", f"{date_range[0]} to {date_range[1]}")
    with st.container(border=True):
        st.write(region_interpretation(selected_region, filtered))

    daily_counts = daily_alert_count(filtered)
    daily_duration = daily_alert_duration(filtered)
    daily_duration["duration_hours"] = daily_duration["duration_minutes"] / 60

    section("Daily Trends", "Count and total completed-alert duration over time.")
    top_left, top_right = st.columns(2)
    with top_left:
        count_figure = px.line(
            daily_counts,
            x="date",
            y="alert_count",
            title="Daily Alert Count",
            labels={"alert_count": "Alerts", "date": "Date"},
            color_discrete_sequence=[PRIMARY_COLOR],
        )
        st.plotly_chart(style_figure(count_figure, height=340), width="stretch")
    with top_right:
        duration_figure = px.line(
            daily_duration,
            x="date",
            y="duration_hours",
            title="Daily Total Duration",
            labels={"duration_hours": "Alert hours", "date": "Date"},
            color_discrete_sequence=["#8a3ffc"],
        )
        st.plotly_chart(style_figure(duration_figure, height=340), width="stretch")

    section("Temporal Shape", "When alerts appear within the selected region and period.")
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
    lower_left, lower_right = st.columns([1.25, 1])
    with lower_left:
        heatmap_figure = px.imshow(
            heatmap_data,
            title="Hour by Weekday",
            labels={"x": "Hour", "y": "Weekday", "color": "Alerts"},
            aspect="auto",
            color_continuous_scale="Reds",
        )
        st.plotly_chart(style_figure(heatmap_figure, height=430), width="stretch")

    with lower_right:
        monthly = monthly_alert_trend(filtered)
        monthly_figure = px.bar(
            monthly,
            x="month",
            y="alert_count",
            title="Monthly Trend",
            hover_data=["total_duration_hours"],
            labels={"alert_count": "Alerts", "month": "Month"},
            color_discrete_sequence=[PRIMARY_COLOR],
        )
        st.plotly_chart(style_figure(monthly_figure, height=430), width="stretch")


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
