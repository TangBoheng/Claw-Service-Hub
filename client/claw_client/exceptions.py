"""Custom exceptions for Claw Client."""


class ClientError(Exception):
    """Base exception for all client errors."""
    pass


class ConnectionError(ClientError):
    """WebSocket connection failed or lost."""

    def __init__(self, url: str, reason: str = ""):
        self.url = url
        self.reason = reason
        super().__init__(f"Connection failed to {url}: {reason}" if reason else f"Connection failed to {url}")


class TimeoutError(ClientError):
    """Request timed out waiting for response."""

    def __init__(self, request_type: str, timeout: float):
        self.request_type = request_type
        self.timeout = timeout
        super().__init__(f"{request_type} timed out after {timeout}s")


class ServiceError(ClientError):
    """Service-related error (not found, unavailable, etc.)."""

    def __init__(self, service_id: str, reason: str = ""):
        self.service_id = service_id
        self.reason = reason
        super().__init__(f"Service error for {service_id}: {reason}" if reason else f"Service error for {service_id}")


class ChannelError(ClientError):
    """Channel-related error (not established, closed, etc.)."""

    def __init__(self, channel_id: str, reason: str = ""):
        self.channel_id = channel_id
        self.reason = reason
        super().__init__(f"Channel error for {channel_id}: {reason}" if reason else f"Channel error for {channel_id}")


class AuthError(ClientError):
    """Authentication/authorization error."""

    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(f"Auth error: {reason}")


class KeyError(ClientError):
    """API Key error (invalid, expired, revoked)."""

    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(f"Key error: {reason}")
