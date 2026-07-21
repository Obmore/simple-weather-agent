"""Domain exceptions with safe, user-facing messages."""


class WeatherAgentError(Exception):
    """Base class for expected application failures."""


class ConfigurationError(WeatherAgentError):
    """Raised when required local configuration is missing or invalid."""


class AgentProtocolError(WeatherAgentError):
    """Raised when the model does not follow the tool-calling protocol."""


class WeatherServiceError(WeatherAgentError):
    """Raised when Open-Meteo cannot provide a valid result."""


class LocationNotFoundError(WeatherServiceError):
    """Raised when a requested city cannot be resolved."""
