#!/usr/bin/env python3
"""
Calculator Consumer Example for Claw Service Hub

This example demonstrates how to consume the calculator service.

Usage:
    # First start the calculator service:
    # python examples/calculator_service.py
    
    # Then run this consumer:
    python examples/calculator_consumer.py
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.skill_client import SkillQueryClient


async def main():
    """Consume the calculator service."""
    hub_url = os.environ.get("HUB_URL", "ws://localhost:8765")

    client = SkillQueryClient(hub_url)
    await client.connect()

    try:
        # Discover available services
        print("🔍 Discovering services...")
        services = await client.discover()
        print(f"   Found {len(services)} services")

        # Find calculator service
        calc_service = None
        for service in services:
            if service.get("name") == "calculator-service":
                calc_service = service
                break

        if not calc_service:
            print("❌ Calculator service not found. Make sure calculator_service.py is running.")
            return

        print(f"\n🧮 Found: {calc_service.get('name')}")
        print(f"   Description: {calc_service.get('description')}")
        print(f"   Service ID: {calc_service.get('service_id')}")

        service_id = calc_service.get("service_id")

        # Addition
        print("\n➕ Testing add: 10 + 5")
        result = await client.call_service(
            service_id=service_id,
            method="add",
            params={"a": 10, "b": 5}
        )
        print(f"   Result: {result}")

        # Subtraction
        print("\n➖ Testing subtract: 10 - 5")
        result = await client.call_service(
            service_id=service_id,
            method="subtract",
            params={"a": 10, "b": 5}
        )
        print(f"   Result: {result}")

        # Multiplication
        print("\n✖️  Testing multiply: 10 * 5")
        result = await client.call_service(
            service_id=service_id,
            method="multiply",
            params={"a": 10, "b": 5}
        )
        print(f"   Result: {result}")

        # Division
        print("\n➗ Testing divide: 10 / 5")
        result = await client.call_service(
            service_id=service_id,
            method="divide",
            params={"a": 10, "b": 5}
        )
        print(f"   Result: {result}")

        # Division by zero
        print("\n➗ Testing divide by zero: 10 / 0")
        result = await client.call_service(
            service_id=service_id,
            method="divide",
            params={"a": 10, "b": 0}
        )
        print(f"   Result: {result}")

        # Power
        print("\n🔢 Testing power: 2 ** 8")
        result = await client.call_service(
            service_id=service_id,
            method="power",
            params={"base": 2, "exponent": 8}
        )
        print(f"   Result: {result}")

        # Square root
        print("\n√ Testing sqrt: 144")
        result = await client.call_service(
            service_id=service_id,
            method="sqrt",
            params={"a": 144}
        )
        print(f"   Result: {result}")

        # Evaluate expression
        print("\n🔬 Testing evaluate: (2 + 3) * 4")
        result = await client.call_service(
            service_id=service_id,
            method="evaluate",
            params={"expression": "(2 + 3) * 4"}
        )
        print(f"   Result: {result}")

    finally:
        await client.disconnect()
        print("\n👋 Disconnected from hub")


if __name__ == "__main__":
    asyncio.run(main())