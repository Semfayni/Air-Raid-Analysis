"""Regional explorer page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from air_alerts.dashboard import (
    filter_featured_alerts,
)
from air_alerts.data import HistoricalDataError, HistoricalSchemaError
from air_alerts.metrics import daily_oblast_metrics, hourly_weekday_episode_matrix
from air_alerts.pages.data_cache import (
    load_featured_historical_data,
    load_historical_metric_tables,
)
from air_alerts.ui import PRIMARY_COLOR, page_header, section, style_figure


@st.cache_data(show_spinner="Computing selected oblast metrics...")
def _daily_oblast_metrics_cached(
    frame: pd.DataFrame,
    sources: tuple[str, ...] | None,
) -> pd.DataFrame:
    return daily_oblast_metrics(frame, sources=sources)


def render() -> None:
    """Render the regional historical explorer."""
    page_header(
        "Regional Explorer",
        "Filter historical alerts by region, date range, and source.",
    )

    try:
        with st.spinner("Loading featured historical data..."):
            featured = load_featured_historical_data()
            _, _, all_region_summary = load_historical_metric_tables()
    except (HistoricalDataError, HistoricalSchemaError, ValueError) as exc:
        st.error(f"Historical data could not be loaded: {exc}")
        return

    if featured.empty:
        st.warning("No historical alerts are available.")
        return

    regions = sorted(region for region in all_region_summary["region"].dropna().unique())
    if not regions:
        regions = sorted(region for region in featured["region"].dropna().unique())
    if not regions:
        st.warning("No oblast-level regions are available for exploration.")
        return
    default_region = _default_region(all_region_summary, regions)
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
            default_sources = ["official"] if "official" in sources else sources
            selected_sources = st.multiselect("Source", sources, default=default_sources)

    metric_base = filter_featured_alerts(
        featured,
        region=selected_region,
        sources=selected_sources,
    )
    if metric_base.empty:
        st.warning("No alerts match the current region and source filters.")
        return

    filtered = filter_featured_alerts(metric_base, date_range=date_range)

    source_tuple = tuple(selected_sources) if selected_sources is not None else None
    daily_metrics = _daily_oblast_metrics_cached(metric_base, source_tuple)
    daily_metrics = daily_metrics[
        (daily_metrics["date"] >= date_range[0]) & (daily_metrics["date"] <= date_range[1])
    ].copy()
    if daily_metrics.empty:
        st.warning("No oblast-level metrics match the current filters.")
        return

    summary_cols = st.columns(4)
    summary_cols[0].metric("Region", selected_region)
    summary_cols[1].metric(
        "Episode Starts",
        f"{int(daily_metrics['oblast_episode_count'].sum()):,}",
    )
    summary_cols[2].metric(
        "Affected Hours",
        f"{daily_metrics['affected_oblast_hours'].sum():,.0f}",
    )
    summary_cols[3].metric("Selected Dates", f"{date_range[0]} to {date_range[1]}")
    with st.container(border=True):
        st.write(_interpret_region_metrics(selected_region, daily_metrics))

    section("Daily Trends", "Merged oblast episode starts and affected hours over time.")
    top_left, top_right = st.columns(2)
    with top_left:
        count_figure = px.line(
            daily_metrics,
            x="date",
            y="oblast_episode_count",
            title="Daily Episode Starts",
            labels={"oblast_episode_count": "Episode starts", "date": "Date"},
            color_discrete_sequence=[PRIMARY_COLOR],
        )
        st.plotly_chart(style_figure(count_figure, height=340), width="stretch")
    with top_right:
        duration_figure = px.line(
            daily_metrics,
            x="date",
            y="affected_oblast_hours",
            title="Daily Affected Hours",
            labels={"affected_oblast_hours": "Affected oblast hours", "date": "Date"},
            color_discrete_sequence=["#8a3ffc"],
        )
        st.plotly_chart(style_figure(duration_figure, height=340), width="stretch")

    section("Temporal Shape", "When alerts appear within the selected region and period.")
    matrix = hourly_weekday_episode_matrix(filtered, sources=source_tuple)
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
            labels={"x": "Hour", "y": "Weekday", "color": "Episode starts"},
            aspect="auto",
            color_continuous_scale="Reds",
        )
        st.plotly_chart(style_figure(heatmap_figure, height=430), width="stretch")

    with lower_right:
        monthly = _monthly_metric_trend(daily_metrics)
        monthly_figure = px.bar(
            monthly,
            x="month",
            y="oblast_episode_count",
            title="Monthly Trend",
            hover_data=["affected_oblast_hours"],
            labels={"oblast_episode_count": "Episode starts", "month": "Month"},
            color_discrete_sequence=[PRIMARY_COLOR],
        )
        st.plotly_chart(style_figure(monthly_figure, height=430), width="stretch")


def _default_region(summary: pd.DataFrame, regions: list[str]) -> str:
    if not summary.empty:
        return str(summary.loc[0, "region"])
    return regions[0]


def _interpret_region_metrics(region: str, daily_metrics: pd.DataFrame) -> str:
    alert_starts = int(daily_metrics["oblast_episode_count"].sum())
    affected_hours = float(daily_metrics["affected_oblast_hours"].sum())
    active_days = int((daily_metrics["affected_oblast_hours"] > 0).sum())
    return (
        f"{region}: {alert_starts:,} merged oblast episode starts and "
        f"{affected_hours:,.1f} affected oblast hours across {active_days:,} active days "
        "in the selected period."
    )


def _monthly_metric_trend(daily_metrics: pd.DataFrame) -> pd.DataFrame:
    monthly = daily_metrics.copy()
    monthly["month"] = pd.to_datetime(monthly["date"]).dt.to_period("M").astype(str)
    return (
        monthly.groupby("month", dropna=False)
        .agg(
            oblast_episode_count=("oblast_episode_count", "sum"),
            affected_oblast_hours=("affected_oblast_hours", "sum"),
        )
        .reset_index()
        .sort_values("month", ignore_index=True)
    )


def _normalize_date_range(selected_dates, min_date, max_date):
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        return selected_dates
    if not isinstance(selected_dates, (tuple, list)):
        return (selected_dates, selected_dates)
    return (min_date, max_date)
