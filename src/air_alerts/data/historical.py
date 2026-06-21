"""Historical air alert CSV loading utilities."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from air_alerts.data.sources import HISTORICAL_CSV_FILES, HISTORICAL_RAW_URLS


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATETIME_COLUMNS = ("started_at", "finished_at", "updated_at")
SOURCE_ORDER = ("official", "volunteer")


class HistoricalDataError(RuntimeError):
    """Raised when historical data cannot be loaded."""


class HistoricalSchemaError(ValueError):
    """Raised when a historical CSV does not match the expected schema."""


@dataclass(frozen=True)
class HistoricalSource:
    """Metadata needed to load one historical CSV source."""

    name: str
    filename: str
    required_columns: frozenset[str]


SOURCES = {
    "official": HistoricalSource(
        name="official",
        filename=HISTORICAL_CSV_FILES["official"],
        required_columns=frozenset(
            {
                "oblast",
                "raion",
                "hromada",
                "level",
                "started_at",
                "finished_at",
                "source",
            }
        ),
    ),
    "volunteer": HistoricalSource(
        name="volunteer",
        filename=HISTORICAL_CSV_FILES["volunteer"],
        required_columns=frozenset({"region", "started_at", "finished_at", "naive"}),
    ),
}


def load_historical_alerts(
    data_dir: str | Path = DEFAULT_DATA_RAW_DIR,
    *,
    allow_download: bool = True,
    sources: Iterable[str] = SOURCE_ORDER,
) -> pd.DataFrame:
    """Load and combine official and volunteer historical alert CSV files.

    The loader checks `data/raw` first, downloads missing CSVs when allowed, validates
    the expected source-specific schema, parses datetime columns, and returns all rows.
    """
    data_path = Path(data_dir)
    selected_sources = tuple(sources)
    unknown_sources = sorted(set(selected_sources).difference(SOURCES))
    if unknown_sources:
        known = ", ".join(SOURCE_ORDER)
        unknown = ", ".join(unknown_sources)
        raise HistoricalDataError(
            f"Unknown historical source(s): {unknown}. Expected one or more of: {known}."
        )

    frames = [
        _load_source(SOURCES[source], data_path, allow_download=allow_download)
        for source in selected_sources
    ]
    if not frames:
        raise HistoricalDataError("No historical sources were requested.")

    return pd.concat(frames, ignore_index=True, sort=False)


def _load_source(
    source: HistoricalSource,
    data_dir: Path,
    *,
    allow_download: bool,
) -> pd.DataFrame:
    csv_path = _ensure_local_csv(source, data_dir, allow_download=allow_download)
    frame = pd.read_csv(csv_path)
    frame = _normalize_column_names(frame)

    _validate_required_columns(frame, source)
    _parse_datetime_columns(frame, source)
    _validate_time_values(frame, source)

    frame["source"] = source.name
    return frame


def _ensure_local_csv(
    source: HistoricalSource,
    data_dir: Path,
    *,
    allow_download: bool,
) -> Path:
    csv_path = data_dir / source.filename
    if csv_path.exists():
        return csv_path

    if not allow_download:
        raise HistoricalDataError(_manual_download_message(source, data_dir))

    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(HISTORICAL_RAW_URLS[source.name], csv_path)
    except (OSError, urllib.error.URLError) as exc:
        if csv_path.exists():
            csv_path.unlink()
        raise HistoricalDataError(_manual_download_message(source, data_dir)) from exc

    return csv_path


def _manual_download_message(source: HistoricalSource, data_dir: Path) -> str:
    return (
        f"Could not load {source.filename}. Please manually download it from the "
        "Vadimkin/ukrainian-air-raid-sirens-dataset GitHub repository and place it in "
        f"{data_dir}."
    )


def _normalize_column_names(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [_normalize_column_name(column) for column in normalized.columns]
    return normalized


def _normalize_column_name(column: object) -> str:
    name = str(column).strip().lower()
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    return name.strip("_")


def _validate_required_columns(frame: pd.DataFrame, source: HistoricalSource) -> None:
    missing = sorted(source.required_columns.difference(frame.columns))
    if missing:
        actual = ", ".join(frame.columns)
        expected = ", ".join(sorted(source.required_columns))
        missing_text = ", ".join(missing)
        raise HistoricalSchemaError(
            f"{source.filename} is missing required column(s): {missing_text}. "
            f"Expected at least: {expected}. Actual columns: {actual}."
        )


def _parse_datetime_columns(frame: pd.DataFrame, source: HistoricalSource) -> None:
    for column in DATETIME_COLUMNS:
        if column in frame.columns:
            original = frame[column]
            parsed = pd.to_datetime(original, errors="coerce", utc=True)
            invalid = original.notna() & parsed.isna()
            if invalid.any():
                bad_count = int(invalid.sum())
                raise HistoricalSchemaError(
                    f"{source.filename} has {bad_count} row(s) with invalid {column} "
                    "datetime values."
                )
            frame[column] = parsed

    if frame["started_at"].isna().any():
        bad_count = int(frame["started_at"].isna().sum())
        raise HistoricalSchemaError(
            f"{source.filename} has {bad_count} row(s) with empty or invalid started_at. "
            "started_at is required for every alert row."
        )


def _validate_time_values(frame: pd.DataFrame, source: HistoricalSource) -> None:
    finished = frame["finished_at"].notna()
    negative_duration = finished & (frame["finished_at"] < frame["started_at"])
    if negative_duration.any():
        bad_count = int(negative_duration.sum())
        raise HistoricalSchemaError(
            f"{source.filename} has {bad_count} row(s) where finished_at is before "
            "started_at. Alert durations must not be negative."
        )
