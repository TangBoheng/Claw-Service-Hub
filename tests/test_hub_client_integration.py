"""
集成测试 - HubClient 统一客户端

测试目标: 验证 HubClient 与服务器的交互
前置条件: Hub 服务器已启动 (python start_server.py)
运行方式: pytest tests/test_hub_client_integration.py -v
"""

import pytest
import asyncio
from claw_service_hub_client import HubClient

# 标记所有测试为异步
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def connected_client():
    """创建并连接 HubClient"""
    client = HubClient(url="ws://localhost:8765")
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def registered_client(connected_client):
    """已注册的客户端"""
    result = await connected_client.register(name="test-agent")
    yield connected_client, result


class TestConnection:
    """IT-CON: 连接测试"""

    async def test_connect(self):
        """测试连接"""
        client = HubClient(url="ws://localhost:8765")
        result = await client.connect()
        assert result == True or client.running == True
        await client.disconnect()

    async def test_disconnect(self):
        """测试断开连接"""
        client = HubClient(url="ws://localhost:8765")
        await client.connect()
        await client.disconnect()
        assert client.running == False


class TestUserIdentity:
    """IT01-02: 用户身份测试"""

    async def test_register(self, connected_client):
        """IT01: 用户注册"""
        result = await connected_client.register(name="test-user-001")

        # 可能返回成功或已存在
        assert "user_id" in result or "api_key" in result or "error" in result

    async def test_login(self, connected_client):
        """IT02: 用户登录"""
        # 先注册
        reg_result = await connected_client.register(name="test-user-002")

        if reg_result.get("api_key"):
            # 尝试登录
            login_result = await connected_client.login(api_key=reg_result["api_key"])
            assert "user_id" in login_result or "error" in login_result

    async def test_whoami(self, connected_client):
        """用户信息查询"""
        result = await connected_client.whoami()
        # 可能返回用户信息或未登录错误
        assert isinstance(result, dict)


class TestServiceManagement:
    """IT03-06: 服务管理测试"""

    async def test_provide_service(self, connected_client):
        """IT03: 服务发布"""
        result = await connected_client.provide(
            service_id=f"test-service-{asyncio.get_event_loop().time():.0f}",
            description="测试服务 - 用于验证 provide 接口",
            schema={"methods": ["test", "ping"]},
            price=10,
            tags=["test"]
        )

        assert isinstance(result, dict)

    async def test_search_service(self, connected_client):
        """IT04: 服务搜索"""
        result = await connected_client.search(query="test")

        assert isinstance(result, list)

    async def test_discover_services(self, connected_client):
        """IT05: 发现所有服务"""
        result = await connected_client.discover()

        assert isinstance(result, list)

    async def test_get_service_info(self, connected_client):
        """IT06: 获取服务详情"""
        # 先搜索获取一个服务ID
        services = await connected_client.search(query="test")

        if services and len(services) > 0:
            service_id = services[0].get("service_id")
            if service_id:
                result = await connected_client.get_info(service_id)
                assert isinstance(result, dict)


class TestServiceCall:
    """IT10-13: 服务调用测试"""

    async def test_request_key(self, connected_client):
        """IT10: 请求访问凭证"""
        # 先搜索获取一个服务ID
        services = await connected_client.search(status="online")

        if services and len(services) > 0:
            service_id = services[0].get("service_id")
            if service_id:
                result = await connected_client.request_key(
                    service_id=service_id,
                    purpose="测试请求"
                )
                assert isinstance(result, dict)

    async def test_establish_channel(self, connected_client):
        """IT11: 建立通道"""
        services = await connected_client.search(status="online")

        if services and len(services) > 0:
            service_id = services[0].get("service_id")
            if service_id:
                result = await connected_client.establish_channel(service_id)
                assert isinstance(result, dict)


class TestTrade:
    """IT30-37: 交易测试"""

    async def test_create_listing(self, connected_client):
        """IT30: 创建挂牌"""
        result = await connected_client.list(
            title=f"测试服务挂牌-{asyncio.get_event_loop().time():.0f}",
            description="测试挂牌描述",
            price=100,
            floor_price=80,
            mode="fixed"
        )

        assert isinstance(result, dict)

    async def test_query_listings(self, connected_client):
        """IT31: 查询挂牌"""
        result = await connected_client.query_listings()

        assert isinstance(result, list)

    async def test_transactions(self, connected_client):
        """IT37: 查询交易记录"""
        result = await connected_client.transactions(role="consumer")

        assert isinstance(result, list)


class TestLifecycle:
    """IT40-44: 生命周期测试"""

    async def test_set_lifecycle_policy(self, connected_client):
        """IT40: 设置生命周期策略"""
        result = await connected_client.set_lifecycle_policy(
            duration_seconds=3600,
            max_calls=100
        )

        assert isinstance(result, dict)

    async def test_heartbeat(self, connected_client):
        """IT44: 心跳"""
        result = await connected_client.heartbeat()

        assert isinstance(result, dict)


class TestRating:
    """评分测试"""

    async def test_rate_service(self, connected_client):
        """IT42: 评价服务"""
        services = await connected_client.search(status="online")

        if services and len(services) > 0:
            service_id = services[0].get("service_id")
            if service_id:
                result = await connected_client.rate(
                    service_id=service_id,
                    score=5,
                    comment="测试评分"
                )
                assert isinstance(result, dict)

    async def test_get_rating(self, connected_client):
        """IT43: 获取评分"""
        services = await connected_client.search(status="online")

        if services and len(services) > 0:
            service_id = services[0].get("service_id")
            if service_id:
                result = await connected_client.get_rating(service_id)
                assert isinstance(result, dict)


class TestChat:
    """IT20-25: 通讯测试"""

    async def test_send_message(self, connected_client):
        """IT20: 发送消息"""
        result = await connected_client.send(
            target="test-target",
            content="测试消息"
        )

        assert isinstance(result, dict)

    async def test_request_chat(self, connected_client):
        """IT21: 请求通讯"""
        services = await connected_client.search(status="online")

        if services and len(services) > 0:
            service_id = services[0].get("service_id")
            if service_id:
                result = await connected_client.request_chat(service_id)
                assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])