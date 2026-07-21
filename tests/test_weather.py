from __future__ import annotations

import httpx
import pytest

from weather_agent.errors import LocationNotFoundError, WeatherServiceError
from weather_agent.weather import OpenMeteoClient


def test_get_current_temperature_uses_only_required_forecast_field() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "geo.test":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Budapest",
                            "country": "Hungary",
                            "latitude": 47.5,
                            "longitude": 19.04,
                            "timezone": "Europe/Budapest",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "timezone": "Europe/Budapest",
                "current": {"time": "2026-07-21T12:00", "temperature_2m": 29.4},
                "current_units": {"temperature_2m": "degrees Celsius"},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenMeteoClient(
        geocoding_url="https://geo.test/v1/search",
        forecast_url="https://forecast.test/v1/forecast",
        http_client=http_client,
    )

    reading = client.get_current_temperature("Budapest")

    assert reading.temperature == 29.4
    assert reading.unit == "degrees Celsius"
    assert reading.resolved_city == "Budapest, Hungary"
    assert requests[0].url.params["name"] == "Budapest"
    assert requests[0].url.params["language"] == "en"
    assert requests[1].url.params["current"] == "temperature_2m"
    assert set(requests[1].url.params.keys()) == {
        "latitude",
        "longitude",
        "current",
        "timezone",
    }


def test_location_not_found() -> None:
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"results": []}))
    )
    client = OpenMeteoClient(http_client=http_client)

    with pytest.raises(LocationNotFoundError, match="City not found"):
        client.resolve_city("Atlantis")


def test_invalid_forecast_payload_is_domain_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "geocoding" in str(request.url):
            return httpx.Response(
                200,
                json={"results": [{"name": "Paris", "latitude": 48.86, "longitude": 2.35}]},
            )
        return httpx.Response(200, json={"current": {}})

    client = OpenMeteoClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(WeatherServiceError, match="no current temperature"):
        client.get_current_temperature("Paris")


def test_batch_deduplicates_and_collects_errors() -> None:
    class StubClient(OpenMeteoClient):
        def get_current_temperature(self, city: str):  # type: ignore[no-untyped-def]
            if city == "Bad City":
                raise LocationNotFoundError("City not found: Bad City")
            return type("Reading", (), {"requested_city": city})()

    client = StubClient(http_client=httpx.Client())
    readings, errors = client.get_current_temperatures(["Budapest", "budapest", "Bad City"])

    assert len(readings) == 1
    assert readings[0].requested_city == "Budapest"
    assert errors == [{"city": "Bad City", "error": "City not found: Bad City"}]


def test_http_and_shape_failures_are_wrapped() -> None:
    failing = OpenMeteoClient(
        http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    )
    with pytest.raises(WeatherServiceError, match="request failed"):
        failing.resolve_city("Budapest")

    invalid = OpenMeteoClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[]))
        )
    )
    with pytest.raises(WeatherServiceError, match="invalid response"):
        invalid.resolve_city("Budapest")


def test_incomplete_geocoding_result_is_wrapped() -> None:
    client = OpenMeteoClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"results": [{"name": "Budapest"}]})
            )
        )
    )

    with pytest.raises(WeatherServiceError, match="incomplete geocoding"):
        client.resolve_city("Budapest")
