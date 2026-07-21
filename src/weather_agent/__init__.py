"""A narrowly scoped, OpenAI-compatible current-temperature agent."""

from weather_agent.agent import WeatherAgent
from weather_agent.config import Settings
from weather_agent.weather import OpenMeteoClient, TemperatureReading

__all__ = ["OpenMeteoClient", "Settings", "TemperatureReading", "WeatherAgent"]
__version__ = "0.1.0"
