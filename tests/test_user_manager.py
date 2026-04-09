"""
用户注册与认证功能测试
"""

import pytest
from server.auth.user_manager import UserManager, User


class TestUserManager:
    """用户管理器测试"""

    def test_create_user(self):
        """测试创建用户"""
        um = UserManager()
        user = um.create_user(name="test_user")

        assert user.user_id is not None
        assert user.name == "test_user"
        assert user.api_key is not None
        assert user.api_key.startswith("ush_")
        assert user.is_active is True

    def test_create_user_without_name(self):
        """测试创建用户（不带名称）"""
        um = UserManager()
        user = um.create_user()

        assert user.user_id is not None
        assert user.name is not None
        assert user.api_key is not None

    def test_get_user(self):
        """测试获取用户"""
        um = UserManager()
        user1 = um.create_user(name="user1")
        user2 = um.get_user(user1.user_id)

        assert user2 is not None
        assert user2.user_id == user1.user_id
        assert user2.name == user1.name

    def test_get_user_by_api_key(self):
        """测试通过 API Key 获取用户"""
        um = UserManager()
        user = um.create_user(name="test_user")
        found = um.get_user_by_api_key(user.api_key)

        assert found is not None
        assert found.user_id == user.user_id

    def test_verify_api_key(self):
        """测试 API Key 验证"""
        um = UserManager()
        user = um.create_user(name="test_user")

        # 正确的 API Key
        result = um.verify_api_key(user.api_key)
        assert result["valid"] is True
        assert result["user"].user_id == user.user_id

        # 错误的 API Key
        result = um.verify_api_key("invalid_key")
        assert result["valid"] is False

    def test_deactivate_user(self):
        """测试禁用用户"""
        um = UserManager()
        user = um.create_user(name="test_user")

        # 验证启用状态
        result = um.verify_api_key(user.api_key)
        assert result["valid"] is True

        # 禁用用户
        um.deactivate_user(user.user_id)

        # 验证禁用状态
        result = um.verify_api_key(user.api_key)
        assert result["valid"] is False

    def test_list_users(self):
        """测试列出用户"""
        um = UserManager()
        um.create_user(name="user1")
        um.create_user(name="user2")

        users = um.list_users()
        assert len(users) >= 2

    def test_delete_user(self):
        """测试删除用户"""
        um = UserManager()
        user = um.create_user(name="test_user")
        user_id = user.user_id

        # 删除用户
        result = um.delete_user(user_id)
        assert result is True

        # 验证用户已被删除
        user = um.get_user(user_id)
        assert user is None


class TestUser:
    """用户实体测试"""

    def test_user_creation(self):
        """测试用户创建"""
        user = User(user_id="test123", name="test_user", api_key="ush_testkey")

        assert user.user_id == "test123"
        assert user.name == "test_user"
        assert user.api_key == "ush_testkey"
        assert user.is_active is True

    def test_verify_api_key(self):
        """测试 API Key 验证"""
        user = User(user_id="test123", name="test_user", api_key="ush_testkey")

        # 正确的 API Key
        assert user.verify_api_key("ush_testkey") is True

        # 错误的 API Key
        assert user.verify_api_key("wrong_key") is False

        # 禁用用户
        user.is_active = False
        assert user.verify_api_key("ush_testkey") is False

    def test_to_dict(self):
        """测试转换为字典"""
        user = User(user_id="test123", name="test_user", api_key="ush_testkey")
        data = user.to_dict()

        assert data["user_id"] == "test123"
        assert data["name"] == "test_user"
        assert data["api_key"] == "ush_testkey"
        assert data["is_active"] is True

    def test_to_metadata_dict(self):
        """测试转换为轻量级 metadata（不包含 API Key）"""
        user = User(user_id="test123", name="test_user", api_key="ush_testkey")
        data = user.to_metadata_dict()

        assert data["user_id"] == "test123"
        assert data["name"] == "test_user"
        assert "api_key" not in data