from __future__ import annotations

import pandas as pd
import pytest

from air_alerts import live_api
from air_alerts.live_api import (
    AlertsApiError,
    MissingAlertsApiTokenError,
    get_active_alerts,
    get_air_raid_statuses_by_oblast,
)


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clear_cache():
    live_api.clear_live_api_cache()
    yield
    live_api.clear_live_api_cache()


def test_missing_token(monkeypatch) -> None:
    monkeypatch.setenv("ALERTS_API_TOKEN", "")

    with pytest.raises(MissingAlertsApiTokenError, match="ALERTS_API_TOKEN"):
        get_active_alerts(cache_ttl_seconds=0)


def test_successful_compact_oblast_statuses_parsing(monkeypatch) -> None:
    monkeypatch.setenv("ALERTS_API_TOKEN", "test-token")
    status_string = "APN" + (" " * (len(live_api.OBLAST_STATUS_ORDER) - 3))

    def fake_get(url, headers, timeout):
        assert headers["Authorization"] == "Bearer test-token"
        return FakeResponse(200, status_string)

    monkeypatch.setattr(live_api.requests, "get", fake_get)

    frame = get_air_raid_statuses_by_oblast(cache_ttl_seconds=0)

    assert len(frame) == len(live_api.OBLAST_STATUS_ORDER)
    assert list(frame.loc[:2, "status"]) == ["active", "partial", "no_alert"]
    assert frame.loc[3, "status"] == "unknown"
    assert frame.loc[0, "oblast"] == "Autonomous Republic of Crimea"


def test_active_alerts_json_normalization(monkeypatch) -> None:
    monkeypatch.setenv("ALERTS_API_TOKEN", "test-token")

    def fake_get(url, headers, timeout):
        return FakeResponse(
            200,
            {
                "alerts": [
                    {
                        "id": 10,
                        "location_title": "Luhansk Oblast",
                        "location_type": "oblast",
                        "started_at": "2022-04-04T16:45:39.000Z",
                        "finished_at": None,
                        "updated_at": "2022-04-08T08:04:26.316Z",
                        "alert_type": "air_raid",
                    }
                ]
            },
        )

    monkeypatch.setattr(live_api.requests, "get", fake_get)

    frame = get_active_alerts(cache_ttl_seconds=0)

    assert list(frame["location_title"]) == ["Luhansk Oblast"]
    assert str(frame["started_at"].dtype).endswith("UTC]")
    assert pd.isna(frame.loc[0, "finished_at"])


def test_rate_limit_error(monkeypatch) -> None:
    monkeypatch.setenv("ALERTS_API_TOKEN", "test-token")

    def fake_get(url, headers, timeout):
        return FakeResponse(429, {"message": "Too many requests"})

    monkeypatch.setattr(live_api.requests, "get", fake_get)

    with pytest.raises(AlertsApiError, match="rate limit"):
        get_active_alerts(cache_ttl_seconds=0)


def test_token_is_not_in_error_messages(monkeypatch) -> None:
    secret_token = "super-secret-token"
    monkeypatch.setenv("ALERTS_API_TOKEN", secret_token)

    def fake_get(url, headers, timeout):
        return FakeResponse(401, {"message": f"bad token {secret_token}"})

    monkeypatch.setattr(live_api.requests, "get", fake_get)

    with pytest.raises(AlertsApiError) as error:
        get_active_alerts(cache_ttl_seconds=0)

    assert secret_token not in str(error.value)
