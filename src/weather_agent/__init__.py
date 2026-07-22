"""OpenAI-compatible agent for current city temperatures."""

from weather_agent.agent import AgentResult, WeatherAgent
from weather_agent.config import Settings
from weather_agent.weather import OpenMeteoClient, TemperatureReading

__all__ = ["AgentResult", "OpenMeteoClient", "Settings", "TemperatureReading", "WeatherAgent"]
__version__ = "0.1.0"
