"""
Claw Service Hub Client SDK.

统一客户端 SDK，支持服务提供者、消费者、管理型等多种角色。

使用:
    from claw_client import (
        ToolServiceClient,
        ManagementOnlyClient,
        SkillQueryClient,
        HubClient,
    )
"""

from claw_client.base import BaseClient
from claw_client.providers.tool_service import ToolServiceClient
from claw_client.providers.management import ManagementOnlyClient
from claw_client.consumers.skill_query import SkillQueryClient
from claw_client.hub.client import HubClient
from claw_client.exceptions import (
    ClientError,
    ConnectionError,
    TimeoutError,
    ServiceError,
    ChannelError,
    AuthError,
    KeyError,
)
from claw_client.types import (
    MessageCallback,
    RequestHandler,
    ServiceId,
    ChannelId,
    ApiKey,
)

__version__ = "0.2.0"
__author__ = "Claw Service Hub Team"

__all__ = [
    "__version__",
    "BaseClient",
    "ToolServiceClient",
    "ManagementOnlyClient",
    "SkillQueryClient",
    "HubClient",
    "ClientError",
    "ConnectionError",
    "TimeoutError",
    "ServiceError",
    "ChannelError",
    "AuthError",
    "KeyError",
    "MessageCallback",
    "RequestHandler",
    "ServiceId",
    "ChannelId",
    "ApiKey",
]
