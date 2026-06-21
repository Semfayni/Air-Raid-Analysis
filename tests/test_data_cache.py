from __future__ import annotations

import pandas as pd

from air_alerts.pages import data_cache


def test_load_historical_metric_tables_returns_overview_national_schema(monkeypatch) -> None:
    frame = pd.DataFrame(
        {
            "region": ["Kyiv Oblast", "Lviv Oblast"],
            "source": ["official", "official"],
            "started_at": pd.to_datetime(
                ["2024-01-01T08:00:00Z", "2024-01-01T08:30:00Z"],
                utc=True,
            ),
            "finished_at": pd.to_datetime(
                ["2024-01-01T09:00:00Z", "2024-01-01T09:30:00Z"],
                utc=True,
            ),
        }
    )

    monkeypatch.setattr(data_cache, "load_featured_historical_data", lambda: frame)
    data_cache.load_historical_metric_tables.clear()

    _, national_daily, _ = data_cache.load_historical_metric_tables("test-schema")

    assert {
        "date",
        "national_alert_wave_count",
        "national_oblast_episode_count",
        "affected_oblast_hours",
        "active_oblasts_count",
    }.issubset(national_daily.columns)
