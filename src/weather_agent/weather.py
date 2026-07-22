"""Open-Meteo geocoding and current-temperature client."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import httpx

from weather_agent.errors import LocationNotFoundError, WeatherServiceError


@dataclass(frozen=True, slots=True)
class ResolvedLocation:
    requested_name: str
    display_name: str
    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True, slots=True)
class TemperatureReading:
    requested_city: str
    resolved_city: str
    temperature: float
    unit: str
    observed_at: str
    timezone: str

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


class OpenMeteoClient:
    """Fetch only the data needed for a current city temperature answer."""

    def __init__(
        self,
        *,
        geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search",
        forecast_url: str = "https://api.open-meteo.com/v1/forecast",
        timeout_seconds: float = 20.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._geocoding_url = geocoding_url
        self._forecast_url = forecast_url
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            transport=httpx.HTTPTransport(retries=2),
            headers={"User-Agent": "simple-weather-agent/0.1"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def resolve_city(self, city: str) -> ResolvedLocation:
        city = city.strip()
        if not city:
            raise LocationNotFoundError("The city name is empty.")

        payload = self._get_json(
            self._geocoding_url,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            service_name="Open-Meteo geocoding",
        )
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise LocationNotFoundError(f"City not found: {city}")

        first = results[0]
        if not isinstance(first, dict):
            raise WeatherServiceError("Open-Meteo returned an invalid geocoding result.")
        try:
            name = str(first["name"])
            country = str(first.get("country", "")).strip()
            latitude = float(first["latitude"])
            longitude = float(first["longitude"])
            timezone = str(first.get("timezone", "auto"))
        except (KeyError, TypeError, ValueError) as exc:
            raise WeatherServiceError(
                "Open-Meteo returned an incomplete geocoding result."
            ) from exc

        display_name = f"{name}, {country}" if country else name
        return ResolvedLocation(city, display_name, latitude, longitude, timezone)

    def get_current_temperature(self, city: str) -> TemperatureReading:
        location = self.resolve_city(city)
        payload = self._get_json(
            self._forecast_url,
            params={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "current": "temperature_2m",
                "timezone": "auto",
            },
            service_name="Open-Meteo forecast",
        )
        current = payload.get("current")
        units = payload.get("current_units")
        if not isinstance(current, dict) or not isinstance(units, dict):
            raise WeatherServiceError("Open-Meteo returned no current temperature.")

        try:
            temperature = float(current["temperature_2m"])
            observed_at = str(current["time"])
            unit = str(units["temperature_2m"])
            timezone = str(payload.get("timezone", location.timezone))
        except (KeyError, TypeError, ValueError) as exc:
            raise WeatherServiceError(
                "Open-Meteo returned an invalid current-temperature payload."
            ) from exc

        return TemperatureReading(
            requested_city=city,
            resolved_city=location.display_name,
            temperature=temperature,
            unit=unit,
            observed_at=observed_at,
            timezone=timezone,
        )

    def get_current_temperatures(
        self, cities: list[str]
    ) -> tuple[list[TemperatureReading], list[dict[str, str]]]:
        readings: list[TemperatureReading] = []
        errors: list[dict[str, str]] = []
        seen: set[str] = set()
        for city in cities:
            normalized = city.strip().casefold()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            try:
                readings.append(self.get_current_temperature(city.strip()))
            except WeatherServiceError as exc:
                errors.append({"city": city.strip(), "error": str(exc)})
        return readings, errors

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, str | float | int],
        service_name: str,
    ) -> dict[str, Any]:
        try:
            response = self._client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WeatherServiceError(f"{service_name} request failed.") from exc
        if not isinstance(payload, dict):
            raise WeatherServiceError(f"{service_name} returned an invalid response.")
        return payload
