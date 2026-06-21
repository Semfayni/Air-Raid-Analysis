from __future__ import annotations

from air_alerts import __version__
from air_alerts.config import Settings
from air_alerts.data import sources


def test_package_has_version() -> None:
    assert __version__


def test_settings_shape() -> None:
    settings = Settings(alerts_api_token=None)
    assert settings.alerts_api_token is None


def test_source_urls_are_declared() -> None:
    assert sources.HISTORICAL_DATASET_URL.startswith("https://github.com/")
    assert sources.LIVE_ALERTS_API_URL.startswith("https://devs.alerts.in.ua/")
