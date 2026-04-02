"""
单元测试 - HubClient 统一客户端

测试目标: 验证 HubClient 接口完整性
运行方式: pytest tests/test_hub_client_unit.py -v
"""

import pytest


class TestHubClientImport:
    """UT01-04: 导入和实例化测试"""

    def test_import_hubclient(self):
        """UT01: 导入验证"""
        from claw_service_hub_client import HubClient
        assert HubClient is not None

    def test_import_convenience_classes(self):
        """UT04: 便捷类导入"""
        from claw_service_hub_client import HubServiceProvider, HubConsumer
        assert HubServiceProvider is not None
        assert HubConsumer is not None


class TestHubClientInstantiation:
    """UT02: 实例化测试"""

    def test_instantiate_with_url(self):
        """使用 URL 实例化"""
        from claw_service_hub_client import HubClient
        client = HubClient(url="ws://localhost:8765")
        assert client.url == "ws://localhost:8765"

    def test_instantiate_with_options(self):
        """使用选项实例化"""
        from claw_service_hub_client import HubClient
        client = HubClient(
            url="ws://localhost:8765",
            name="test-client",
            heartbeat_interval=30
        )
        assert client.name == "test-client"
        assert client.heartbeat_interval == 30

    def test_default_values(self):
        """默认值验证"""
        from claw_service_hub_client import HubClient
        client = HubClient()
        assert client.url == "ws://localhost:8765"
        assert client.heartbeat_interval == 15
        assert client.auto_reconnect == True


class TestHubClientMethods:
    """UT03: 接口完整性测试"""

    def test_user_identity_methods(self):
        """用户身份接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'register')
        assert hasattr(client, 'login')
        assert hasattr(client, 'whoami')

    def test_service_management_methods(self):
        """服务管理接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'provide')
        assert hasattr(client, 'unregister')
        assert hasattr(client, 'update')

    def test_service_discovery_methods(self):
        """服务发现接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'search')
        assert hasattr(client, 'discover')
        assert hasattr(client, 'get_info')

    def test_service_call_methods(self):
        """服务调用接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'request_key')
        assert hasattr(client, 'establish_channel')
        assert hasattr(client, 'call')
        assert hasattr(client, 'close_channel')

    def test_chat_methods(self):
        """通讯接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'connect')
        assert hasattr(client, 'on_message')
        assert hasattr(client, 'send')
        assert hasattr(client, 'request_chat')
        assert hasattr(client, 'accept_chat')
        assert hasattr(client, 'reject_chat')
        assert hasattr(client, 'end_chat')
        assert hasattr(client, 'history')

    def test_trade_methods(self):
        """交易接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'list')
        assert hasattr(client, 'query_listings')
        assert hasattr(client, 'bid')
        assert hasattr(client, 'accept_bid')
        assert hasattr(client, 'negotiate')
        assert hasattr(client, 'accept_offer')
        assert hasattr(client, 'cancel_listing')
        assert hasattr(client, 'transactions')

    def test_lifecycle_methods(self):
        """生命周期接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'set_lifecycle_policy')
        assert hasattr(client, 'renew_key')

    def test_rating_methods(self):
        """评分接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'rate')
        assert hasattr(client, 'get_rating')

    def test_heartbeat_method(self):
        """心跳接口"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert hasattr(client, 'heartbeat')

    def test_all_34_methods(self):
        """验证全部 34 个预期接口"""
        from claw_service_hub_client import HubClient

        expected_methods = [
            # 用户身份 (3)
            'register', 'login', 'whoami',
            # 服务管理 (3)
            'provide', 'unregister', 'update',
            # 服务发现 (3)
            'search', 'discover', 'get_info',
            # 服务调用 (4)
            'request_key', 'establish_channel', 'call', 'close_channel',
            # 通讯 (8)
            'connect', 'on_message', 'send', 'request_chat',
            'accept_chat', 'reject_chat', 'end_chat', 'history',
            # 交易 (8)
            'list', 'query_listings', 'bid', 'accept_bid',
            'negotiate', 'accept_offer', 'cancel_listing', 'transactions',
            # 生命周期 (2)
            'set_lifecycle_policy', 'renew_key',
            # 评分 (2)
            'rate', 'get_rating',
            # 心跳 (1)
            'heartbeat'
        ]

        client = HubClient()
        missing = []

        for method in expected_methods:
            if not hasattr(client, method):
                missing.append(method)

        assert len(missing) == 0, f"缺少方法: {missing}"
        assert len(expected_methods) == 34, f"方法数应为34，实际: {len(expected_methods)}"


class TestHubClientInternals:
    """内部状态测试"""

    def test_initial_state(self):
        """初始状态验证"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        assert client.running == False
        assert client.websocket is None
        assert client.user_id is None
        assert client._services == {}
        assert client._channels == {}
        assert client._keys == {}

    def test_message_callback_registration(self):
        """消息回调注册"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        def callback(msg):
            pass

        client.on_message(callback)
        assert callback in client._chat_callbacks["message"]

    def test_request_handler_registration(self):
        """请求处理器注册"""
        from claw_service_hub_client import HubClient
        client = HubClient()

        async def handler(**params):
            return {"ok": True}

        client.register_handler("test_method", handler)
        assert "test_method" in client._request_handlers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])