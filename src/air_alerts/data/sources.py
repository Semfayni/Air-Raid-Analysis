"""Known data sources for future implementation."""

from __future__ import annotations

HISTORICAL_DATASET_URL = "https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset"
HISTORICAL_DATASET_RAW_BASE_URL = (
    "https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset"
    "/main/datasets"
)
HISTORICAL_CSV_FILES = {
    "official": "official_data_en.csv",
    "volunteer": "volunteer_data_en.csv",
}
HISTORICAL_RAW_URLS = {
    source: f"{HISTORICAL_DATASET_RAW_BASE_URL}/{filename}"
    for source, filename in HISTORICAL_CSV_FILES.items()
}
LIVE_ALERTS_API_URL = "https://devs.alerts.in.ua/"
