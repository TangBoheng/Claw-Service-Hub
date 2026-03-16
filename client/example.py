"""
示例：启动一个本地工具服务
"""
import asyncio
import json


async def main():
    # 从 client 模块导入
    import sys
    sys.path.insert(0, "/home/t/.openclaw/workspace/tool-service-hub")
    
    from client.client import LocalServiceRunner
    
    # 定义服务处理函数
    async def process_csv(**params):
        """处理CSV数据"""
        filename = params.get("filename", "data.csv")
        operation = params.get("operation", "count")
        
        print(f"[Service] Processing {filename} with operation: {operation}")
        
        # 这里可以添加实际的 CSV 处理逻辑
        return {
            "filename": filename,
            "operation": operation,
            "result": f"Processed {filename} successfully",
            "rows": 100,
            "columns": 5
        }
    
    async def query_local_data(**params):
        """查询本地数据"""
        query = params.get("query", "")
        
        return {
            "query": query,
            "results": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
            ],
            "count": 2
        }
    
    # 创建服务运行器
    runner = LocalServiceRunner(
        name="csv-processor",
        description="处理本地CSV数据的服务",
        version="1.0.0",
        endpoint="http://localhost:8080",
        tags=["data", "csv", "processor"],
        hub_url="ws://localhost:8765"
    )
    
    # 注册处理函数
    runner.register_handler("process_csv", process_csv)
    runner.register_handler("query_local_data", query_local_data)
    
    print("Starting CSV Processor Service...")
    print("Connect to hub at: ws://localhost:8765")
    print("Available methods: process_csv, query_local_data")
    print()
    
    # 运行服务
    try:
        await runner.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())