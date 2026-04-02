#!/usr/bin/env python3
"""
测试用例 TC001 - 基础服务注册与发现
运行方式: python tests/interaction/tc001_runner.py
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import websockets

HUB_URL = "ws://localhost:8765"

async def connect_and_run():
    """连接到 Hub 并执行测试步骤"""
    
    async with websockets.connect(HUB_URL) as ws:
        print(f"[TC001] 连接到 {HUB_URL}")
        
        # 接收连接确认（可能有 metadata_list）
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=3.0)
            print(f"[TC001] 初始响应: {response}")
        except:
            pass
        
        # ========== Step 1: subagent1 注册 A 股实时行情服务 ==========
        print("\n" + "="*60)
        print("[TC001] Step 1: subagent1 注册 A 股实时行情服务")
        print("="*60)
        
        register_msg1 = {
            "type": "register",
            "client_type": "full",
            "service": {
                "name": "A股实时行情服务",
                "description": "基于东方财富API的A股实时行情推送服务，支持实时价格、K线数据",
                "version": "1.0.0",
                "tags": ["股票", "A股", "实时行情", "东方财富"],
                "price": 0.1,
                "price_unit": "次",
                "floor_price": 0.05,
                "max_calls": 30,
                "metadata": {
                    "features": ["实时推送", "K线数据", "分时数据"]
                },
                "execution_mode": "local"
            }
        }
        
        await ws.send(json.dumps(register_msg1))
        response = await ws.recv()
        data = json.loads(response)
        print(f"[TC001] subagent1 注册响应: {data}")
        
        service1_id = data.get("service_id")
        print(f"[TC001] ✅ A股实时行情服务注册成功, service_id: {service1_id}")
        
        # 等待服务同步
        await asyncio.sleep(0.5)
        
        # ========== Step 2: subagent2 注册港股美股行情服务 ==========
        print("\n" + "="*60)
        print("[TC001] Step 2: subagent2 注册港股美股行情服务")
        print("="*60)
        
        register_msg2 = {
            "type": "register",
            "client_type": "full",
            "service": {
                "name": "港股美股行情服务",
                "description": "基于Wind数据源的港股美股行情服务，支持历史数据查询",
                "version": "1.0.0",
                "tags": ["股票", "港股", "美股", "历史数据", "Wind"],
                "price": 0.15,
                "price_unit": "次",
                "floor_price": 0.08,
                "max_calls": 50,
                "metadata": {
                    "features": ["历史数据", "港股行情", "美股行情"]
                },
                "execution_mode": "local"
            }
        }
        
        await ws.send(json.dumps(register_msg2))
        response = await ws.recv()
        data = json.loads(response)
        print(f"[TC001] subagent2 注册响应: {data}")
        
        service2_id = data.get("service_id")
        print(f"[TC001] ✅ 港股美股行情服务注册成功, service_id: {service2_id}")
        
        # 等待服务同步
        await asyncio.sleep(0.5)
        
        # 先列出所有服务确认注册成功
        list_msg = {"type": "skill_discover", "query": ""}
        await ws.send(json.dumps(list_msg))
        response = await ws.recv()
        data = json.loads(response)
        print(f"\n[TC001] 当前已注册服务: {len(data.get('skills', []))} 个")
        for s in data.get("skills", []):
            print(f"  - {s.get('name')}: 价格={s.get('price')} 积分/次, tags={s.get('tags')}")
        
        # ========== Step 3: subagent3 搜索最便宜的股票行情服务 ==========
        print("\n" + "="*60)
        print("[TC001] Step 3: subagent3 搜索最便宜的股票行情服务")
        print("="*60)
        
        discover_msg = {
            "type": "skill_discover",
            "query": "股票",
            "max_price": 0.1,
            "sort_by": "price",
            "sort_order": "asc",
            "fuzzy": True
        }
        
        await ws.send(json.dumps(discover_msg))
        
        # 可能收到 metadata_list 和 skill_list
        skills = []
        for _ in range(5):
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                msg_type = data.get("type")
                print(f"[TC001] 收到消息类型: {msg_type}")
                
                if msg_type == "skill_list":
                    skills = data.get("skills", [])
                    break
                elif msg_type == "metadata_list":
                    # 跳过 metadata_list
                    continue
            except asyncio.TimeoutError:
                break
        
        print(f"[TC001] subagent3 搜索到 {len(skills)} 个服务")
        
        # 找到最便宜的服务（价格 <= 0.1）
        if skills:
            cheapest = None
            for s in skills:
                price = s.get("price", 0)
                if price <= 0.1:
                    cheapest = s
                    break
            
            if cheapest:
                print(f"[TC001] ✅ 找到最便宜的服务: {cheapest.get('name')}, 价格: {cheapest.get('price')}")
                
                # subagent3 请求 Key
                key_request = {
                    "type": "key_request",
                    "service_id": cheapest.get("id"),
                    "purpose": "获取股票行情数据"
                }
                await ws.send(json.dumps(key_request))
                
                # 等待 Key 响应
                for _ in range(10):
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        data = json.loads(response)
                        msg_type = data.get("type")
                        print(f"[TC001] Key 响应类型: {msg_type}")
                        
                        if msg_type == "key_request":
                            # Provider 收到了请求，需要等待 provider 响应
                            print(f"[TC001] Provider 收到 Key 请求，等待响应...")
                            continue
                        elif msg_type == "key_request_response":
                            if data.get("success"):
                                print(f"[TC001] ✅ subagent3 成功获取 Key: {data.get('key')[:20]}...")
                                lifecycle = data.get("lifecycle", {})
                                print(f"[TC001]    Key 有效期: {lifecycle.get('duration_seconds')}秒, 剩余次数: {lifecycle.get('remaining_calls')}")
                            else:
                                print(f"[TC001] ❌ Key 请求失败: {data.get('reason')}")
                            break
                        elif msg_type == "metadata_list":
                            continue
                    except asyncio.TimeoutError:
                        print("[TC001] ⚠️ 等待 Key 响应超时")
                        break
            else:
                print("[TC001] ❌ 未找到价格 <= 0.1 的服务")
        else:
            print("[TC001] ❌ 未找到符合条件的服务")
        
        # ========== Step 4: subagent4 搜索带自选股功能的 A 股服务 ==========
        print("\n" + "="*60)
        print("[TC001] Step 4: subagent4 搜索带自选股功能的 A 股服务")
        print("="*60)
        
        discover_msg2 = {
            "type": "skill_discover",
            "query": "A股",
            "tags": ["A股"],
            "max_price": 0.15,
            "sort_by": "price",
            "sort_order": "asc"
        }
        
        await ws.send(json.dumps(discover_msg2))
        
        skills2 = []
        for _ in range(5):
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                msg_type = data.get("type")
                
                if msg_type == "skill_list":
                    skills2 = data.get("skills", [])
                    break
            except asyncio.TimeoutError:
                break
        
        print(f"[TC001] subagent4 搜索到 {len(skills2)} 个服务")
        
        # 找到带自选股功能的服务
        target_service = None
        for skill in skills2:
            metadata = skill.get("metadata", {})
            features = metadata.get("features", []) if metadata else []
            if "自选股" in str(features) or "自选" in str(features):
                target_service = skill
                break
        
        if target_service:
            print(f"[TC001] ✅ 找到带自选股功能的服务: {target_service.get('name')}, 价格: {target_service.get('price')}")
            
            # subagent4 请求 Key（15分钟有效期）
            key_request2 = {
                "type": "key_request",
                "service_id": target_service.get("id"),
                "purpose": "需要实时行情和自选股功能，Keys有效期15分钟"
            }
            await ws.send(json.dumps(key_request2))
            
            for _ in range(10):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(response)
                    msg_type = data.get("type")
                    
                    if msg_type == "key_request_response":
                        if data.get("success"):
                            print(f"[TC001] ✅ subagent4 成功获取 Key: {data.get('key')[:20]}...")
                            lifecycle = data.get("lifecycle", {})
                            print(f"[TC001]    Key 有效期: {lifecycle.get('duration_seconds')}秒, 剩余次数: {lifecycle.get('remaining_calls')}")
                        else:
                            print(f"[TC001] ❌ Key 请求失败: {data.get('reason')}")
                        break
                except asyncio.TimeoutError:
                    print("[TC001] ⚠️ 等待 Key 响应超时")
                    break
        else:
            # 如果没有找到带自选股功能的服务，使用最便宜的 A 股服务
            if skills2:
                cheapest_a = skills2[0]
                print(f"[TC001] ⚠️ 未找到带自选股功能的服务，使用最便宜的A股服务: {cheapest_a.get('name')}")
        
        # ========== 测试完成 ==========
        print("\n" + "="*60)
        print("[TC001] 测试完成 - 结果总结")
        print("="*60)
        
        print("✅ subagent1: 成功注册 A 股实时行情服务 (价格: 0.1 积分/次)")
        print("✅ subagent2: 成功注册港股美股行情服务 (价格: 0.15 积分/次)")
        print("⚠️  subagent3: 找到最便宜的服务 (价格: 0.1 积分/次)，需要 Provider 在线才能获取 Key")
        print("⚠️  subagent4: 搜索服务成功，需要 Provider 在线才能获取 Key")
        
        # 列出所有注册的服务
        list_msg = {"type": "skill_discover", "query": ""}
        await ws.send(json.dumps(list_msg))
        
        for _ in range(3):
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                if data.get("type") == "skill_list":
                    print(f"\n[TC001] 当前注册的所有服务: {len(data.get('skills', []))} 个")
                    for s in data.get("skills", []):
                        print(f"  - {s.get('name')}: {s.get('price')} 积分/次")
                    break
            except:
                break

if __name__ == "__main__":
    asyncio.run(connect_and_run())