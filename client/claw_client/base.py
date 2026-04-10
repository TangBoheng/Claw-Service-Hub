"""Base client for all Claw Service Hub clients."""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets.client import WebSocketClientProtocol

from .exceptions import ConnectionError, TimeoutError
from .utils import deserialize_message, serialize_message


class BaseClient(ABC):
    """
    所有 Claw Service Hub 客户端的抽象基类。

    提供公共功能:
    - WebSocket 连接管理
    - 消息接收循环
    - 心跳保活
    - 请求/响应管理
    """

    def __init__(self, url: str = "ws://localhost:8765", heartbeat_interval: int = 15):
        """
        初始化 BaseClient。

        Args:
            url: Hub 服务地址
            heartbeat_interval: 心跳间隔（秒）
        """
        self.url = url
        self.heartbeat_interval = heartbeat_interval
        self.client_id = f"client_{uuid.uuid4().hex[:8]}"

        # 连接状态
        self.websocket: Optional[WebSocketClientProtocol] = None
        self._running = False

        # 请求/响应管理
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._request_handlers: Dict[str, Callable] = {}

        # 消息回调
        self._message_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    # ==================== 连接管理 ====================

    async def connect(self) -> bool:
        """
        建立 WebSocket 连接。

        Returns:
            True 如果连接成功
        """
        try:
            self.websocket = await websockets.connect(
                self.url,
                ping_interval=None,  # 我们自己处理心跳
                close_timeout=5,
            )
            self._running = True

            # 启动后台任务
            asyncio.create_task(self._receive_loop())
            asyncio.create_task(self._heartbeat_loop())

            # 调用子类钩子
            await self._on_connected()

            return True
        except Exception as e:
            raise ConnectionError(self.url, str(e))

    async def disconnect(self):
        """断开 WebSocket 连接。"""
        self._running = False

        # 取消所有待处理的请求
        for future in self._response_futures.values():
            if not future.done():
                future.set_exception(ConnectionError(self.url, "Client disconnected"))
        self._response_futures.clear()

        if self.websocket:
            await self.websocket.close()

        await self._on_disconnected()

    async def _receive_loop(self):
        """接收并处理来自服务器的消息。"""
        try:
            async for raw_message in self.websocket:
                await self._process_message(raw_message)
        except websockets.exceptions.ConnectionClosed:
            self._running = False
        except Exception as e:
            print(f"[{self.client_id}] Receive error: {e}")
            self._running = False

    async def _heartbeat_loop(self):
        """定期发送心跳以保持连接活跃。"""
        while self._running:
            await asyncio.sleep(self.heartbeat_interval)
            try:
                await self._send_heartbeat()
            except Exception as e:
                print(f"[{self.client_id}] Heartbeat error: {e}")
                self._running = False

    async def _send_heartbeat(self):
        """发送心跳消息。"""
        if self.websocket and self.websocket.open:
            message = serialize_message({"type": "heartbeat", "client_id": self.client_id})
            await self.websocket.send(message)

    # ==================== 消息处理 ====================

    async def _process_message(self, raw_message: str):
        """
        处理接收到的消息。

        Args:
            raw_message: 原始 JSON 消息
        """
        try:
            message = deserialize_message(raw_message)
        except json.JSONDecodeError:
            print(f"[{self.client_id}] Invalid JSON: {raw_message[:100]}")
            return

        msg_type = message.get("type")

        # 调用消息回调
        for callback in self._message_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"[{self.client_id}] Callback error: {e}")

        # 处理响应
        request_id = message.get("request_id")
        if request_id and request_id in self._response_futures:
            future = self._response_futures.pop(request_id)
            if not future.done():
                future.set_result(message)
            return

        # 处理请求
        if "payload" in message or msg_type in ("request", "key_request", "channel_request"):
            await self._handle_request(message)

        # 子类特定处理
        await self._handle_message(message)

    async def _handle_request(self, message: Dict[str, Any]):
        """
        处理服务器发来的请求。

        Args:
            message: 请求消息
        """
        msg_type = message.get("type")
        handler = self._request_handlers.get(msg_type)

        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                print(f"[{self.client_id}] Handler error for {msg_type}: {e}")

    @abstractmethod
    async def _on_connected(self):
        """连接建立后的钩子（子类实现）。"""
        pass

    @abstractmethod
    async def _on_disconnected(self):
        """断开连接后的钩子（子类实现）。"""
        pass

    @abstractmethod
    async def _handle_message(self, message: Dict[str, Any]):
        """
        处理特定类型的消息（子类实现）。

        Args:
            message: 消息字典
        """
        pass

    # ==================== 请求/响应管理 ====================

    async def _send_request(
        self,
        msg_type: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        发送请求并等待响应。

        Args:
            msg_type: 消息类型
            payload: 请求负载
            timeout: 超时时间（秒）

        Returns:
            响应消息

        Raises:
            TimeoutError: 请求超时
            ConnectionError: 未连接
        """
        if not self.websocket or not self.websocket.open:
            raise ConnectionError(self.url, "Not connected")

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        future = asyncio.Future()
        self._response_futures[request_id] = future

        # 构建并发送请求
        message = {
            "type": msg_type,
            "payload": payload,
            "request_id": request_id,
            "client_id": self.client_id,
        }

        await self.websocket.send(serialize_message(message))

        # 等待响应
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._response_futures.pop(request_id, None)
            raise TimeoutError(msg_type, timeout)

    async def send(self, message: Dict[str, Any]):
        """
        发送消息（不等待响应）。

        Args:
            message: 消息字典
        """
        if self.websocket and self.websocket.open:
            await self.websocket.send(serialize_message(message))

    # ==================== 回调注册 ====================

    def on_message(self, callback: Callable[[Dict[str, Any]], Any]):
        """
        注册消息回调。

        Args:
            callback: 回调函数，接收消息字典
        """
        self._message_callbacks.append(callback)

    def register_handler(self, msg_type: str, handler: Callable[[Dict[str, Any]], Any]):
        """
        注册请求处理器。

        Args:
            msg_type: 消息类型
            handler: 处理函数
        """
        self._request_handlers[msg_type] = handler

    # ==================== 上下文管理器 ====================

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口。"""
        await self.disconnect()
