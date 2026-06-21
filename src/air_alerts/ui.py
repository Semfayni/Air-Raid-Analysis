"""Shared Streamlit presentation helpers."""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st


BACKGROUND_COLOR = "#07111f"
PANEL_COLOR = "#0d1b2e"
PANEL_ALT_COLOR = "#10233a"
PANEL_BORDER = "rgba(103, 232, 249, 0.16)"
PRIMARY_COLOR = "#22d3ee"
SECONDARY_COLOR = "#f59e0b"
ACCENT_COLOR = "#ef4444"
ALERT_COLOR = "#ef4444"
MUTED_COLOR = "#94a3b8"
TEXT_COLOR = "#e5edf7"
GRID_COLOR = "rgba(148, 163, 184, 0.16)"


def apply_page_style() -> None:
    """Apply a compact dark dashboard theme for Streamlit pages."""
    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34, 211, 238, 0.08), transparent 28rem),
                #07111f;
            color: #e5edf7;
        }
        .block-container {
            max-width: 1500px;
            padding-top: 1.15rem;
            padding-bottom: 2.4rem;
        }
        [data-testid="stSidebar"] {
            background: #0a1627;
            border-right: 1px solid rgba(103, 232, 249, 0.12);
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #e5edf7;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color: #e5edf7;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(16, 35, 58, 0.98), rgba(13, 27, 46, 0.98));
            border: 1px solid rgba(103, 232, 249, 0.16);
            border-radius: 8px;
            padding: 0.65rem 0.8rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
        }
        [data-testid="stMetricLabel"] {
            color: #94a3b8;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        [data-testid="stMetricValue"] {
            color: #f8fafc;
            font-size: 1.35rem;
        }
        [data-testid="stMetricDelta"] {
            color: #22d3ee;
        }
        div[data-testid="stAlert"] {
            border-radius: 8px;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(103, 232, 249, 0.12);
            border-radius: 8px;
            overflow: hidden;
        }
        div[data-testid="stDataFrame"] * {
            color-scheme: dark;
        }
        div[data-testid="stExpander"] {
            border: 1px solid rgba(103, 232, 249, 0.12);
            background: rgba(13, 27, 46, 0.72);
            border-radius: 8px;
        }
        div[data-testid="stExpander"] summary {
            color: #e5edf7;
        }
        .aa-page-header {
            border-bottom: 1px solid rgba(103, 232, 249, 0.14);
            margin-bottom: 0.85rem;
            padding: 0.25rem 0 0.85rem 0;
        }
        .aa-page-title {
            color: #f8fafc;
            font-size: clamp(1.8rem, 3vw, 2.55rem);
            font-weight: 750;
            line-height: 1.08;
            margin: 0;
        }
        .aa-page-subtitle {
            color: #a7b4c5;
            font-size: 0.98rem;
            margin-top: 0.35rem;
            max-width: 920px;
        }
        .aa-section {
            border-top: 1px solid rgba(103, 232, 249, 0.12);
            margin: 1.15rem 0 0.65rem 0;
            padding-top: 0.8rem;
        }
        .aa-section h2 {
            color: #f8fafc;
            font-size: 1.02rem;
            font-weight: 700;
            margin: 0;
        }
        .aa-section p {
            color: #94a3b8;
            font-size: 0.86rem;
            margin: 0.2rem 0 0 0;
        }
        .aa-note {
            background: rgba(13, 27, 46, 0.82);
            border: 1px solid rgba(103, 232, 249, 0.16);
            border-left: 3px solid #22d3ee;
            border-radius: 8px;
            color: #dbeafe;
            font-size: 0.9rem;
            margin: 0.55rem 0 0.85rem 0;
            padding: 0.62rem 0.75rem;
        }
        .aa-note-warning {
            border-left-color: #f59e0b;
            color: #fde68a;
        }
        .aa-note-error {
            border-left-color: #ef4444;
            color: #fecaca;
        }
        .aa-panel {
            background: linear-gradient(180deg, rgba(16, 35, 58, 0.95), rgba(13, 27, 46, 0.95));
            border: 1px solid rgba(103, 232, 249, 0.16);
            border-radius: 8px;
            padding: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    """Render a consistent page header."""
    apply_page_style()
    st.markdown(
        f"""
        <div class="aa-page-header">
            <h1 class="aa-page-title">{escape(title)}</h1>
            <div class="aa-page-subtitle">{escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compact_note(text: str, *, kind: str = "info") -> None:
    """Render a compact status note."""
    note_class = "aa-note"
    if kind == "warning":
        note_class += " aa-note-warning"
    elif kind == "error":
        note_class += " aa-note-error"
    st.markdown(
        f'<div class="{note_class}">{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def section(title: str, caption: str | None = None) -> None:
    """Render a section heading with optional compact caption."""
    caption_html = f"<p>{escape(caption)}</p>" if caption else ""
    st.markdown(
        f"""
        <div class="aa-section">
            <h2>{escape(title)}</h2>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_figure(figure: go.Figure, *, height: int | None = None) -> go.Figure:
    """Apply the shared dark dashboard theme to a Plotly figure."""
    figure.update_layout(
        template="plotly_dark",
        font={"family": "Arial, sans-serif", "color": TEXT_COLOR},
        title={"font": {"size": 15, "color": "#f8fafc"}, "x": 0.02, "xanchor": "left"},
        legend_title_text="",
        margin={"l": 18, "r": 18, "t": 46, "b": 26},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PANEL_COLOR,
        coloraxis_colorbar={"outlinewidth": 0, "tickcolor": MUTED_COLOR},
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        linecolor="rgba(148, 163, 184, 0.22)",
        tickfont={"color": MUTED_COLOR},
        title_font={"color": TEXT_COLOR},
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        linecolor="rgba(148, 163, 184, 0.22)",
        tickfont={"color": MUTED_COLOR},
        title_font={"color": TEXT_COLOR},
    )
    if height:
        figure.update_layout(height=height)
    return figure
