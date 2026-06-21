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
            "duration_hours": [1.0, 2.0, pd.NA],
            "is_finished": [True, True, False],
        }
    )


def test_overview_kpis_ignore_unfinished_for_totals() -> None:
    kpis = overview_kpis(_featured_frame())

    assert kpis.total_alerts == 2
    assert kpis.total_alert_hours == 3.0
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

    assert list(top.columns) == ["region", "alert_count"]
    assert top.loc[0, "region"] == "Kyiv Oblast"
    assert top.loc[0, "alert_count"] == 2


def test_monthly_alert_trend() -> None:
    monthly = monthly_alert_trend(_featured_frame())

    assert list(monthly["month"]) == ["2024-01"]
    assert monthly.loc[0, "alert_count"] == 2


def test_region_interpretation_is_deterministic() -> None:
    text = region_interpretation("Kyiv Oblast", _featured_frame())

    assert text == (
        "Kyiv Oblast: 2 completed alerts from 2024-01-01 to 2024-01-02, "
        "with 3.0 total alert hours and an average duration of 1.50 hours."
    )
