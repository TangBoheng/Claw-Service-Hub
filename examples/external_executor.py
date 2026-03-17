"""
外部执行器示例

模拟 subagent1 注册的外部服务（如 n8n webhook 或 python 服务）
这个服务实际处理业务请求。
"""
import asyncio
import json
from aiohttp import web


# 模拟 COCO 图片数据
MOCK_IMAGES = [
    {"id": "000001", "file_name": "000001.jpg", "label": "person"},
    {"id": "000002", "file_name": "000002.jpg", "label": "dog"},
    {"id": "000003", "file_name": "000003.jpg", "label": "cat"},
    {"id": "000004", "file_name": "000004.jpg", "label": "car"},
    {"id": "000005", "file_name": "000005.jpg", "label": "person"},
]


async def list_images(request):
    """列出图片"""
    params = await request.json() if request.can_read_body else {}
    limit = params.get("limit", 10)
    offset = params.get("offset", 0)

    images = MOCK_IMAGES[offset:offset + limit]

    return web.json_response({
        "images": images,
        "total": len(MOCK_IMAGES),
        "limit": limit,
        "offset": offset
    })


async def get_image(request):
    """获取单张图片"""
    params = await request.json() if request.can_read_body else {}
    image_id = params.get("id")

    image = next((img for img in MOCK_IMAGES if img["id"] == image_id), None)

    if image:
        # 模拟返回图片数据（base64）
        return web.json_response({
            "id": image_id,
            "file_name": image["file_name"],
            "label": image["label"],
            "data": "base64_encoded_image_data_here...",
            "url": f"http://localhost:8080/images/{image['file_name']}"
        })
    else:
        return web.json_response(
            {"error": "Image not found"},
            status=404
        )


async def health(request):
    """健康检查"""
    return web.json_response({"status": "ok"})


async def main():
    """启动外部执行器服务"""
    app = web.Application()

    # 路由
    app.router.add_post("/api/coco/list_images", list_images)
    app.router.add_post("/api/coco/get_image", get_image)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()

    print("="*50)
    print("外部执行器服务已启动")
    print("="*50)
    print("API 端点:")
    print("  POST /api/coco/list_images - 列出图片")
    print("  POST /api/coco/get_image    - 获取图片")
    print("  GET  /health                - 健康检查")
    print()
    print("监听: http://localhost:8080")
    print("="*50)

    # 保持运行
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[执行器] 停止")
