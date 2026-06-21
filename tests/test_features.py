from __future__ import annotations

import pandas as pd

from air_alerts.features import add_historical_features, daily_alert_count


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
