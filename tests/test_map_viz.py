from __future__ import annotations

import json

import pandas as pd

from air_alerts.map_viz import (
    get_status_color,
    normalize_region_name,
    prepare_live_map_data,
)


def test_status_color_mapping() -> None:
    assert get_status_color("active") == "#d7263d"
    assert get_status_color("partial") == "#f08a24"
    assert get_status_color("no_alert") == "#e9e4d8"
    assert get_status_color("not-a-real-status") == "#d7dce2"


def test_region_name_normalization_and_mapping() -> None:
    assert normalize_region_name("Kyivska oblast") == "Kyiv Oblast"
    assert normalize_region_name("m. Kyiv") == "Kyiv City"
    assert normalize_region_name("  Odeska   oblast ") == "Odesa Oblast"
    assert normalize_region_name("\u041a\u0438\u0457\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c") == "Kyiv Oblast"


def test_missing_geojson_returns_missing_state(tmp_path) -> None:
    statuses = pd.DataFrame(
        {
            "oblast": ["Kyiv Oblast"],
            "status": ["active"],
            "status_code": ["A"],
            "is_active": [True],
        }
    )

    result = prepare_live_map_data(statuses, tmp_path / "missing.geojson")

    assert result.geojson_missing is True
    assert result.geojson is None
    assert list(result.map_data["oblast"]) == ["Kyiv Oblast"]


def test_prepare_live_map_data_joins_statuses_to_geojson(tmp_path) -> None:
    geojson_path = tmp_path / "ukraine_oblasts.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": "kyiv-oblast",
                        "properties": {"name": "Kyivska oblast"},
                        "geometry": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    statuses = pd.DataFrame(
        {
            "oblast": ["Kyiv Oblast"],
            "status": ["partial"],
            "status_code": ["P"],
            "is_active": [True],
        }
    )

    result = prepare_live_map_data(statuses, geojson_path)

    assert result.geojson_missing is False
    assert result.map_data.loc[0, "feature_id"] == "kyiv-oblast"
    assert result.map_data.loc[0, "status"] == "partial"
    expected_columns = {
        "feature_id",
        "geojson_region_name",
        "region_key",
        "oblast",
        "status",
        "status_code",
        "status_label",
        "status_color",
        "status_rank",
    }
    assert expected_columns.issubset(result.map_data.columns)


def test_prepare_live_map_data_marks_unmatched_geojson_region_unknown(tmp_path) -> None:
    geojson_path = tmp_path / "ukraine_oblasts.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": "kyiv-oblast",
                        "properties": {"name": "Kyivska oblast"},
                        "geometry": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    statuses = pd.DataFrame(
        {
            "oblast": ["Odesa Oblast"],
            "status": ["active"],
            "status_code": ["A"],
            "is_active": [True],
        }
    )

    result = prepare_live_map_data(statuses, geojson_path)

    assert result.map_data.loc[0, "status"] == "unknown"
    assert result.map_data.loc[0, "status_code"] is None
    assert result.unmatched_geojson_regions == ("Kyivska oblast",)
