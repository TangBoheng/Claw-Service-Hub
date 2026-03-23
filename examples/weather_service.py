#!/usr/bin/env python3
"""
Weather Service Example for Claw Service Hub

This example demonstrates:
- Fetching weather data from Open-Meteo API (free, no API key required)
- Registering multiple service methods
- Error handling for API failures
- Environment variable configuration

Usage:
    # As Provider - Run this to start the weather service
    python examples/weather_service.py

    # As Consumer - Use SkillQueryClient to call this service
    # See examples/weather_consumer.py for consumer example
"""

import os
import asyncio
import aiohttp
from typing import Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client import LocalServiceRunner


class WeatherService:
    """Weather service provider using Open-Meteo API."""

    def __init__(self, default_location: str = "Shanghai"):
        self.default_location = default_location
        # Location coordinates (latitude, longitude)
        self.locations = {
            "Shanghai": (31.2304, 121.4737),
            "Beijing": (39.9042, 116.4074),
            "Tokyo": (35.6762, 139.6503),
            "New York": (40.7128, -74.0060),
            "London": (51.5074, -0.1278),
            "San Francisco": (37.7749, -122.4194),
        }

    async def get_weather(self, location: Optional[str] = None, **kwargs) -> dict:
        """
        Get current weather for a location.

        Args:
            location: City name (defaults to Shanghai)
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Weather data including temperature, humidity, weather condition
        """
        loc = location or self.default_location

        if loc not in self.locations:
            return {
                "success": False,
                "error": f"Location '{loc}' not supported. Choose from: {', '.join(self.locations.keys())}"
            }

        lat, lon = self.locations[loc]

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "timezone": "auto"
                }

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"API error: {response.status}"}

                    data = await response.json()
                    current = data.get("current", {})

                    # Map weather codes to conditions
                    weather_code = current.get("weather_code", 0)
                    condition = self._get_weather_condition(weather_code)

                    return {
                        "success": True,
                        "location": loc,
                        "temperature": current.get("temperature_2m"),
                        "unit": "°C",
                        "humidity": current.get("relative_humidity_2m"),
                        "wind_speed": current.get("wind_speed_10m"),
                        "wind_unit": "km/h",
                        "condition": condition,
                        "weather_code": weather_code
                    }

        except aiohttp.ClientError as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    async def get_forecast(self, location: Optional[str] = None, days: int = 3, **kwargs) -> dict:
        """
        Get weather forecast for a location.

        Args:
            location: City name (defaults to Shanghai)
            days: Number of days to forecast (1-7)
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Forecast data for the specified number of days
        """
        loc = location or self.default_location

        if loc not in self.locations:
            return {
                "success": False,
                "error": f"Location '{loc}' not supported. Choose from: {', '.join(self.locations.keys())}"
            }

        days = min(max(days, 1), 7)  # Clamp to 1-7 days
        lat, lon = self.locations[loc]

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                    "timezone": "auto",
                    "forecast_days": days
                }

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"API error: {response.status}"}

                    data = await response.json()
                    daily = data.get("daily", {})

                    forecast = []
                    for i in range(len(daily.get("time", []))):
                        weather_code = daily.get("weather_code", [0])[i]
                        forecast.append({
                            "date": daily.get("time", [])[i],
                            "temp_max": daily.get("temperature_2m_max", [None])[i],
                            "temp_min": daily.get("temperature_2m_min", [None])[i],
                            "condition": self._get_weather_condition(weather_code)
                        })

                    return {
                        "success": True,
                        "location": loc,
                        "forecast": forecast
                    }

        except aiohttp.ClientError as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def _get_weather_condition(self, code: int) -> str:
        """Map Open-Meteo weather code to condition string."""
        conditions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail",
        }
        return conditions.get(code, "Unknown")


async def main():
    """Start the weather service provider."""
    hub_url = os.environ.get("HUB_URL", "ws://localhost:8765")

    # Create weather service instance
    weather_service = WeatherService(
        default_location=os.environ.get("DEFAULT_LOCATION", "Shanghai")
    )

    # Create service runner
    runner = LocalServiceRunner(
        name="weather-service",
        description="Provides weather data using Open-Meteo API. Supports: Shanghai, Beijing, Tokyo, New York, London, San Francisco",
        hub_url=hub_url,
        tags=["weather", "api", "utility"]
    )

    # Register methods
    runner.register_handler("get_weather", weather_service.get_weather)
    runner.register_handler("get_forecast", weather_service.get_forecast)

    print(f"🌤️  Weather Service starting...")
    print(f"   Hub URL: {hub_url}")
    print(f"   Supported locations: {', '.join(weather_service.locations.keys())}")
    print(f"   Methods: get_weather, get_forecast")
    print()

    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())