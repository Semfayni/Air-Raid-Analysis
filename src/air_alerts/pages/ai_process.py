"""AI process transparency page."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Render the AI process placeholder."""
    st.title("AI Process")
    st.caption("Transparent notes for future agentic analysis steps.")

    st.write(
        "This page will document data provenance, prompt design, assumptions, validation checks, "
        "and limits of any AI-assisted analysis."
    )
    st.warning("The project must not present AI output as official warnings or attack predictions.")
