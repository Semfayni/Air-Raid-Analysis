"""Shared Streamlit presentation helpers."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st


PRIMARY_COLOR = "#1f4e5f"
ACCENT_COLOR = "#d7263d"
MUTED_COLOR = "#5f6b76"
GRID_COLOR = "rgba(31, 78, 95, 0.12)"


def apply_page_style() -> None:
    """Apply small, restrained CSS adjustments for dashboard pages."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid rgba(31, 78, 95, 0.12);
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
        }
        [data-testid="stMetricLabel"] {
            color: #5f6b76;
        }
        div[data-testid="stAlert"] {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    """Render a consistent page header."""
    apply_page_style()
    st.title(title)
    st.caption(subtitle)


def compact_note(text: str, *, kind: str = "info") -> None:
    """Render a compact status note."""
    if kind == "warning":
        st.warning(text)
    elif kind == "error":
        st.error(text)
    else:
        st.info(text)


def section(title: str, caption: str | None = None) -> None:
    """Render a section heading with optional compact caption."""
    st.divider()
    st.subheader(title)
    if caption:
        st.caption(caption)


def style_figure(figure: go.Figure, *, height: int | None = None) -> go.Figure:
    """Apply a restrained dashboard theme to a Plotly figure."""
    figure.update_layout(
        template="plotly_white",
        font={"family": "Arial, sans-serif", "color": "#1f2933"},
        title={"font": {"size": 16}, "x": 0.02, "xanchor": "left"},
        legend_title_text="",
        margin={"l": 16, "r": 16, "t": 48, "b": 24},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    figure.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)
    figure.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)
    if height:
        figure.update_layout(height=height)
    return figure
