"""Anomaly lab page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from air_alerts.anomalies import AnomalyAnalysisError, detect_daily_anomalies
from air_alerts.anomaly_view import (
    holiday_window_comparison,
    nearby_holiday_frequency,
    top_anomalies,
)
from air_alerts.dashboard import filter_featured_alerts
from air_alerts.data import HistoricalDataError, HistoricalSchemaError
from air_alerts.features import regional_summary
from air_alerts.pages.data_cache import load_featured_historical_data
from air_alerts.ui import (
    ACCENT_COLOR,
    PRIMARY_COLOR,
    compact_note,
    page_header,
    section,
    style_figure,
)


ALL_REGIONS = "All regions"


@st.cache_data(show_spinner="Scoring daily anomaly signals...")
def _detect_anomalies_cached(
    filtered: pd.DataFrame,
    rolling_window: int,
    min_periods: int,
    z_threshold: float,
    holiday_window_days: int,
) -> pd.DataFrame:
    return detect_daily_anomalies(
        filtered,
        rolling_window=rolling_window,
        min_periods=min_periods,
        z_threshold=z_threshold,
        holiday_window_days=holiday_window_days,
    )


def render() -> None:
    """Render the anomaly lab page."""
    page_header(
        "Anomaly Lab",
        "Inspect unusual daily regional activity with nearby holiday and important-date context.",
    )
    compact_note(
        "Holiday proximity is exploratory context and not evidence of a direct relationship. "
        "Use this page to inspect patterns, not as an operational warning source.",
        kind="warning",
    )

    with st.expander("Methodology"):
        st.write(
            "The lab first builds daily alert activity by region. It combines alert count "
            "and total alert duration into a transparent activity score, then compares each "
            "day with a rolling historical baseline for the same region. Higher z scores "
            "mean the day was unusual relative to the selected rolling window. The holiday "
            "window marks whether the date is within the selected number of days from a "
            "Ukrainian public holiday or important date."
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

    min_date = featured["date"].min()
    max_date = featured["date"].max()
    with st.sidebar:
        st.header("Anomaly Controls")
        selected_region = _region_selector(featured)
        selected_dates = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        date_range = _normalize_date_range(selected_dates, min_date, max_date)

        selected_sources = None
        if "source" in featured.columns:
            sources = sorted(str(source) for source in featured["source"].dropna().unique())
            selected_sources = st.multiselect("Source", sources, default=sources)

        z_threshold = st.slider("Z score threshold", 1.0, 5.0, 2.0, 0.1)
        rolling_window = st.slider("Rolling window days", 14, 120, 30, 1)
        holiday_window_days = st.slider("Holiday window days", 0, 14, 2, 1)
        min_periods = min(14, rolling_window)

    region_filter = None if selected_region == ALL_REGIONS else selected_region
    filtered = filter_featured_alerts(
        featured,
        region=region_filter,
        date_range=date_range,
        sources=selected_sources,
    )

    if filtered.empty:
        st.warning("No alerts match the current filters.")
        return

    try:
        scored = _detect_anomalies_cached(
            filtered,
            rolling_window,
            min_periods,
            z_threshold,
            holiday_window_days,
        )
    except AnomalyAnalysisError as exc:
        st.error(f"Anomaly scoring could not run: {exc}")
        return

    if scored.empty:
        st.warning("No daily records are available after scoring.")
        return

    anomaly_rows = scored[scored["is_anomaly"]]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Scored Daily Rows", f"{len(scored):,}")
    metric_cols[1].metric("Anomaly Days", f"{len(anomaly_rows):,}")
    metric_cols[2].metric("Threshold", f"{z_threshold:.1f}")
    metric_cols[3].metric("Holiday Window", f"+/- {holiday_window_days} days")

    section("Daily Activity and Anomaly Points", "Highlighted points meet the selected z-score threshold.")
    st.plotly_chart(style_figure(_activity_figure(scored), height=460), width="stretch")

    section("Top Anomalies", "Highest-scoring days in the current filter selection.")
    top_table = top_anomalies(scored)
    if top_table.empty:
        st.info("No anomaly days were found with the current threshold.")
    else:
        st.dataframe(top_table, width="stretch", hide_index=True)

    section("Holiday Context", "Counts below compare anomaly days by proximity window and nearest date marker.")
    left, right = st.columns(2)
    with left:
        comparison = holiday_window_comparison(scored)
        if comparison.empty:
            st.info("No anomaly days to compare.")
        else:
            figure = px.bar(
                comparison,
                x="holiday_window",
                y="anomaly_count",
                labels={
                    "holiday_window": "Holiday window",
                    "anomaly_count": "Anomaly days",
                },
                title="Inside vs Outside Holiday Window",
                color_discrete_sequence=[PRIMARY_COLOR],
            )
            st.plotly_chart(style_figure(figure, height=360), width="stretch")

    with right:
        frequency = nearby_holiday_frequency(scored)
        if frequency.empty:
            st.info("No anomaly days to summarize.")
        else:
            figure = px.bar(
                frequency,
                x="anomaly_count",
                y="nearest_holiday_name",
                orientation="h",
                labels={
                    "anomaly_count": "Anomaly days",
                    "nearest_holiday_name": "Nearest holiday or date",
                },
                title="Most Frequent Nearby Dates",
                color_discrete_sequence=[PRIMARY_COLOR],
            ).update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(style_figure(figure, height=360), width="stretch")


def _region_selector(featured: pd.DataFrame) -> str:
    regions = sorted(str(region) for region in featured["region"].dropna().unique())
    if not regions:
        return ALL_REGIONS
    summary = regional_summary(featured)
    default_region = str(summary.loc[0, "region"]) if not summary.empty else regions[0]
    options = [ALL_REGIONS] + regions
    default_index = options.index(default_region) if default_region in options else 0
    return st.selectbox("Region", options, index=default_index)


def _activity_figure(scored: pd.DataFrame) -> go.Figure:
    figure = px.line(
        scored,
        x="date",
        y="alert_count",
        color="region",
        title="Daily Alert Count with Anomaly Markers",
        labels={"alert_count": "Alerts", "date": "Date", "region": "Region"},
        color_discrete_sequence=[PRIMARY_COLOR, "#6f4e37", "#8a3ffc", "#2f855a"],
    )
    anomaly_rows = scored[scored["is_anomaly"]]
    if not anomaly_rows.empty:
        figure.add_trace(
            go.Scatter(
                x=anomaly_rows["date"],
                y=anomaly_rows["alert_count"],
                mode="markers",
                name="Anomaly",
                marker={"color": ACCENT_COLOR, "size": 9, "symbol": "diamond"},
                text=anomaly_rows["explanation"],
                hovertemplate="%{text}<extra></extra>",
            )
        )
    return figure


def _normalize_date_range(selected_dates, min_date, max_date):
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        return selected_dates
    if not isinstance(selected_dates, (tuple, list)):
        return (selected_dates, selected_dates)
    return (min_date, max_date)
