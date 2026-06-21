"""Map data preparation and Plotly visualization helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GEOJSON_PATH = PROJECT_ROOT / "data" / "geo" / "ukraine_oblasts.geojson"
GEOJSON_NAME_KEYS = ("name", "NAME_1", "shapeName", "admin1Name", "oblast", "region")

STATUS_LABELS = {
    "active": "Active alert",
    "partial": "Partial alert",
    "no_alert": "No alert",
    "unknown": "Unknown",
}
STATUS_COLOR_MAP = {
    "active": "#d7263d",
    "partial": "#f08a24",
    "no_alert": "#e9e4d8",
    "unknown": "#d7dce2",
}
STATUS_RANK = {
    "unknown": 0,
    "no_alert": 1,
    "partial": 2,
    "active": 3,
}

DIRECT_REGION_NAME_ALIASES = {
    "\u0430\u0432\u0442\u043e\u043d\u043e\u043c\u043d\u0430 \u0440\u0435\u0441\u043f\u0443\u0431\u043b\u0456\u043a\u0430 \u043a\u0440\u0438\u043c": "Autonomous Republic of Crimea",
    "\u0432\u043e\u043b\u0438\u043d\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Volyn Oblast",
    "\u0432\u0456\u043d\u043d\u0438\u0446\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Vinnytsia Oblast",
    "\u0434\u043d\u0456\u043f\u0440\u043e\u043f\u0435\u0442\u0440\u043e\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Dnipropetrovsk Oblast",
    "\u0434\u043e\u043d\u0435\u0446\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Donetsk Oblast",
    "\u0436\u0438\u0442\u043e\u043c\u0438\u0440\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Zhytomyr Oblast",
    "\u0437\u0430\u043a\u0430\u0440\u043f\u0430\u0442\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Zakarpattia Oblast",
    "\u0437\u0430\u043f\u043e\u0440\u0456\u0437\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Zaporizhzhia Oblast",
    "\u0456\u0432\u0430\u043d\u043e-\u0444\u0440\u0430\u043d\u043a\u0456\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Ivano-Frankivsk Oblast",
    "\u043c. \u043a\u0438\u0457\u0432": "Kyiv City",
    "\u043a\u0438\u0457\u0432": "Kyiv City",
    "\u043a\u0438\u0457\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Kyiv Oblast",
    "\u043a\u0456\u0440\u043e\u0432\u043e\u0433\u0440\u0430\u0434\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Kirovohrad Oblast",
    "\u043b\u0443\u0433\u0430\u043d\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Luhansk Oblast",
    "\u043b\u044c\u0432\u0456\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Lviv Oblast",
    "\u043c\u0438\u043a\u043e\u043b\u0430\u0457\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Mykolaiv Oblast",
    "\u043e\u0434\u0435\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Odesa Oblast",
    "\u043f\u043e\u043b\u0442\u0430\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Poltava Oblast",
    "\u0440\u0456\u0432\u043d\u0435\u043d\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Rivne Oblast",
    "\u043c. \u0441\u0435\u0432\u0430\u0441\u0442\u043e\u043f\u043e\u043b\u044c": "Sevastopol City",
    "\u0441\u0443\u043c\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Sumy Oblast",
    "\u0442\u0435\u0440\u043d\u043e\u043f\u0456\u043b\u044c\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Ternopil Oblast",
    "\u0445\u0430\u0440\u043a\u0456\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Kharkiv Oblast",
    "\u0445\u0435\u0440\u0441\u043e\u043d\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Kherson Oblast",
    "\u0445\u043c\u0435\u043b\u044c\u043d\u0438\u0446\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Khmelnytskyi Oblast",
    "\u0447\u0435\u0440\u043a\u0430\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Cherkasy Oblast",
    "\u0447\u0435\u0440\u043d\u0456\u0432\u0435\u0446\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Chernivtsi Oblast",
    "\u0447\u0435\u0440\u043d\u0456\u0433\u0456\u0432\u0441\u044c\u043a\u0430 \u043e\u0431\u043b\u0430\u0441\u0442\u044c": "Chernihiv Oblast",
}

REGION_NAME_ALIASES = {
    "autonomous republic of crimea": "Autonomous Republic of Crimea",
    "crimea": "Autonomous Republic of Crimea",
    "volyn oblast": "Volyn Oblast",
    "volynska oblast": "Volyn Oblast",
    "vinnytsia oblast": "Vinnytsia Oblast",
    "vinnytska oblast": "Vinnytsia Oblast",
    "dnipropetrovsk oblast": "Dnipropetrovsk Oblast",
    "dnipropetrovska oblast": "Dnipropetrovsk Oblast",
    "donetsk oblast": "Donetsk Oblast",
    "donetska oblast": "Donetsk Oblast",
    "zhytomyr oblast": "Zhytomyr Oblast",
    "zhytomyrska oblast": "Zhytomyr Oblast",
    "zakarpattia oblast": "Zakarpattia Oblast",
    "zakarpatska oblast": "Zakarpattia Oblast",
    "zaporizhzhia oblast": "Zaporizhzhia Oblast",
    "zaporizka oblast": "Zaporizhzhia Oblast",
    "ivano frankivsk oblast": "Ivano-Frankivsk Oblast",
    "ivano frankivska oblast": "Ivano-Frankivsk Oblast",
    "kyiv city": "Kyiv City",
    "kyiv": "Kyiv City",
    "m kyiv": "Kyiv City",
    "kyiv oblast": "Kyiv Oblast",
    "kyivska oblast": "Kyiv Oblast",
    "kirovohrad oblast": "Kirovohrad Oblast",
    "kirovohradska oblast": "Kirovohrad Oblast",
    "luhansk oblast": "Luhansk Oblast",
    "luhanska oblast": "Luhansk Oblast",
    "lviv oblast": "Lviv Oblast",
    "lvivska oblast": "Lviv Oblast",
    "mykolaiv oblast": "Mykolaiv Oblast",
    "mykolaivska oblast": "Mykolaiv Oblast",
    "odesa oblast": "Odesa Oblast",
    "odeska oblast": "Odesa Oblast",
    "poltava oblast": "Poltava Oblast",
    "poltavska oblast": "Poltava Oblast",
    "rivne oblast": "Rivne Oblast",
    "rivnenska oblast": "Rivne Oblast",
    "sevastopol city": "Sevastopol City",
    "sevastopol": "Sevastopol City",
    "sumy oblast": "Sumy Oblast",
    "sumska oblast": "Sumy Oblast",
    "ternopil oblast": "Ternopil Oblast",
    "ternopilska oblast": "Ternopil Oblast",
    "kharkiv oblast": "Kharkiv Oblast",
    "kharkivska oblast": "Kharkiv Oblast",
    "kherson oblast": "Kherson Oblast",
    "khersonska oblast": "Kherson Oblast",
    "khmelnytskyi oblast": "Khmelnytskyi Oblast",
    "khmelnytska oblast": "Khmelnytskyi Oblast",
    "cherkasy oblast": "Cherkasy Oblast",
    "cherkaska oblast": "Cherkasy Oblast",
    "chernivtsi oblast": "Chernivtsi Oblast",
    "chernivetska oblast": "Chernivtsi Oblast",
    "chernihiv oblast": "Chernihiv Oblast",
    "chernihivska oblast": "Chernihiv Oblast",
}


@dataclass(frozen=True)
class MapDataResult:
    """Prepared data and GeoJSON state for the live map page."""

    statuses: pd.DataFrame
    geojson: dict[str, Any] | None
    map_data: pd.DataFrame
    geojson_path: Path
    geojson_missing: bool
    unmatched_geojson_regions: tuple[str, ...] = ()


def normalize_region_name(value: object) -> str:
    """Normalize region names for explicit API-to-GeoJSON joins."""
    if value is None or pd.isna(value):
        return ""
    raw_text = str(value).strip().lower()
    if raw_text in DIRECT_REGION_NAME_ALIASES:
        return DIRECT_REGION_NAME_ALIASES[raw_text]
    text = raw_text
    text = text.replace("'", "")
    text = re.sub(r"[^0-9a-z]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return REGION_NAME_ALIASES.get(text, text.title())


def get_status_color(status: object) -> str:
    """Return the display color for a normalized live status."""
    normalized = str(status or "unknown").strip().lower()
    return STATUS_COLOR_MAP.get(normalized, STATUS_COLOR_MAP["unknown"])


def prepare_live_map_data(
    statuses: pd.DataFrame,
    geojson_path: str | Path = DEFAULT_GEOJSON_PATH,
) -> MapDataResult:
    """Prepare live status data for a future map or fallback table."""
    normalized_statuses = _normalize_status_frame(statuses)
    path = Path(geojson_path)
    if not path.exists():
        return MapDataResult(
            statuses=normalized_statuses,
            geojson=None,
            map_data=normalized_statuses.copy(),
            geojson_path=path,
            geojson_missing=True,
        )

    geojson = _load_geojson(path)
    geo_regions = _extract_geojson_regions(geojson)
    geo_frame = pd.DataFrame(geo_regions)
    map_data = geo_frame.merge(
        normalized_statuses,
        on="region_key",
        how="left",
        suffixes=("", "_status"),
    )
    unmatched_mask = map_data["status"].isna()
    map_data["oblast"] = map_data["oblast"].fillna(map_data["geojson_region_name"])
    map_data["status"] = map_data["status"].fillna("unknown")
    if "status_code" not in map_data.columns:
        map_data["status_code"] = pd.Series([None] * len(map_data), dtype=object)
    else:
        map_data["status_code"] = map_data["status_code"].astype(object)
        map_data.loc[map_data["status_code"].isna(), "status_code"] = None
    if "is_active" not in map_data.columns:
        map_data["is_active"] = False
    else:
        map_data["is_active"] = map_data["is_active"].fillna(False).astype(bool)
    map_data.loc[unmatched_mask, "status"] = "unknown"
    map_data.loc[unmatched_mask, "status_code"] = None
    map_data.loc[unmatched_mask, "is_active"] = False
    map_data["status_label"] = map_data["status"].map(STATUS_LABELS).fillna("Unknown")
    map_data["status_rank"] = map_data["status"].map(STATUS_RANK).fillna(0).astype(int)
    map_data["status_color"] = map_data["status"].map(get_status_color)

    unmatched = tuple(map_data.loc[unmatched_mask, "geojson_region_name"].dropna())
    return MapDataResult(
        statuses=normalized_statuses,
        geojson=geojson,
        map_data=map_data,
        geojson_path=path,
        geojson_missing=False,
        unmatched_geojson_regions=unmatched,
    )


def build_live_status_choropleth(map_result: MapDataResult) -> go.Figure:
    """Build a Plotly choropleth for prepared live status data."""
    if map_result.geojson_missing or map_result.geojson is None:
        raise ValueError("Cannot build choropleth without a GeoJSON file.")

    figure = px.choropleth(
        map_result.map_data,
        geojson=map_result.geojson,
        locations="feature_id",
        featureidkey="id",
        color="status",
        category_orders={"status": ["active", "partial", "no_alert", "unknown"]},
        color_discrete_map=STATUS_COLOR_MAP,
        hover_name="oblast",
        hover_data={"status_label": True, "feature_id": False, "status": False},
    )
    figure.update_geos(fitbounds="locations", visible=False)
    figure.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="Status",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def status_summary(statuses: pd.DataFrame) -> pd.DataFrame:
    """Summarize live statuses for a compact table."""
    normalized = _normalize_status_frame(statuses)
    return (
        normalized.groupby("status_label", dropna=False)
        .size()
        .reset_index(name="oblast_count")
        .sort_values("status_label", ignore_index=True)
    )


def _normalize_status_frame(statuses: pd.DataFrame) -> pd.DataFrame:
    required = {"oblast", "status"}
    missing = sorted(required.difference(statuses.columns))
    if missing:
        raise ValueError(f"Missing live status column(s): {', '.join(missing)}.")

    normalized = statuses.copy()
    normalized["status"] = normalized["status"].fillna("unknown").astype(str).str.lower()
    normalized.loc[~normalized["status"].isin(STATUS_COLOR_MAP), "status"] = "unknown"
    normalized["region_key"] = normalized["oblast"].map(normalize_region_name)
    normalized["status_label"] = normalized["status"].map(STATUS_LABELS).fillna("Unknown")
    normalized["status_color"] = normalized["status"].map(get_status_color)
    normalized["status_rank"] = normalized["status"].map(STATUS_RANK).fillna(0).astype(int)
    if "is_active" not in normalized.columns:
        normalized["is_active"] = normalized["status"].isin({"active", "partial"})
    return normalized


def _load_geojson(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        geojson = json.load(file)
    if not isinstance(geojson, dict) or not isinstance(geojson.get("features"), list):
        raise ValueError("GeoJSON must be a FeatureCollection with features.")
    return _ensure_feature_ids(geojson)


def _ensure_feature_ids(geojson: dict[str, Any]) -> dict[str, Any]:
    for index, feature in enumerate(geojson["features"]):
        feature.setdefault("id", str(feature.get("id", index)))
    return geojson


def _extract_geojson_regions(geojson: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for feature in geojson["features"]:
        properties = feature.get("properties", {})
        region_name = _region_name_from_properties(properties)
        feature_id = str(feature.get("id"))
        rows.append(
            {
                "feature_id": feature_id,
                "geojson_region_name": region_name,
                "region_key": normalize_region_name(region_name),
            }
        )
    return rows


def _region_name_from_properties(properties: dict[str, Any]) -> str:
    for key in GEOJSON_NAME_KEYS:
        value = properties.get(key)
        if value:
            return str(value)
    raise ValueError(
        "GeoJSON feature is missing a supported region name property. "
        f"Expected one of: {', '.join(GEOJSON_NAME_KEYS)}."
    )
