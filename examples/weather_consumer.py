#!/usr/bin/env python3
"""
Weather Consumer Example for Claw Service Hub

This example demonstrates how to consume the weather service.

Usage:
    # First start the weather service:
    # python examples/weather_service.py
    
    # Then run this consumer:
    python examples/weather_consumer.py
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.skill_client import SkillQueryClient


async def main():
    """Consume the weather service."""
    hub_url = os.environ.get("HUB_URL", "ws://localhost:8765")

    client = SkillQueryClient(hub_url)
    await client.connect()

    try:
        # Discover available services
        print("🔍 Discovering services...")
        services = await client.discover()
        print(f"   Found {len(services)} services")

        # Find weather service
        weather_service = None
        for service in services:
            if service.get("name") == "weather-service":
                weather_service = service
                break

        if not weather_service:
            print("❌ Weather service not found. Make sure weather_service.py is running.")
            return

        print(f"\n🌤️  Found: {weather_service.get('name')}")
        print(f"   Description: {weather_service.get('description')}")
        print(f"   Service ID: {weather_service.get('service_id')}")

        service_id = weather_service.get("service_id")

        # Get current weather
        print("\n📡 Getting weather for Shanghai...")
        result = await client.call_service(
            service_id=service_id,
            method="get_weather",
            params={"location": "Shanghai"}
        )
        print(f"   Result: {result}")

        # Get weather for Tokyo
        print("\n📡 Getting weather for Tokyo...")
        result = await client.call_service(
            service_id=service_id,
            method="get_weather",
            params={"location": "Tokyo"}
        )
        print(f"   Result: {result}")

        # Get forecast
        print("\n📡 Getting 3-day forecast for Beijing...")
        result = await client.call_service(
            service_id=service_id,
            method="get_forecast",
            params={"location": "Beijing", "days": 3}
        )
        print(f"   Result: {result}")

        # Try unsupported location
        print("\n📡 Getting weather for unsupported location...")
        result = await client.call_service(
            service_id=service_id,
            method="get_weather",
            params={"location": "Mars"}
        )
        print(f"   Result: {result}")

    finally:
        await client.disconnect()
        print("\n👋 Disconnected from hub")


if __name__ == "__main__":
    asyncio.run(main())