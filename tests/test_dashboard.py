from __future__ import annotations

from datetime import date

import pandas as pd

from air_alerts.dashboard import (
    filter_featured_alerts,
    monthly_alert_trend,
    overview_kpis,
    region_interpretation,
    top_regions_by_alert_count,
)


def _featured_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["Kyiv Oblast", "Kyiv Oblast", "Lviv Oblast"],
            "source": ["official", "volunteer", "official"],
            "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 2, 1)],
            "started_at": pd.to_datetime(
                [
                    "2024-01-01T01:00:00Z",
                    "2024-01-02T01:00:00Z",
                    "2024-02-01T01:00:00Z",
                ],
                utc=True,
            ),
            "finished_at": pd.to_datetime(
                [
                    "2024-01-01T02:00:00Z",
                    "2024-01-02T03:00:00Z",
                    None,
                ],
                utc=True,
            ),
            "duration_hours": [1.0, 2.0, pd.NA],
            "is_finished": [True, True, False],
        }
    )


def test_overview_kpis_ignore_unfinished_for_totals() -> None:
    kpis = overview_kpis(_featured_frame())

    assert not hasattr(kpis, "total_alerts")
    assert kpis.national_alert_wave_count == 1
    assert kpis.national_oblast_episode_count == 1
    assert kpis.alert_start_count == 1
    assert kpis.affected_oblast_hours == 1.0
    assert kpis.most_affected_region == "Kyiv Oblast"


def test_filter_featured_alerts_by_region_date_and_source() -> None:
    filtered = filter_featured_alerts(
        _featured_frame(),
        region="Kyiv Oblast",
        date_range=(date(2024, 1, 2), date(2024, 1, 31)),
        sources=["volunteer"],
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["source"] == "volunteer"


def test_top_regions_by_alert_count() -> None:
    top = top_regions_by_alert_count(_featured_frame())

    assert list(top.columns) == ["region", "oblast_episode_count"]
    assert top.loc[0, "region"] == "Kyiv Oblast"
    assert top.loc[0, "oblast_episode_count"] == 1


def test_monthly_alert_trend() -> None:
    monthly = monthly_alert_trend(_featured_frame())

    assert list(monthly["month"]) == ["2024-01"]
    assert monthly.loc[0, "oblast_episode_count"] == 1


def test_monthly_alert_trend_uses_merged_episode_starts() -> None:
    frame = pd.DataFrame(
        {
            "region": ["Kyiv Oblast", "Kyiv Oblast", "Kyiv Oblast"],
            "source": ["official", "official", "official"],
            "date": [date(2024, 1, 1)] * 3,
            "started_at": pd.to_datetime(
                [
                    "2024-01-01T08:00:00Z",
                    "2024-01-01T08:00:00Z",
                    "2024-01-01T08:15:00Z",
                ],
                utc=True,
            ),
            "finished_at": pd.to_datetime(
                [
                    "2024-01-01T09:00:00Z",
                    "2024-01-01T09:00:00Z",
                    "2024-01-01T09:30:00Z",
                ],
                utc=True,
            ),
            "is_finished": [True, True, True],
        }
    )

    monthly = monthly_alert_trend(frame)

    assert monthly.loc[0, "oblast_episode_count"] == 1


def test_region_interpretation_is_deterministic() -> None:
    text = region_interpretation("Kyiv Oblast", _featured_frame())

    assert text == (
        "Kyiv Oblast: 1 merged oblast episode starts from 2024-01-01 "
        "to 2024-01-01, with 1.0 affected oblast hours across 1 active days."
    )
