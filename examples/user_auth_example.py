"""
用户注册与认证示例
展示如何使用用户注册机制
"""

import asyncio
import json
from server.user_manager import user_manager
from server.core.registry import ToolService
from server.key_manager import key_manager


async def main():
    print("=" * 60)
    print("用户注册与认证示例")
    print("=" * 60)

    # ========== 1. 用户注册 ==========
    print("\n[1] 用户注册")
    
    # 创建第一个用户
    user1 = user_manager.create_user(name="Alice")
    print(f"  用户 1 创建成功: {user1.user_id}")
    print(f"  名称: {user1.name}")
    print(f"  API Key: {user1.api_key}")
    
    # 创建第二个用户
    user2 = user_manager.create_user(name="Bob")
    print(f"\n  用户 2 创建成功: {user2.user_id}")
    print(f"  名称: {user2.name}")
    print(f"  API Key: {user2.api_key}")

    # ========== 2. 用户认证 ==========
    print("\n[2] 用户认证")
    
    # 正确的 API Key
    result = user_manager.verify_api_key(user1.api_key)
    print(f"  使用正确的 API Key 验证: {result['valid']}")
    
    # 错误的 API Key
    result = user_manager.verify_api_key("invalid_key")
    print(f"  使用错误的 API Key 验证: {result['valid']}")

    # 禁用用户
    user_manager.deactivate_user(user2.user_id)
    result = user_manager.verify_api_key(user2.api_key)
    print(f"  禁用后验证: {result['valid']}, 原因: {result['reason']}")

    # ========== 3. 服务访问控制 ==========
    print("\n[3] 服务访问控制")
    
    # 创建一个公开的服务（无访问限制）
    public_service = ToolService(
        id="public_service",
        name="公开服务",
        description="所有人都可以访问",
        allowed_users=[]  # 空列表表示无限制
    )
    
    # 创建一个受限服务
    private_service = ToolService(
        id="private_service",
        name="私有服务",
        description="需要授权才能访问",
        allowed_users=[user1.user_id]  # 只允许 Alice 访问
    )
    
    print(f"  公开服务 - Alice 访问: {public_service.can_access(user1.user_id)}")
    print(f"  公开服务 - Bob 访问: {public_service.can_access(user2.user_id)}")
    print(f"  私有服务 - Alice 访问: {private_service.can_access(user1.user_id)}")
    print(f"  私有服务 - Bob 访问: {private_service.can_access(user2.user_id)}")

    # ========== 4. 获取用户列表 ==========
    print("\n[4] 获取用户列表")
    
    users = user_manager.list_users()
    print(f"  当前用户数: {len(users)}")
    for u in users:
        print(f"    - {u['name']} ({u['user_id']})")

    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())