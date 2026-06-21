"""Safe client for current alerts.in.ua live alert status."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
import time
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


API_BASE_URL = "https://api.alerts.in.ua"
ACTIVE_ALERTS_ENDPOINT = "/v1/alerts/active.json"
OBLAST_STATUS_ENDPOINT = "/v1/iot/active_air_raid_alerts_by_oblast.json"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_CACHE_TTL_SECONDS = 60

COMPACT_STATUS_MAP = {
    "A": "active",
    "P": "partial",
    "N": "no_alert",
}

OBLAST_STATUS_ORDER = [
    "Autonomous Republic of Crimea",
    "Volyn Oblast",
    "Vinnytsia Oblast",
    "Dnipropetrovsk Oblast",
    "Donetsk Oblast",
    "Zhytomyr Oblast",
    "Zakarpattia Oblast",
    "Zaporizhzhia Oblast",
    "Ivano-Frankivsk Oblast",
    "Kyiv City",
    "Kyiv Oblast",
    "Kirovohrad Oblast",
    "Luhansk Oblast",
    "Lviv Oblast",
    "Mykolaiv Oblast",
    "Odesa Oblast",
    "Poltava Oblast",
    "Rivne Oblast",
    "Sevastopol City",
    "Sumy Oblast",
    "Ternopil Oblast",
    "Kharkiv Oblast",
    "Kherson Oblast",
    "Khmelnytskyi Oblast",
    "Cherkasy Oblast",
    "Chernivtsi Oblast",
    "Chernihiv Oblast",
]


class AlertsApiError(RuntimeError):
    """Raised when live alerts.in.ua data cannot be loaded safely."""


class MissingAlertsApiTokenError(AlertsApiError):
    """Raised when ALERTS_API_TOKEN is not available."""


@dataclass
class _CacheEntry:
    expires_at: float
    value: Any


_CACHE: dict[tuple[str, str], _CacheEntry] = {}


def get_active_alerts(*, cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> pd.DataFrame:
    """Return currently active alerts as a normalized dataframe."""
    payload = _get_json(ACTIVE_ALERTS_ENDPOINT, cache_ttl_seconds=cache_ttl_seconds)
    return _normalize_active_alerts(payload)


def get_air_raid_statuses_by_oblast(
    *,
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
) -> pd.DataFrame:
    """Return compact current air-raid statuses by oblast as a dataframe."""
    payload = _get_json(OBLAST_STATUS_ENDPOINT, cache_ttl_seconds=cache_ttl_seconds)
    status_string = _extract_compact_status_string(payload)
    return _normalize_oblast_statuses(status_string)


def clear_live_api_cache() -> None:
    """Clear the in-memory live API cache."""
    _CACHE.clear()


def _get_json(endpoint: str, *, cache_ttl_seconds: int) -> Any:
    token = _load_token()
    cache_key = (endpoint, _token_fingerprint(token))
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{API_BASE_URL}{endpoint}"
    response = _request_json(url, token)
    _cache_set(cache_key, response, cache_ttl_seconds)
    return response


def _load_token() -> str:
    load_dotenv(override=False)
    token = os.getenv("ALERTS_API_TOKEN", "").strip()
    placeholders = {"your_token_here", "replace_with_your_alerts_in_ua_token"}
    if not token or token in placeholders:
        raise MissingAlertsApiTokenError(
            "ALERTS_API_TOKEN is not set. Add it to your local .env file."
        )
    return token


def _token_fingerprint(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _request_json(url: str, token: str) -> Any:
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise AlertsApiError("Network error while contacting alerts.in.ua API.") from exc

    _raise_for_status(response.status_code)
    try:
        return response.json()
    except ValueError as exc:
        raise AlertsApiError("Unexpected alerts.in.ua response: invalid JSON.") from exc


def _raise_for_status(status_code: int) -> None:
    if status_code == 200:
        return
    if status_code == 401:
        raise AlertsApiError("alerts.in.ua rejected the request: invalid or missing token.")
    if status_code == 403:
        raise AlertsApiError("alerts.in.ua rejected the request: access is forbidden.")
    if status_code == 429:
        raise AlertsApiError("alerts.in.ua rate limit reached. Please wait before retrying.")
    raise AlertsApiError(f"alerts.in.ua returned unexpected HTTP status {status_code}.")


def _normalize_active_alerts(payload: Any) -> pd.DataFrame:
    if not isinstance(payload, dict) or not isinstance(payload.get("alerts"), list):
        raise AlertsApiError("Unexpected active alerts response shape.")

    frame = pd.json_normalize(payload["alerts"])
    frame.columns = [_normalize_column_name(column) for column in frame.columns]
    for column in ("started_at", "finished_at", "updated_at"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=True)
    return frame


def _extract_compact_status_string(payload: Any) -> str:
    if isinstance(payload, str):
        status_string = payload
    elif isinstance(payload, dict) and isinstance(payload.get("statuses"), str):
        status_string = payload["statuses"]
    else:
        raise AlertsApiError("Unexpected compact oblast status response shape.")

    if len(status_string) != len(OBLAST_STATUS_ORDER):
        raise AlertsApiError("Unexpected compact oblast status length.")
    return status_string


def _normalize_oblast_statuses(status_string: str) -> pd.DataFrame:
    rows = []
    for index, (oblast, status_code) in enumerate(
        zip(OBLAST_STATUS_ORDER, status_string),
        start=1,
    ):
        normalized_code = status_code.strip().upper()
        status = COMPACT_STATUS_MAP.get(normalized_code, "unknown")
        rows.append(
            {
                "oblast_index": index,
                "oblast": oblast,
                "status_code": normalized_code or None,
                "status": status,
                "is_active": status in {"active", "partial"},
            }
        )
    return pd.DataFrame(rows)


def _normalize_column_name(column: object) -> str:
    return str(column).strip().lower().replace(".", "_")


def _cache_get(cache_key: tuple[str, str]) -> Any | None:
    entry = _CACHE.get(cache_key)
    if entry is None:
        return None
    if entry.expires_at <= time.time():
        _CACHE.pop(cache_key, None)
        return None
    return entry.value


def _cache_set(cache_key: tuple[str, str], value: Any, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    _CACHE[cache_key] = _CacheEntry(
        expires_at=time.time() + ttl_seconds,
        value=value,
    )
