from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from air_alerts.metrics import (
    audit_metric_pipeline_by_year,
    daily_oblast_metrics,
    debug_national_day_metrics,
    debug_region_yearly_counts,
    hourly_weekday_episode_matrix,
    merge_overlapping_intervals,
    national_daily_metrics,
    prepare_metric_events,
    split_intervals_by_day,
)


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_sample_row_duration_is_exact_for_metric_events() -> None:
    events = prepare_metric_events(
        _frame(
            [
                {
                    "oblast": "Vinnytska oblast",
                    "raion": None,
                    "hromada": None,
                    "level": "oblast",
                    "started_at": pd.Timestamp("2022-03-15 16:10:34+00:00"),
                    "finished_at": pd.Timestamp("2022-03-15 16:50:07+00:00"),
                    "source": "official",
                }
            ]
        )
    )
    merged = merge_overlapping_intervals(events)

    assert merged.loc[0, "duration_seconds"] == 2373
    assert merged.loc[0, "affected_oblast_hours"] == pytest.approx(2373 / 3600)


def test_daily_split_across_midnight_uses_kyiv_dates() -> None:
    events = prepare_metric_events(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "started_at": pd.Timestamp("2024-01-01 21:30:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 22:30:00+00:00"),
                }
            ]
        )
    )

    split = split_intervals_by_day(merge_overlapping_intervals(events))

    assert list(split["date"]) == [date(2024, 1, 1), date(2024, 1, 2)]
    assert list(split["affected_hours"]) == pytest.approx([0.5, 0.5])


def test_multi_day_split_allocates_each_calendar_day() -> None:
    events = prepare_metric_events(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "started_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-03 04:00:00+00:00"),
                }
            ]
        )
    )

    split = split_intervals_by_day(merge_overlapping_intervals(events))

    assert list(split["date"]) == [
        date(2024, 1, 1),
        date(2024, 1, 2),
        date(2024, 1, 3),
    ]
    assert list(split["affected_hours"]) == pytest.approx([12, 24, 6])


def test_overlapping_intervals_in_one_oblast_are_counted_once() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 10:30:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 12:00:00+00:00"),
                },
            ]
        )
    )

    assert daily.loc[0, "oblast_episode_count"] == 1
    assert daily.loc[0, "affected_oblast_hours"] == pytest.approx(4)


def test_duplicate_identical_official_rows_do_not_increase_episode_count() -> None:
    row = {
        "source": "official",
        "oblast": "Kyivska oblast",
        "raion": "Bucha raion",
        "hromada": "Irpin hromada",
        "level": "hromada",
        "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
        "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
    }

    daily = daily_oblast_metrics(_frame([row, row.copy(), row.copy()]))

    assert daily.loc[0, "oblast_episode_count"] == 1
    assert daily.loc[0, "affected_oblast_hours"] == pytest.approx(1)


def test_touching_intervals_in_one_oblast_are_one_episode() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 10:03:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
                },
            ]
        )
    )

    assert daily.loc[0, "oblast_episode_count"] == 1
    assert daily.loc[0, "affected_oblast_hours"] == pytest.approx(3)


def test_intervals_beyond_merge_gap_are_separate_episodes() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 09:10:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 10:20:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
                },
            ]
        )
    )

    assert daily.loc[0, "oblast_episode_count"] == 3


def test_raion_and_hromada_rows_aggregate_under_oblast() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "oblast": "Kyivska oblast",
                    "level": "oblast",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                },
                {
                    "oblast": "Kyivska oblast",
                    "level": "raion",
                    "started_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
                },
                {
                    "oblast": "Kyivska oblast",
                    "level": "hromada",
                    "started_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 12:00:00+00:00"),
                },
            ]
        )
    )

    assert daily.loc[0, "oblast_episode_count"] == 1
    assert daily.loc[0, "region"] == "Kyivska oblast"
    assert daily.loc[0, "affected_oblast_hours"] == pytest.approx(4)


def test_official_source_is_default_for_metrics() -> None:
    frame = _frame(
        [
            {
                "region": "Kyiv Oblast",
                "source": "official",
                "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
            },
            {
                "region": "Kyiv Oblast",
                "source": "volunteer",
                "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
            },
        ]
    )

    default_daily = daily_oblast_metrics(frame)

    assert default_daily.loc[0, "oblast_episode_count"] == 1
    assert default_daily.loc[0, "affected_oblast_hours"] == pytest.approx(1)


def test_explicit_both_sources_can_include_volunteer_intervals() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "volunteer",
                    "started_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
                },
            ]
        ),
        sources=("official", "volunteer"),
    )

    assert daily.loc[0, "oblast_episode_count"] == 2
    assert daily.loc[0, "affected_oblast_hours"] == pytest.approx(2)


def test_explicit_both_sources_keeps_source_rows_for_preparation() -> None:
    events = prepare_metric_events(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "volunteer",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
            ]
        ),
        sources=("official", "volunteer"),
    )

    assert set(events["source"]) == {"official", "volunteer"}


def test_m_kyiv_and_kyivska_oblast_remain_separate_regions() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "oblast": "m. Kyiv",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
                {
                    "oblast": "Kyivska oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
            ]
        )
    )

    assert set(daily["region"]) == {"m. Kyiv", "Kyivska oblast"}


def test_daily_alert_start_count_uses_merged_episode_start_date() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 21:58:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 22:10:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 22:01:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 22:30:00+00:00"),
                },
            ]
        )
    )

    assert list(daily["date"]) == [date(2024, 1, 1), date(2024, 1, 2)]
    assert list(daily["oblast_episode_count"]) == [1, 0]


def test_national_wave_count_merges_across_oblasts() -> None:
    national = national_daily_metrics(
        _frame(
            [
                {
                    "oblast": "Kyivska oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                },
                {
                    "oblast": "Lvivska oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:30:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 10:30:00+00:00"),
                },
                {
                    "oblast": "Odeska oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
                },
            ]
        )
    )

    assert national.loc[0, "national_alert_wave_count"] == 1
    assert national.loc[0, "national_oblast_episode_count"] == 3
    assert national.loc[0, "active_oblasts_count"] == 3


def test_hourly_weekday_matrix_uses_merged_episode_starts() -> None:
    matrix = hourly_weekday_episode_matrix(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-01-01 08:10:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:10:00+00:00"),
                },
            ]
        )
    )

    assert int(matrix.to_numpy().sum()) == 1


def test_debug_national_day_metrics_reports_duplicates_and_waves() -> None:
    row = {
        "oblast": "Kyivska oblast",
        "source": "official",
        "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
        "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
    }

    debug = debug_national_day_metrics(_frame([row, row.copy()]), "2024-01-01")

    assert debug["raw_records_count"] == 2
    assert debug["duplicate_raw_records_count"] == 1
    assert debug["oblast_episode_starts"] == 1
    assert debug["national_alert_waves"] == 1


def test_non_overlapping_intervals_in_one_oblast_are_summed() -> None:
    daily = daily_oblast_metrics(
        _frame(
            [
                {
                    "region": "Kyiv Oblast",
                    "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                },
                {
                    "region": "Kyiv Oblast",
                    "started_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
                },
            ]
        )
    )

    assert daily.loc[0, "affected_oblast_hours"] == pytest.approx(2)


def test_national_daily_hours_do_not_exceed_24_times_regions_present() -> None:
    frame = _frame(
        [
            {
                "region": "Kyiv Oblast",
                "started_at": pd.Timestamp("2024-01-01 00:00:00+02:00"),
                "finished_at": pd.Timestamp("2024-01-02 00:00:00+02:00"),
            },
            {
                "region": "Kyiv Oblast",
                "started_at": pd.Timestamp("2024-01-01 06:00:00+02:00"),
                "finished_at": pd.Timestamp("2024-01-01 18:00:00+02:00"),
            },
            {
                "region": "Lviv Oblast",
                "started_at": pd.Timestamp("2024-01-01 12:00:00+02:00"),
                "finished_at": pd.Timestamp("2024-01-02 00:00:00+02:00"),
            },
        ]
    )

    national = national_daily_metrics(frame)
    daily = daily_oblast_metrics(frame)
    region_counts = daily.groupby("date")["region"].nunique()

    for row in national.itertuples(index=False):
        assert row.affected_oblast_hours <= 24 * region_counts.loc[row.date]


def test_audit_metric_pipeline_by_year_preserves_expected_stage_counts() -> None:
    duplicate_row = {
        "oblast": "Kyivska oblast",
        "source": "official",
        "level": "oblast",
        "started_at": pd.Timestamp("2023-01-01 08:00:00+00:00"),
        "finished_at": pd.Timestamp("2023-01-01 09:00:00+00:00"),
    }
    frame = _frame(
        [
            duplicate_row,
            duplicate_row.copy(),
            {
                "oblast": "Kyivska oblast",
                "source": "official",
                "level": "raion",
                "started_at": pd.Timestamp("2024-01-01 08:00:00+00:00"),
                "finished_at": pd.Timestamp("2024-01-01 10:00:00+00:00"),
            },
            {
                "oblast": "Kyivska oblast",
                "source": "official",
                "level": "hromada",
                "started_at": pd.Timestamp("2024-01-01 09:00:00+00:00"),
                "finished_at": pd.Timestamp("2024-01-01 11:00:00+00:00"),
            },
            {
                "oblast": "Kyivska oblast",
                "source": "official",
                "level": "oblast",
                "started_at": pd.Timestamp("2025-01-01 08:00:00+00:00"),
                "finished_at": pd.Timestamp("2025-01-01 09:00:00+00:00"),
            },
            {
                "oblast": "Kyivska oblast",
                "source": "volunteer",
                "level": "oblast",
                "started_at": pd.Timestamp("2025-01-01 10:00:00+00:00"),
                "finished_at": pd.Timestamp("2025-01-01 11:00:00+00:00"),
            },
        ]
    )

    audit = audit_metric_pipeline_by_year(frame)
    by_year = audit.set_index("year")

    assert list(by_year.index) == [2023, 2024, 2025]
    assert by_year.loc[2023, "raw_loaded_rows"] == 2
    assert by_year.loc[2023, "duplicate_raw_records_count"] == 1
    assert by_year.loc[2023, "deduplicated_rows"] == 1
    assert by_year.loc[2024, "source_filtered_rows"] == 2
    assert by_year.loc[2024, "prepared_metric_intervals"] == 2
    assert by_year.loc[2024, "merged_intervals"] == 1
    assert by_year.loc[2024, "oblast_episode_count"] == 1
    assert by_year.loc[2025, "raw_loaded_rows"] == 2
    assert by_year.loc[2025, "source_filtered_rows"] == 1
    assert by_year.loc[2025, "official_only_rows"] == 1


def test_official_oblast_rows_with_missing_raion_hromada_survive_preparation() -> None:
    events = prepare_metric_events(
        _frame(
            [
                {
                    "oblast": "Dnipropetrovska oblast",
                    "raion": None,
                    "hromada": None,
                    "level": "oblast",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-02-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-02-01 09:00:00+00:00"),
                }
            ]
        )
    )

    assert len(events) == 1
    assert events.loc[0, "region"] == "Dnipropetrovska oblast"


def test_raion_hromada_rows_with_oblast_roll_up_in_audit() -> None:
    audit = audit_metric_pipeline_by_year(
        _frame(
            [
                {
                    "oblast": "Dnipropetrovska oblast",
                    "raion": "Dnipro raion",
                    "hromada": None,
                    "level": "raion",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-02-01 08:00:00+00:00"),
                    "finished_at": pd.Timestamp("2024-02-01 09:00:00+00:00"),
                },
                {
                    "oblast": "Dnipropetrovska oblast",
                    "raion": "Dnipro raion",
                    "hromada": "Dnipro hromada",
                    "level": "hromada",
                    "source": "official",
                    "started_at": pd.Timestamp("2024-02-01 08:30:00+00:00"),
                    "finished_at": pd.Timestamp("2024-02-01 09:30:00+00:00"),
                },
            ]
        )
    )

    row = audit.iloc[0]
    assert row["prepared_metric_intervals"] == 2
    assert row["merged_intervals"] == 1
    assert row["oblast_episode_count"] == 1
    assert row["levels_present"] == ["hromada", "raion"]


def test_debug_region_yearly_counts_reports_region_pipeline_stages() -> None:
    frame = _frame(
        [
            {
                "oblast": "Dnipropetrovska oblast",
                "source": "official",
                "level": "oblast",
                "started_at": pd.Timestamp("2024-02-01 08:00:00+00:00"),
                "finished_at": pd.Timestamp("2024-02-01 09:00:00+00:00"),
            },
            {
                "oblast": "Dnipropetrovska oblast",
                "source": "official",
                "level": "raion",
                "started_at": pd.Timestamp("2024-02-01 08:30:00+00:00"),
                "finished_at": pd.Timestamp("2024-02-01 09:30:00+00:00"),
            },
        ]
    )

    debug = debug_region_yearly_counts(
        frame,
        "Dnipropetrovska oblast",
    )
    row = debug.iloc[0]

    assert row["year"] == 2024
    assert row["raw_records"] == 2
    assert row["prepared_intervals"] == 2
    assert row["merged_episodes"] == 1
    assert row["oblast_episode_count"] == 1
    assert row["affected_oblast_hours"] == pytest.approx(1.5)
    assert row["levels_present"] == ["oblast", "raion"]
