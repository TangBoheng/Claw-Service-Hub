"""Claw Service Hub Client SDK."""

from .base import BaseClient
from .cli import ClawClientCLI
from .consumers.skill_query import SkillQueryClient
from .exceptions import (
    AuthError,
    ChannelError,
    ClientError,
    ConnectionError,
    KeyError,
    ServiceError,
    TimeoutError,
)
from .hub.client import HubClient
from .providers.management import ManagementOnlyClient
from .providers.tool_service import ToolServiceClient

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "BaseClient",
    "ToolServiceClient",
    "ManagementOnlyClient",
    "SkillQueryClient",
    "HubClient",
    "ClawClientCLI",
    "ClientError",
    "ConnectionError",
    "TimeoutError",
    "ServiceError",
    "ChannelError",
    "AuthError",
    "KeyError",
]
