"""Streamlit entry point for the Ukraine Air Alert Intelligence Dashboard."""

from __future__ import annotations

import streamlit as st

from air_alerts.pages import (
    ai_process,
    anomaly_lab,
    live_map,
    overview,
    regional_explorer,
)


def main() -> None:
    """Render the multipage Streamlit app shell."""
    st.set_page_config(
        page_title="Ukraine Air Alert Intelligence Dashboard",
        page_icon="UA",
        layout="wide",
    )

    pages = {
        "Dashboard": [
            st.Page(overview.render, title="Overview", url_path="overview"),
            st.Page(live_map.render, title="Live Map", url_path="live-map"),
            st.Page(
                regional_explorer.render,
                title="Regional Explorer",
                url_path="regional-explorer",
            ),
            st.Page(anomaly_lab.render, title="Anomaly Lab", url_path="anomaly-lab"),
        ],
        "Project": [
            st.Page(ai_process.render, title="AI Process", url_path="ai-process"),
        ],
    }

    navigation = st.navigation(pages)
    navigation.run()


if __name__ == "__main__":
    main()
