# 实战案例：每日穿衣推荐 + 图片服务

本案例展示如何使用 Claw Service Hub 构建一个完整的多代理工作流：获取天气信息并根据天气推荐穿着，同时获取搭配图片。

## 场景概述

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ weather-service │────▶│   Hub (WS:8765)  │◀────│ ng-image-service    │
│  (天气服务)     │     │   (服务中心)      │     │  (图片服务)          │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                               ▲
                               │
                        ┌──────┴──────┐
                        │  Consumer   │
                        │  (工作流)   │
                        └─────────────┘
```

## 最终效果

```
📍 Shanghai | 15°C | 阴
👔 穿衣建议：温度适中，建议穿长袖衬衫或薄外套
🎨 今日搭配灵感: 时尚春季穿搭
```

---

## 第一步：启动 Hub 服务器

```bash
pip install claw-service-hub && python -m server.main
```

---

## 第二步：启动天气服务 (Provider 1)

```python
# weather_service.py
import asyncio
from client.client import LocalServiceRunner

# 模拟天气数据
WEATHER_DATA = {
    "Shanghai": {"temp": 15, "condition": "阴", "humidity": 65, "wind": "东北风3级"},
    "Beijing": {"temp": 8, "condition": "晴", "humidity": 30, "wind": "北风2级"},
    "Shenzhen": {"temp": 25, "condition": "多云", "humidity": 75, "wind": "南风1级"},
    "Chengdu": {"temp": 12, "condition": "小雨", "humidity": 80, "wind": "西北风2级"},
}

async def get_weather(**params):
    """获取天气信息"""
    location = params.get("location", "Shanghai")
    weather = WEATHER_DATA.get(location, {"temp": 0, "condition": "未知"})
    
    return {
        "location": location,
        "temperature": weather["temp"],
        "condition": weather["condition"],
        "humidity": weather["humidity"],
        "wind": weather["wind"]
    }

async def suggest_clothing(**params):
    """根据天气推荐穿着"""
    temp = params.get("temperature", 20)
    condition = params.get("condition", "晴")
    
    if temp < 5:
        suggestion = "温度较低，建议穿羽绒服或厚棉服，佩戴围巾和手套"
    elif temp < 10:
        suggestion = "建议穿毛衣、加绒外套或轻薄羽绒服"
    elif temp < 15:
        suggestion = "温度适中，建议穿长袖衬衫或薄外套"
    elif temp < 20:
        suggestion = "建议穿长袖T恤或薄款针织衫"
    elif temp < 25:
        suggestion = "天气温暖，建议穿轻便服装，如T恤和牛仔裤"
    else:
        suggestion = "高温预警，建议穿浅色透气的衣物"
    
    # 根据天气状况补充
    if "雨" in condition:
        suggestion += "，记得带伞！"
    elif "阴" in condition:
        suggestion += "，天气阴沉建议带一件外套备用"
    
    return {"suggestion": suggestion, "temperature": temp}

async def main():
    runner = LocalServiceRunner(
        name="weather-service",
        description="提供城市天气查询和穿衣建议",
        hub_url="ws://localhost:8765",
        tags=["weather", "lifestyle", "daily"]
    )
    
    runner.register_handler("get_weather", get_weather)
    runner.register_handler("suggest_clothing", suggest_clothing)
    
    print("🌤️ 天气服务已启动...")
    await runner.run()

asyncio.run(main())
```

---

## 第三步：启动图片服务 (Provider 2)

```python
# image_service.py
import asyncio
import random
from client.client import LocalServiceRunner

# 模拟图片数据
IMAGE_COLLECTIONS = {
    "春季": ["时尚春季穿搭1", "春季街拍", "春装搭配"],
    "秋季": ["秋季时尚", "秋装搭配", "街拍秋装"],
    "冬季": ["冬季保暖穿搭", "时尚羽绒服", "秋冬过渡"],
    "夏季": ["夏季清爽穿搭", "夏日街拍", "轻薄材质"],
    "阴天": ["阴天情绪风", "灰色系穿搭", "室内拍照"],
    "晴天": ["阳光户外风", "亮色搭配", "户外街拍"],
}

async def get_inspiration_image(**params):
    """获取搭配灵感图片"""
    season = params.get("season", "春季")
    weather = params.get("weather", "晴")
    
    # 根据天气选择合适的图集
    if "雨" in weather:
        collection = "阴天"
    elif "阴" in weather:
        collection = "阴天"
    else:
        collection = season
    
    images = IMAGE_COLLECTIONS.get(collection, IMAGE_COLLECTIONS["春季"])
    selected = random.choice(images)
    
    return {
        "title": selected,
        "description": f"今日搭配灵感: {selected}",
        "season": collection
    }

async def main():
    runner = LocalServiceRunner(
        name="image-service",
        description="提供穿搭灵感图片",
        hub_url="ws://localhost:8765",
        tags=["image", "fashion", "inspiration"]
    )
    
    runner.register_handler("get_inspiration", get_inspiration_image)
    
    print("🖼️ 图片服务已启动...")
    await runner.run()

asyncio.run(main())
```

---

## 第四步：构建工作流 (Consumer)

```python
# workflow.py
import asyncio
from client.skill_client import SkillQueryClient

async def daily_recommendation(location: str = "Shanghai"):
    """每日推荐工作流"""
    client = SkillQueryClient("ws://localhost:8765")
    await client.connect()
    
    print(f"\n📍 获取 {location} 的天气信息...")
    
    # 1. 发现天气服务
    weather_services = await client.discover(tags=["weather"])
    if not weather_services:
        print("❌ 未找到天气服务")
        await client.disconnect()
        return
    
    # 2. 获取天气
    weather_result = await client.call_service(
        service_id=weather_services[0]["id"],
        method="get_weather",
        params={"location": location}
    )
    
    # 3. 获取穿衣建议
    clothing_result = await client.call_service(
        service_id=weather_services[0]["id"],
        method="suggest_clothing",
        params={
            "temperature": weather_result["temperature"],
            "condition": weather_result["condition"]
        }
    )
    
    # 4. 发现图片服务
    image_services = await client.discover(tags=["image"])
    if image_services:
        # 5. 获取搭配图片
        image_result = await client.call_service(
            service_id=image_services[0]["id"],
            method="get_inspiration",
            params={
                "season": "春季",  # 可以根据月份动态判断
                "weather": weather_result["condition"]
            }
        )
    else:
        image_result = None
    
    # 6. 输出结果
    print("\n" + "="*50)
    print(f"📍 {location} | {weather_result['temperature']}°C | {weather_result['condition']}")
    print(f"👔 穿衣建议：{clothing_result['suggestion']}")
    if image_result:
        print(f"🎨 {image_result['description']}")
    print("="*50)
    
    await client.disconnect()

# 运行工作流
asyncio.run(daily_recommendation("Shanghai"))
```

---

## 运行效果

启动顺序：
1. `python -m server.main` - 启动 Hub
2. `python weather_service.py` - 启动天气服务
3. `python image_service.py` - 启动图片服务
4. `python workflow.py` - 运行工作流

输出结果：
```
📍 获取 Shanghai 的天气信息...

==================================================
📍 Shanghai | 15°C | 阴
👔 穿衣建议：温度适中，建议穿长袖衬衫或薄外套，天气阴沉建议带一件外套备用
🎨 今日搭配灵感: 时尚春季穿搭
==================================================
```

---

## 进阶扩展

### 添加更多服务

1. **新闻服务** - 获取今日热门新闻
2. **日历服务** - 获取今日日程/纪念日
3. **出行服务** - 获取交通/限行信息

### 添加评分系统

```python
# 调用服务后进行评分
await client.rate_service(
    service_id=weather_services[0]["id"],
    rating=9,
    comment="天气准确，穿衣建议很实用"
)
```

### 错误处理

```python
try:
    result = await client.call_service(...)
except Exception as e:
    print(f"服务调用失败: {e}")
    # 降级处理：使用本地数据
```

---

## 下一步

- 📖 阅读 [Provider 指南](../guide/provider.md)
- 📖 阅读 [Consumer 指南](../guide/consumer.md)
- 🔧 查看 [API 参考](../api.md)