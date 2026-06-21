from __future__ import annotations

from datetime import date

import pandas as pd

from air_alerts.anomaly_view import (
    holiday_window_comparison,
    nearby_holiday_frequency,
    top_anomalies,
)


def _scored_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [date(2024, 8, 23), date(2024, 8, 24), date(2024, 8, 25)],
            "region": ["Kyiv Oblast", "Kyiv Oblast", "Lviv Oblast"],
            "oblast_episode_count": [2, 10, 4],
            "affected_oblast_hours": [2.0, 8.0, 3.0],
            "z_score": [1.0, 3.2, 2.4],
            "is_anomaly": [False, True, True],
            "nearest_holiday_name": ["Independence Day", "Independence Day", "Christmas"],
            "days_to_nearest_holiday": [1, 0, 122],
            "is_holiday_window": [True, True, False],
            "explanation": ["baseline context", "worth inspecting", "worth inspecting"],
        }
    )


def test_top_anomalies_returns_expected_columns() -> None:
    result = top_anomalies(_scored_frame(), limit=1)

    assert list(result.columns) == [
        "date",
        "region",
        "oblast_episode_count",
        "affected_oblast_hours",
        "z_score",
        "nearest_holiday_name",
        "days_to_nearest_holiday",
        "explanation",
    ]
    assert result.loc[0, "z_score"] == 3.2


def test_holiday_window_comparison_counts_anomalies_only() -> None:
    result = holiday_window_comparison(_scored_frame())

    assert result["anomaly_count"].sum() == 2
    assert set(result["holiday_window"]) == {
        "Inside holiday window",
        "Outside holiday window",
    }


def test_nearby_holiday_frequency_counts_anomalies_only() -> None:
    result = nearby_holiday_frequency(_scored_frame())

    assert result["anomaly_count"].sum() == 2
    assert set(result["nearest_holiday_name"]) == {"Independence Day", "Christmas"}
