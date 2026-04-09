"""
Simple rate limiting for Claw Service Hub.
Uses in-memory token bucket algorithm.

P2 错误提示优化：所有限流相关错误信息改为中文友好提示
"""

import asyncio
import time
from collections import defaultdict
from typing import Dict, Optional


# P2: 中文友好的错误消息
RATE_LIMIT_ERROR_MESSAGES = {
    "exceeded": "请求过于频繁，请稍后再试",
    "retry_after": "请等待 {seconds} 秒后重试",
    "no_limiter": "未配置对应的限流器",
    "limit_info": "您当前剩余 {remaining} 次请求机会，最多 {limit} 次/分钟",
    "bucket_exhausted": "当前时段请求配额已用尽",
}


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 60, burst_size: Optional[int] = None):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.rate = requests_per_minute / 60.0  # requests per second
        self.burst_size = burst_size or requests_per_minute
        self.buckets: Dict[str, Dict] = defaultdict(self._create_bucket)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # 5 minutes

    def _create_bucket(self) -> Dict:
        """Create a new token bucket."""
        return {"tokens": self.burst_size, "last_update": time.time()}

    def _refill_bucket(self, bucket: Dict) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(self.burst_size, bucket["tokens"] + elapsed * self.rate)
        bucket["last_update"] = now

    async def check_rate_limit(self, client_id: str, cost: int = 1) -> tuple[bool, Dict]:
        """
        Check if request is allowed and update bucket.

        Args:
            client_id: Unique identifier for the client
            cost: Token cost for this request (default 1)

        Returns:
            Tuple of (allowed: bool, info: Dict)
        """
        bucket = self.buckets[client_id]
        self._refill_bucket(bucket)

        if bucket["tokens"] >= cost:
            bucket["tokens"] -= cost
            return True, {
                "allowed": True,
                "remaining": int(bucket["tokens"]),
                "reset_at": bucket["last_update"]
                + (self.burst_size - bucket["tokens"]) / self.rate,
                # P2: 添加友好的中文提示
                "message": RATE_LIMIT_ERROR_MESSAGES["limit_info"].format(
                    remaining=int(bucket["tokens"]),
                    limit=self.burst_size
                ),
            }
        else:
            retry_after = int((self.burst_size - bucket["tokens"]) / self.rate)
            return False, {
                "allowed": False,
                "remaining": 0,
                "reset_at": bucket["last_update"]
                + (self.burst_size - bucket["tokens"]) / self.rate,
                "retry_after": retry_after,
                # P2: 添加友好的中文提示
                "message": RATE_LIMIT_ERROR_MESSAGES["exceeded"],
                "hint": RATE_LIMIT_ERROR_MESSAGES["retry_after"].format(seconds=retry_after),
            }

    async def cleanup_inactive(self, max_age_seconds: int = 3600) -> int:
        """
        Remove inactive client buckets to save memory.

        Args:
            max_age_seconds: Remove buckets not updated in this time

        Returns:
            Number of buckets removed
        """
        now = time.time()
        removed = 0

        to_remove = [
            client_id
            for client_id, bucket in self.buckets.items()
            if now - bucket["last_update"] > max_age_seconds
        ]

        for client_id in to_remove:
            del self.buckets[client_id]
            removed += 1

        return removed

    def get_status(self, client_id: str) -> Dict:
        """Get current rate limit status for a client."""
        bucket = self.buckets.get(client_id)
        if not bucket:
            return {
                "allowed": True,
                "remaining": self.burst_size,
                "limit": self.burst_size,
                "message": RATE_LIMIT_ERROR_MESSAGES["limit_info"].format(
                    remaining=self.burst_size,
                    limit=self.burst_size
                ),
            }

        self._refill_bucket(bucket)
        return {
            "allowed": bucket["tokens"] >= 1,
            "remaining": int(bucket["tokens"]),
            "limit": self.burst_size,
            "message": RATE_LIMIT_ERROR_MESSAGES["limit_info"].format(
                remaining=int(bucket["tokens"]),
                limit=self.burst_size
            ),
        }


class MultiLimiter:
    """Multiple rate limiters for different resource types."""

    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}

    def add_limiter(
        self, name: str, requests_per_minute: int, burst_size: Optional[int] = None
    ) -> None:
        """Add a named rate limiter."""
        self.limiters[name] = RateLimiter(requests_per_minute, burst_size)

    async def check_all(self, client_id: str, **costs) -> tuple[bool, Dict]:
        """
        Check all limiters.

        Args:
            client_id: Client identifier
            **costs: Resource names and their costs

        Returns:
            Tuple of (all_allowed: bool, results: Dict)
        """
        results = {}
        all_allowed = True

        for resource, cost in costs.items():
            if resource in self.limiters:
                allowed, info = await self.limiters[resource].check_rate_limit(client_id, cost)
                results[resource] = info
                if not allowed:
                    all_allowed = False
            else:
                results[resource] = {"allowed": True, "error": "No limiter configured"}

        return all_allowed, results

    def get_status(self, client_id: str) -> Dict:
        """Get status for all limiters."""
        return {name: limiter.get_status(client_id) for name, limiter in self.limiters.items()}


# Global rate limiter instance
_default_limiter: Optional[RateLimiter] = None


def get_rate_limiter(requests_per_minute: int = 60) -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = RateLimiter(requests_per_minute)
    return _default_limiter
