#!/usr/bin/env python3
"""
Calculator Service Example for Claw Service Hub

This example demonstrates:
- Basic arithmetic operations
- Error handling (division by zero, invalid input)
- Registering multiple service methods
- Simple synchronous and async handlers

Usage:
    # As Provider - Run this to start the calculator service
    python examples/calculator_service.py

    # As Consumer - Use SkillQueryClient to call this service
    # See examples/calculator_consumer.py for consumer example
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client import LocalServiceRunner


class Calculator:
    """Simple calculator service with basic arithmetic operations."""

    def add(self, a: float = 0, b: float = 0, **kwargs) -> dict:
        """
        Add two numbers.

        Args:
            a: First number
            b: Second number
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Result of a + b
        """
        try:
            result = float(a) + float(b)
            return {
                "success": True,
                "operation": "add",
                "a": a,
                "b": b,
                "result": result
            }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": f"Invalid input: {str(e)}"
            }

    def subtract(self, a: float = 0, b: float = 0, **kwargs) -> dict:
        """
        Subtract b from a.

        Args:
            a: First number (minuend)
            b: Second number (subtrahend)
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Result of a - b
        """
        try:
            result = float(a) - float(b)
            return {
                "success": True,
                "operation": "subtract",
                "a": a,
                "b": b,
                "result": result
            }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": f"Invalid input: {str(e)}"
            }

    def multiply(self, a: float = 1, b: float = 1, **kwargs) -> dict:
        """
        Multiply two numbers.

        Args:
            a: First number
            b: Second number
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Result of a * b
        """
        try:
            result = float(a) * float(b)
            return {
                "success": True,
                "operation": "multiply",
                "a": a,
                "b": b,
                "result": result
            }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": f"Invalid input: {str(e)}"
            }

    def divide(self, a: float = 1, b: float = 1, **kwargs) -> dict:
        """
        Divide a by b.

        Args:
            a: Dividend
            b: Divisor
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Result of a / b

        Error:
            Returns error if b is zero
        """
        try:
            b_val = float(b)
            if b_val == 0:
                return {
                    "success": False,
                    "error": "Division by zero is not allowed"
                }
            result = float(a) / b_val
            return {
                "success": True,
                "operation": "divide",
                "a": a,
                "b": b,
                "result": result
            }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": f"Invalid input: {str(e)}"
            }

    def power(self, base: float = 2, exponent: float = 2, **kwargs) -> dict:
        """
        Calculate base raised to the power of exponent.

        Args:
            base: Base number
            exponent: Exponent
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Result of base ** exponent
        """
        try:
            result = float(base) ** float(exponent)
            return {
                "success": True,
                "operation": "power",
                "base": base,
                "exponent": exponent,
                "result": result
            }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": f"Invalid input: {str(e)}"
            }

    def sqrt(self, a: float = 0, **kwargs) -> dict:
        """
        Calculate square root of a.

        Args:
            a: Number to calculate square root of
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Result of sqrt(a)
        """
        try:
            a_val = float(a)
            if a_val < 0:
                return {
                    "success": False,
                    "error": "Cannot calculate square root of negative number"
                }
            import math
            result = math.sqrt(a_val)
            return {
                "success": True,
                "operation": "sqrt",
                "a": a,
                "result": result
            }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": f"Invalid input: {str(e)}"
            }

    def evaluate(self, expression: str = "", **kwargs) -> dict:
        """
        Safely evaluate a mathematical expression.

        Args:
            expression: Mathematical expression (e.g., "2 + 3 * 4")
            **kwargs: Additional parameters (ignored)

        Returns:
            dict: Result of the expression

        Note:
            Only supports: +, -, *, /, **, (, )
            For security, only allows numbers and these operators
        """
        allowed_chars = set("0123456789.+-*/()** ")
        expression = expression.strip()

        # Check for allowed characters only
        if not all(c in allowed_chars for c in expression):
            return {
                "success": False,
                "error": "Expression contains invalid characters. Only +, -, *, /, **, (, ) allowed"
            }

        # Check for dangerous patterns
        dangerous = ["__", "import", "eval", "exec", "os.", "sys."]
        if any(d in expression.lower() for d in dangerous):
            return {
                "success": False,
                "error": "Expression contains potentially dangerous patterns"
            }

        try:
            # Replace ** with ^ for Python eval (if user used **)
            expression = expression.replace("^", "**")
            result = eval(expression)
            return {
                "success": True,
                "expression": expression,
                "result": result
            }
        except ZeroDivisionError:
            return {
                "success": False,
                "error": "Division by zero in expression"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid expression: {str(e)}"
            }


async def main():
    """Start the calculator service provider."""
    hub_url = os.environ.get("HUB_URL", "ws://localhost:8765")

    # Create calculator instance
    calculator = Calculator()

    # Create service runner
    runner = LocalServiceRunner(
        name="calculator-service",
        description="Provides basic arithmetic operations: add, subtract, multiply, divide, power, sqrt, evaluate",
        hub_url=hub_url,
        tags=["calculator", "math", "utility"]
    )

    # Register methods
    runner.register_handler("add", calculator.add)
    runner.register_handler("subtract", calculator.subtract)
    runner.register_handler("multiply", calculator.multiply)
    runner.register_handler("divide", calculator.divide)
    runner.register_handler("power", calculator.power)
    runner.register_handler("sqrt", calculator.sqrt)
    runner.register_handler("evaluate", calculator.evaluate)

    print(f"🧮 Calculator Service starting...")
    print(f"   Hub URL: {hub_url}")
    print(f"   Methods: add, subtract, multiply, divide, power, sqrt, evaluate")
    print()

    await runner.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())