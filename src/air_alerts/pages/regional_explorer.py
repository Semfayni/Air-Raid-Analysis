"""Regional explorer page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def render() -> None:
    """Render the regional explorer placeholder."""
    st.title("Regional Explorer")
    st.caption("Placeholder chart using tiny sample data until historical loaders are added.")

    sample = pd.DataFrame(
        {
            "region": ["Kyiv", "Kharkiv", "Lviv"],
            "sample_alert_count": [0, 0, 0],
        }
    )
    chart = px.bar(
        sample,
        x="region",
        y="sample_alert_count",
        title="Sample Regional Alert Counts",
    )
    st.plotly_chart(chart, use_container_width=True)
