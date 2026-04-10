"""WebSocket utilities for Claw Client."""

import json
from typing import Any, Dict, Optional

import websockets
from websockets.client import WebSocketClientProtocol


async def ws_connect(url: str, **kwargs) -> WebSocketClientProtocol:
    """
    Connect to WebSocket server with common defaults.

    Args:
        url: WebSocket URL
        **kwargs: Additional arguments passed to websockets.connect()

    Returns:
        WebSocket client protocol instance
    """
    # Default settings optimized for Claw Service Hub
    defaults = {
        "ping_interval": None,  # We handle heartbeat ourselves
        "close_timeout": 5,
        "max_size": 10 * 1024 * 1024,  # 10MB max message size
    }

    # Merge defaults with user-provided kwargs
    settings = {**defaults, **kwargs}

    return await websockets.connect(url, **settings)


def serialize_message(message: Dict[str, Any]) -> str:
    """
    Serialize message to JSON string.

    Args:
        message: Message dictionary

    Returns:
        JSON string
    """
    return json.dumps(message, ensure_ascii=False)


def deserialize_message(raw: str) -> Dict[str, Any]:
    """
    Deserialize JSON string to message dictionary.

    Args:
        raw: JSON string

    Returns:
        Message dictionary

    Raises:
        json.JSONDecodeError: If raw is not valid JSON
    """
    return json.loads(raw)


def build_request(msg_type: str, payload: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a standard request message.

    Args:
        msg_type: Message type (e.g., "register", "call", "discover")
        payload: Message payload
        request_id: Optional request ID for tracking responses

    Returns:
        Request dictionary
    """
    import uuid

    return {
        "type": msg_type,
        "payload": payload,
        "request_id": request_id or f"req_{uuid.uuid4().hex[:12]}",
    }
