"""AI process transparency page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from air_alerts.ui import compact_note, page_header, section


def render() -> None:
    """Render AI-assisted development process notes."""
    page_header(
        "AI Process",
        "Architecture reasoning, prompt-log support, and repair history for evaluation.",
    )

    compact_note(
        "This project supports exploratory analysis and visualization. It is not an "
        "operational warning tool and does not attempt to predict attacks.",
        kind="warning",
    )

    top_left, top_right = st.columns(2)
    with top_left:
        st.subheader("Data Boundary")
        st.write(
            "Historical analysis uses the public CSV dataset because it is reproducible, "
            "testable, and appropriate for time-series exploration. The alerts.in.ua API "
            "is used only for current live status."
        )
    with top_right:
        st.subheader("Exploratory Framing")
        st.write(
            "The anomaly lab compares daily activity with a rolling baseline. Holiday "
            "proximity is context for inspection, not evidence that one event explains another."
        )

    section("Pipeline")
    pipeline = pd.DataFrame(
        [
            ("1", "Historical loading", "Validate CSV schema and parse UTC timestamps."),
            ("2", "Kyiv-time features", "Add local calendar fields for daily analysis."),
            ("3", "Holiday proximity", "Attach nearby public holidays and important dates."),
            ("4", "Anomaly scoring", "Compare regional daily activity with a rolling baseline."),
            ("5", "Live status", "Read compact alerts.in.ua oblast status through a token-safe client."),
            ("6", "Dashboard", "Expose the workflow through Streamlit pages."),
        ],
        columns=["Step", "Stage", "Purpose"],
    )
    st.dataframe(pipeline, width="stretch", hide_index=True)

    section("AI Mistakes and Corrections")
    repairs = pd.DataFrame(
        [
            (
                "Duplicate Streamlit page paths",
                "All page callables were named `render`, so Streamlit inferred duplicate routes.",
                "App crashed on startup.",
                "Added explicit `url_path` values for every page.",
            ),
            (
                "Brittle datetime test",
                "The test expected exact pandas nanosecond timestamp precision.",
                "Local pandas returned another valid timezone-aware precision.",
                "Changed the assertion to check datetime and UTC semantics.",
            ),
            (
                "Missing region in anomalies",
                "`groupby.apply` dropped `region` in the scored dataframe.",
                "Tests failed when explanation text accessed `region`.",
                "Replaced it with an explicit per-region scoring loop.",
            ),
            (
                "Map missing-value handling",
                "The map join expected optional `oblast_index` and left unmatched status as `NaN`.",
                "Minimal-schema map tests failed.",
                "Used missing status after join and normalized unmatched rows.",
            ),
        ],
        columns=["Issue", "What went wrong", "How detected", "Correction"],
    )
    st.dataframe(repairs, width="stretch", hide_index=True)

    section("Prompt Log")
    st.write(
        "The `prompts/` directory contains short stage summaries and placeholders where real prompts, outputs, "
        "or screenshots can be added for KSE submission. It is support material, not a full chat export."
    )
