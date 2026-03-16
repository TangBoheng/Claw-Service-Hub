#!/usr/bin/env python3
"""
快速启动服务器脚本
"""
import sys
import os

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.main import main

if __name__ == "__main__":
    print("Starting Tool Service Hub...")
    print("WebSocket server will listen on ws://0.0.0.0:8765")
    print()
    main()