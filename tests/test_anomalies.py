from __future__ import annotations

from datetime import date

import pandas as pd

from air_alerts.anomalies import build_daily_region_timeseries, detect_daily_anomalies


def _alert_rows(
    daily_counts: list[int],
    *,
    region: str = "Kyivska oblast",
    start_date: str = "2024-07-20",
) -> pd.DataFrame:
    rows = []
    current = pd.Timestamp(start_date, tz="Europe/Kyiv")
    for day_offset, count in enumerate(daily_counts):
        day = current + pd.Timedelta(days=day_offset)
        for alert_index in range(count):
            started_at_kyiv = day + pd.Timedelta(hours=alert_index)
            finished_at_kyiv = started_at_kyiv + pd.Timedelta(hours=1)
            rows.append(
                {
                    "region": region,
                    "started_at": started_at_kyiv.tz_convert("UTC"),
                    "finished_at": finished_at_kyiv.tz_convert("UTC"),
                    "source": "official",
                }
            )
    return pd.DataFrame(rows)


def test_synthetic_spike_is_detected_as_anomaly() -> None:
    frame = _alert_rows([1] * 20 + [10])

    result = detect_daily_anomalies(
        frame,
        rolling_window=14,
        min_periods=7,
        z_threshold=2.0,
    )
    spike = result[result["date"] == date(2024, 8, 9)].iloc[0]

    assert bool(spike["is_anomaly"]) is True
    assert spike["z_score"] >= 2.0


def test_holiday_proximity_columns_are_joined() -> None:
    frame = _alert_rows([1] * 10, start_date="2024-08-20")

    result = detect_daily_anomalies(frame, rolling_window=5, min_periods=3)

    assert "region" in result.columns
    assert result["region"].eq("Kyivska oblast").all()
    assert "nearest_holiday_name" in result.columns
    assert "nearest_holiday_date" in result.columns
    assert "days_to_nearest_holiday" in result.columns
    assert "is_holiday_window" in result.columns
    near_independence_day = result[result["date"] == date(2024, 8, 23)].iloc[0]
    assert near_independence_day["nearest_holiday_name"] == "Independence Day"


def test_constant_values_do_not_divide_by_zero() -> None:
    frame = _alert_rows([1] * 25)

    result = detect_daily_anomalies(frame, rolling_window=10, min_periods=5)

    assert result["z_score"].notna().all()
    assert result["z_score"].max() == 0
    assert bool(result["is_anomaly"].any()) is False


def test_unfinished_alerts_are_excluded_by_default() -> None:
    frame = pd.DataFrame(
        {
            "region": ["Kyivska oblast", "Kyivska oblast"],
            "started_at": pd.to_datetime(
                ["2024-08-01 08:00:00+00:00", "2024-08-01 10:00:00+00:00"],
                utc=True,
            ),
            "finished_at": pd.to_datetime(["2024-08-01 09:00:00+00:00", None], utc=True),
            "source": ["official", "official"],
        }
    )

    default_daily = build_daily_region_timeseries(frame)
    inclusive_daily = build_daily_region_timeseries(frame, include_unfinished=True)

    assert default_daily.loc[0, "alert_count"] == 1
    assert inclusive_daily.loc[0, "alert_count"] == 2


def test_output_contains_deterministic_explanation_text() -> None:
    frame = _alert_rows([1] * 20 + [10])

    first = detect_daily_anomalies(frame, rolling_window=14, min_periods=7)
    second = detect_daily_anomalies(frame, rolling_window=14, min_periods=7)

    assert first["explanation"].equals(second["explanation"])
    assert first["explanation"].str.contains("worth inspecting|baseline context").all()


def test_explanations_avoid_restricted_wording() -> None:
    frame = _alert_rows([1] * 20 + [10])

    result = detect_daily_anomalies(frame, rolling_window=14, min_periods=7)
    explanation_text = " ".join(result["explanation"]).lower()

    restricted_terms = [
        "cau" + "se",
        "cau" + "sed",
        "pro" + "ves",
        "pre" + "dicts",
        "attack " + "prediction",
    ]
    assert all(term not in explanation_text for term in restricted_terms)
