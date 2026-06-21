from __future__ import annotations

import pandas as pd
import pytest
from pandas.api.types import is_datetime64_any_dtype

from air_alerts.data import HistoricalSchemaError, load_historical_alerts


def _write_csv(path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _assert_utc_datetime_column(series: pd.Series) -> None:
    assert is_datetime64_any_dtype(series)
    assert isinstance(series.dtype, pd.DatetimeTZDtype)
    assert str(series.dtype.tz) == "UTC"


def test_load_historical_alerts_adds_source_column(tmp_path) -> None:
    _write_csv(
        tmp_path / "official_data_en.csv",
        "\n".join(
            [
                "oblast,raion,hromada,level,started_at,finished_at,source",
                "Kyivska oblast,,,oblast,2022-03-15 16:10:34+00:00,2022-03-15 16:50:07+00:00,official",
            ]
        ),
    )
    _write_csv(
        tmp_path / "volunteer_data_en.csv",
        "\n".join(
            [
                "region,started_at,finished_at,naive",
                "Kyiv City,2022-02-25 16:36:22+00:00,2022-02-25 17:06:22+00:00,True",
            ]
        ),
    )

    frame = load_historical_alerts(tmp_path, allow_download=False)

    assert list(frame["source"]) == ["official", "volunteer"]
    assert len(frame) == 2


def test_load_historical_alerts_parses_datetime_columns(tmp_path) -> None:
    _write_csv(
        tmp_path / "official_data_en.csv",
        "\n".join(
            [
                "oblast,raion,hromada,level,started_at,finished_at,source,updated_at",
                "Kyivska oblast,,,oblast,2022-03-15 16:10:34+00:00,,official,2022-03-15 16:20:00+00:00",
            ]
        ),
    )

    frame = load_historical_alerts(
        tmp_path,
        allow_download=False,
        sources=("official",),
    )

    _assert_utc_datetime_column(frame["started_at"])
    _assert_utc_datetime_column(frame["finished_at"])
    _assert_utc_datetime_column(frame["updated_at"])
    assert pd.isna(frame.loc[0, "finished_at"])


def test_load_historical_alerts_validates_required_columns(tmp_path) -> None:
    _write_csv(
        tmp_path / "volunteer_data_en.csv",
        "\n".join(
            [
                "region,finished_at,naive",
                "Kyiv City,2022-02-25 17:06:22+00:00,True",
            ]
        ),
    )

    with pytest.raises(HistoricalSchemaError, match="missing required column"):
        load_historical_alerts(
            tmp_path,
            allow_download=False,
            sources=("volunteer",),
        )


def test_load_historical_alerts_rejects_negative_duration(tmp_path) -> None:
    _write_csv(
        tmp_path / "official_data_en.csv",
        "\n".join(
            [
                "oblast,raion,hromada,level,started_at,finished_at,source",
                "Kyivska oblast,,,oblast,2022-03-15 16:50:07+00:00,2022-03-15 16:10:34+00:00,official",
            ]
        ),
    )

    with pytest.raises(HistoricalSchemaError, match="durations must not be negative"):
        load_historical_alerts(
            tmp_path,
            allow_download=False,
            sources=("official",),
        )
