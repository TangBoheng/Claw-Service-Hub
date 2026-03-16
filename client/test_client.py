"""
测试客户端 - 模拟 OpenClaw Skill 注册到 Hub
"""
import asyncio
import json
import uuid
import websockets

HUB_URL = "ws://localhost:8765"

async def test_register():
    """测试服务注册"""
    service_id = str(uuid.uuid4())[:8]
    
    async with websockets.connect(HUB_URL) as ws:
        print(f"✅ Connected to Hub")
        
        # 注册服务
        register_msg = {
            "type": "register",
            "service": {
                "id": service_id,
                "name": "test-service",
                "description": "测试服务 - 响应 test 消息",
                "version": "1.0.0",
                "endpoint": "http://localhost:9000",
                "tags": ["test", "demo"],
                "emoji": "🧪",
                "requires": {}
            },
            "skill_doc": """# Test Service

这是一个测试服务。

## 调用方法

发送 test 消息，会返回响应。
"""
        }
        
        await ws.send(json.dumps(register_msg))
        print(f"📤 Sent register request")
        
        # 等待注册确认
        response = await ws.recv()
        data = json.loads(response)
        print(f"📥 Received: {data}")
        
        if data.get("type") == "registered":
            print(f"✅ Service registered! ID: {data.get('service_id')}")
        
        # 保持连接，定期发送心跳
        for i in range(5):
            await asyncio.sleep(5)
            heartbeat = {
                "type": "heartbeat",
                "service_id": data.get("service_id")
            }
            await ws.send(json.dumps(heartbeat))
            print(f"💓 Heartbeat sent ({i+1}/5)")
        
        # 模拟接收请求
        print("\n📥 Waiting for requests...")
        try:
            async for msg in ws:
                print(f"📥 Received: {msg}")
                data = json.loads(msg)
                
                if data.get("type") == "request":
                    # 处理请求
                    request_id = data.get("request_id")
                    method = data.get("method")
                    params = data.get("params", {})
                    
                    print(f"🔧 Method: {method}, Params: {params}")
                    
                    # 发送响应
                    response = {
                        "type": "response",
                        "request_id": request_id,
                        "response": {"status": "ok", "message": "Test response!"}
                    }
                    await ws.send(json.dumps(response))
                    print(f"📤 Sent response")
        except websockets.exceptions.ConnectionClosed:
            print("❌ Connection closed")

if __name__ == "__main__":
    asyncio.run(test_register())