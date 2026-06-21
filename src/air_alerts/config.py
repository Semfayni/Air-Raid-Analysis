"""Environment configuration for the dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    alerts_api_token: str | None


def load_settings() -> Settings:
    """Load settings from `.env` and the current environment."""
    load_dotenv()
    token = os.getenv("ALERTS_API_TOKEN")
    return Settings(alerts_api_token=token or None)
