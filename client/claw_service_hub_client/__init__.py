"""
Claw Service Hub Client

统一客户端，整合服务提供者、消费者、管理型客户端的所有能力。

使用方式:
    from claw_service_hub_client import HubClient

    hub = HubClient(url="ws://localhost:8765")
    await hub.connect()
"""

from .client import HubClient, HubServiceProvider, HubConsumer

__all__ = ["HubClient", "HubServiceProvider", "HubConsumer"]
__version__ = "1.0.0"