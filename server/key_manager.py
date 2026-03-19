"""
Key 生命周期管理模块
负责 Key 的生成、验证、使用追踪
"""
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List


class KeyLifecycle:
    """Key 生命周期"""
    
    def __init__(
        self,
        key: str,
        service_id: str,
        consumer_id: str,
        duration_seconds: int = 3600,
        max_calls: int = 100,
        created_at: datetime = None
    ):
        self.key = key
        self.service_id = service_id
        self.consumer_id = consumer_id
        
        # 时间维度
        self.created_at = created_at or datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=duration_seconds)
        
        # 次数维度
        self.max_calls = max_calls
        self.call_count = 0
        
        # 状态
        self.is_active = True
    
    def is_valid(self) -> bool:
        """检查 Key 是否有效"""
        now = datetime.now()
        return (
            self.is_active and
            now <= self.expires_at and
            self.call_count < self.max_calls
        )
    
    def use(self) -> bool:
        """使用 Key（调用计数+1）"""
        if not self.is_valid():
            return False
        self.call_count += 1
        return True
    
    def remaining_calls(self) -> int:
        """剩余调用次数"""
        return max(0, self.max_calls - self.call_count)
    
    def remaining_time(self) -> int:
        """剩余有效时间（秒）"""
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "key": self.key,
            "service_id": self.service_id,
            "consumer_id": self.consumer_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "max_calls": self.max_calls,
            "call_count": self.call_count,
            "remaining_calls": self.remaining_calls(),
            "remaining_time": self.remaining_time(),
            "is_active": self.is_active,
            "is_valid": self.is_valid()
        }


class KeyManager:
    """
    Key 管理器
    负责 Key 的生成、验证、存储
    """
    
    def __init__(self):
        # Key 存储: key -> KeyLifecycle
        self._keys: Dict[str, KeyLifecycle] = {}
        
        # 服务生命周期策略: service_id -> policy
        self._service_policies: Dict[str, dict] = {}
    
    def register_policy(self, service_id: str, policy: dict):
        """Provider 注册服务的生命周期策略"""
        self._service_policies[service_id] = {
            "default": {
                "duration_seconds": policy.get("duration_seconds", 3600),
                "max_calls": policy.get("max_calls", 100)
            },
            "custom": policy.get("custom_policies", {})
        }
    
    def get_policy(self, service_id: str) -> dict:
        """获取服务的生命周期策略"""
        return self._service_policies.get(service_id, {
            "default": {"duration_seconds": 3600, "max_calls": 100},
            "custom": {}
        })
    
    def generate_key(
        self,
        service_id: str,
        consumer_id: str,
        duration_seconds: int = None,
        max_calls: int = None,
        custom_policy: str = None
    ) -> str:
        """
        生成 Key
        
        Args:
            service_id: 服务ID
            consumer_id: 调用者ID
            duration_seconds: 有效时长（秒），None 则使用策略默认值
            max_calls: 最大调用次数，None 则使用策略默认值
            custom_policy: 自定义策略名称
            
        Returns:
            Key 字符串
        """
        # 获取策略配置
        policy = self.get_policy(service_id)
        
        if duration_seconds is None:
            if custom_policy and custom_policy in policy.get("custom", {}):
                duration_seconds = policy["custom"][custom_policy].get("duration_seconds", 3600)
            else:
                duration_seconds = policy["default"]["duration_seconds"]
        
        if max_calls is None:
            if custom_policy and custom_policy in policy.get("custom", {}):
                max_calls = policy["custom"][custom_policy].get("max_calls", 100)
            else:
                max_calls = policy["default"]["max_calls"]
        
        # 生成唯一 Key
        key = f"key_{uuid.uuid4().hex[:16]}"
        
        # 创建生命周期
        lifecycle = KeyLifecycle(
            key=key,
            service_id=service_id,
            consumer_id=consumer_id,
            duration_seconds=duration_seconds,
            max_calls=max_calls
        )
        
        self._keys[key] = lifecycle
        return key
    
    def verify_key(self, key: str, service_id: str) -> dict:
        """
        验证 Key
        
        Returns:
            {"valid": bool, "reason": str, "lifecycle": dict}
        """
        lifecycle = self._keys.get(key)
        
        # 1. Key 存在
        if not lifecycle:
            return {
                "valid": False,
                "reason": "Key不存在"
            }
        
        # 2. 服务匹配
        if service_id != lifecycle.service_id:
            return {
                "valid": False,
                "reason": "服务不匹配"
            }
        
        # 3. 活跃状态
        if not lifecycle.is_active:
            return {
                "valid": False,
                "reason": "Key已禁用"
            }
        
        # 4. 时间验证
        if not lifecycle.is_valid():
            if datetime.now() > lifecycle.expires_at:
                return {
                    "valid": False,
                    "reason": "Key已过期"
                }
            if lifecycle.call_count >= lifecycle.max_calls:
                return {
                    "valid": False,
                    "reason": "调用次数已用尽"
                }
        
        return {
            "valid": True,
            "reason": "",
            "lifecycle": lifecycle.to_dict()
        }
    
    def use_key(self, key: str) -> bool:
        """使用 Key（调用计数+1）"""
        lifecycle = self._keys.get(key)
        if lifecycle and lifecycle.is_valid():
            lifecycle.call_count += 1
            return True
        return False
    
    def revoke_key(self, key: str) -> bool:
        """撤销 Key"""
        lifecycle = self._keys.get(key)
        if lifecycle:
            lifecycle.is_active = False
            return True
        return False
    
    def list_keys(
        self,
        service_id: str = None,
        consumer_id: str = None,
        active_only: bool = False
    ) -> List[dict]:
        """列出 Key"""
        result = []
        for key, lifecycle in self._keys.items():
            if service_id and lifecycle.service_id != service_id:
                continue
            if consumer_id and lifecycle.consumer_id != consumer_id:
                continue
            if active_only and not lifecycle.is_active:
                continue
            result.append(lifecycle.to_dict())
        return result
    
    def get_key_info(self, key: str) -> Optional[dict]:
        """获取 Key 信息"""
        lifecycle = self._keys.get(key)
        return lifecycle.to_dict() if lifecycle else None
    
    def cleanup_expired(self):
        """清理已过期的 Key"""
        expired_keys = []
        for key, lifecycle in self._keys.items():
            if not lifecycle.is_valid():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._keys[key]
        
        return len(expired_keys)


# 全局实例
key_manager = KeyManager()