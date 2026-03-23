"""
用户认证客户端示例
展示客户端如何进行用户注册和认证
"""

import asyncio
import json
import websockets


async def user_auth_example():
    """用户认证示例 - 连接到服务器进行用户注册和认证"""
    
    server_url = "ws://localhost:8765"
    
    try:
        async with websockets.connect(server_url) as websocket:
            print("已连接到服务器")
            
            # ========== 1. 用户注册 ==========
            print("\n[1] 发送用户注册请求...")
            await websocket.send(json.dumps({
                "type": "user_register",
                "name": "MyClient"
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "user_register_response" and data.get("success"):
                user = data.get("user", {})
                print(f"  ✅ 用户注册成功!")
                print(f"     User ID: {user.get('user_id')}")
                print(f"     API Key: {user.get('api_key')}")
                api_key = user.get("api_key")
            else:
                print(f"  ❌ 用户注册失败: {data.get('reason', '未知错误')}")
                return
            
            # ========== 2. 用户认证 ==========
            print("\n[2] 发送用户认证请求...")
            await websocket.send(json.dumps({
                "type": "user_auth",
                "api_key": api_key
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "user_auth_response" and data.get("success"):
                print(f"  ✅ 认证成功!")
                print(f"     用户: {data.get('user', {}).get('name')}")
            else:
                print(f"  ❌ 认证失败: {data.get('reason', '未知错误')}")
                
            # ========== 3. 查询用户列表 ==========
            print("\n[3] 查询用户列表...")
            await websocket.send(json.dumps({
                "type": "user_list"
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "user_list_response":
                users = data.get("users", [])
                print(f"  用户列表 ({len(users)} 个):")
                for u in users:
                    print(f"    - {u.get('name')} ({u.get('user_id')})")
            
    except websockets.exceptions.ConnectionRefusedError:
        print("❌ 无法连接到服务器 (请确保服务器正在运行)")
    except Exception as e:
        print(f"❌ 错误: {e}")


# WebSocket 消息类型参考
MESSAGE_TYPES = """
=== 用户相关 WebSocket 消息 ===

发送消息:
1. user_register - 注册新用户
   {"type": "user_register", "name": "用户名"}

2. user_auth - 用户认证
   {"type": "user_auth", "api_key": "用户的 API Key"}

3. user_list - 查询用户列表
   {"type": "user_list"}

4. user_grant_access - 授权用户访问服务 (服务提供者)
   {"type": "user_grant_access", "service_id": "服务ID", "user_id": "用户ID"}

5. user_revoke_access - 撤销用户访问权限 (服务提供者)
   {"type": "user_revoke_access", "service_id": "服务ID", "user_id": "用户ID"}

接收消息:
- user_register_response: {"type": "user_register_response", "success": true, "user": {...}}
- user_auth_response: {"type": "user_auth_response", "success": true, "user": {...}}
- user_list_response: {"type": "user_list_response", "users": [...]}
- user_grant_access_response: {"type": "user_grant_access_response", "success": true}
- user_revoke_access_response: {"type": "user_revoke_access_response", "success": true}

=== REST API ===

POST /api/users - 创建用户
GET /api/users - 列出用户
GET /api/users/{user_id} - 获取用户信息
POST /api/users/auth - 验证 API Key
"""


if __name__ == "__main__":
    print(MESSAGE_TYPES)
    print("\n运行示例...\n")
    asyncio.run(user_auth_example())