from __future__ import annotations

import pandas as pd
import pytest

from air_alerts.features import (
    add_historical_features,
    allocate_alert_duration_by_day,
    daily_alert_count,
    daily_alert_duration,
    largest_daily_duration_values,
    largest_raw_alert_durations,
)


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "oblast": ["Kyivska oblast", None, "Lvivska oblast"],
            "region": [None, "Kyiv City", None],
            "started_at": pd.to_datetime(
                [
                    "2022-03-26 22:30:00+00:00",
                    "2022-03-27 01:00:00+00:00",
                    "2022-03-27 05:00:00+00:00",
                ],
                utc=True,
            ),
            "finished_at": pd.to_datetime(
                [
                    "2022-03-26 23:45:00+00:00",
                    "2022-03-27 01:30:00+00:00",
                    None,
                ],
                utc=True,
            ),
            "source": ["official", "volunteer", "official"],
        }
    )


def test_add_historical_features_converts_to_kyiv_timezone() -> None:
    frame = add_historical_features(_sample_frame())

    assert str(frame["started_at_kyiv"].dt.tz) == "Europe/Kyiv"
    assert str(frame["finished_at_kyiv"].dt.tz) == "Europe/Kyiv"
    assert frame.loc[0, "started_at"].hour == 22
    assert frame.loc[0, "started_at_kyiv"].hour == 0
    assert frame.loc[0, "date"].isoformat() == "2022-03-27"


def test_add_historical_features_calculates_duration() -> None:
    frame = add_historical_features(_sample_frame())

    assert frame.loc[0, "duration_minutes"] == 75
    assert frame.loc[0, "duration_hours"] == 1.25
    assert pd.isna(frame.loc[2, "duration_minutes"])
    assert bool(frame.loc[2, "is_finished"]) is False


def test_sample_row_duration_is_exact() -> None:
    frame = add_historical_features(
        pd.DataFrame(
            {
                "oblast": ["Vinnytska oblast"],
                "raion": [None],
                "hromada": [None],
                "level": ["oblast"],
                "started_at": pd.to_datetime(["2022-03-15 16:10:34+00:00"], utc=True),
                "finished_at": pd.to_datetime(["2022-03-15 16:50:07+00:00"], utc=True),
                "source": ["official"],
            }
        )
    )

    assert round(frame.loc[0, "duration_minutes"] * 60) == 2373
    assert frame.loc[0, "duration_hours"] == pytest.approx(2373 / 3600)


def test_midnight_crossing_duration_splits_across_kyiv_dates() -> None:
    frame = add_historical_features(
        pd.DataFrame(
            {
                "region": ["Kyiv Oblast"],
                "started_at": pd.to_datetime(["2024-01-01 21:30:00+00:00"], utc=True),
                "finished_at": pd.to_datetime(["2024-01-01 22:30:00+00:00"], utc=True),
            }
        )
    )

    allocated = allocate_alert_duration_by_day(frame)

    assert list(allocated["date"].astype(str)) == ["2024-01-01", "2024-01-02"]
    assert list(allocated["duration_hours"]) == pytest.approx([0.5, 0.5])


def test_multi_day_duration_splits_across_all_kyiv_dates() -> None:
    frame = add_historical_features(
        pd.DataFrame(
            {
                "region": ["Kyiv Oblast"],
                "started_at": pd.to_datetime(["2024-01-01 10:00:00+00:00"], utc=True),
                "finished_at": pd.to_datetime(["2024-01-03 04:00:00+00:00"], utc=True),
            }
        )
    )

    allocated = allocate_alert_duration_by_day(frame)

    assert list(allocated["date"].astype(str)) == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
    ]
    assert list(allocated["duration_hours"]) == pytest.approx([12, 24, 6])


def test_daily_alert_duration_uses_split_allocation() -> None:
    frame = pd.DataFrame(
        {
            "region": ["Kyiv Oblast"],
            "started_at": pd.to_datetime(["2024-01-01 21:30:00+00:00"], utc=True),
            "finished_at": pd.to_datetime(["2024-01-01 22:30:00+00:00"], utc=True),
        }
    )

    daily = daily_alert_duration(frame)

    assert list(daily["date"].astype(str)) == ["2024-01-01", "2024-01-02"]
    assert list(daily["total_duration_hours"]) == pytest.approx([0.5, 0.5])


def test_daily_alert_duration_excludes_unfinished_by_default() -> None:
    frame = pd.DataFrame(
        {
            "region": ["Kyiv Oblast", "Kyiv Oblast"],
            "started_at": pd.to_datetime(
                ["2024-01-01 10:00:00+00:00", "2024-01-01 12:00:00+00:00"],
                utc=True,
            ),
            "finished_at": pd.to_datetime(["2024-01-01 11:00:00+00:00", None], utc=True),
        }
    )

    daily = daily_alert_duration(frame)

    assert len(daily) == 1
    assert daily.loc[0, "total_duration_hours"] == 1


def test_duration_diagnostic_helpers_return_largest_values() -> None:
    frame = pd.DataFrame(
        {
            "region": ["Kyiv Oblast", "Kyiv Oblast"],
            "started_at": pd.to_datetime(
                ["2024-01-01 10:00:00+00:00", "2024-01-02 10:00:00+00:00"],
                utc=True,
            ),
            "finished_at": pd.to_datetime(
                ["2024-01-01 11:00:00+00:00", "2024-01-02 13:00:00+00:00"],
                utc=True,
            ),
        }
    )

    raw = largest_raw_alert_durations(frame, limit=1)
    daily = largest_daily_duration_values(frame, limit=1)

    assert raw.iloc[0]["duration_hours"] == 3
    assert daily.iloc[0]["total_duration_hours"] == 3


def test_unfinished_alerts_are_excluded_from_counts_by_default() -> None:
    raw = _sample_frame()

    default_counts = daily_alert_count(raw)
    inclusive_counts = daily_alert_count(raw, include_unfinished=True)

    assert int(default_counts["alert_count"].sum()) == 2
    assert int(inclusive_counts["alert_count"].sum()) == 3


def test_official_and_volunteer_rows_get_grouping_region() -> None:
    frame = add_historical_features(_sample_frame())

    assert frame.loc[0, "region"] == "Kyivska oblast"
    assert frame.loc[1, "region"] == "Kyiv City"
    assert frame.loc[2, "region"] == "Lvivska oblast"
    assert "oblast" in frame.columns


def test_daily_alert_count_groups_by_kyiv_local_date() -> None:
    counts = daily_alert_count(_sample_frame())

    assert list(counts.columns) == ["date", "alert_count"]
    assert counts.loc[0, "date"].isoformat() == "2022-03-27"
    assert counts.loc[0, "alert_count"] == 2
