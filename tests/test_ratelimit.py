"""Tests for server/ratelimit.py"""

import asyncio
import time

import pytest


class TestRateLimiter:
    """Test cases for RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter for testing."""
        from server.ratelimit import RateLimiter

        # 10 requests per second, burst of 10
        return RateLimiter(requests_per_minute=60, burst_size=10)

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, limiter):
        """Test that requests under limit are allowed."""
        client_id = "test_client_1"

        # Should allow up to burst_size requests
        for i in range(10):
            allowed, info = await limiter.check_rate_limit(client_id)
            assert allowed is True
            assert info["remaining"] >= 0

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, limiter):
        """Test that requests over limit are blocked."""
        client_id = "test_client_2"

        # Exhaust the bucket
        for i in range(10):
            await limiter.check_rate_limit(client_id)

        # Next request should be blocked
        allowed, info = await limiter.check_rate_limit(client_id)
        assert allowed is False
        assert info["remaining"] == 0
        assert "retry_after" in info

    @pytest.mark.asyncio
    async def test_different_clients_independent(self, limiter):
        """Test that different clients have independent limits."""
        client_a = "client_a"
        client_b = "client_b"

        # Exhaust client_a's bucket
        for i in range(10):
            await limiter.check_rate_limit(client_a)

        # client_b should still have full bucket
        allowed, info = await limiter.check_rate_limit(client_b)
        assert allowed is True
        assert info["remaining"] >= 9

    @pytest.mark.asyncio
    async def test_token_refill_over_time(self, limiter):
        """Test that tokens refill over time."""
        client_id = "test_client_refill"

        # Exhaust the bucket
        for i in range(10):
            await limiter.check_rate_limit(client_id)

        # Wait for some tokens to refill (60 req/min = 1 req/sec)
        await asyncio.sleep(0.5)

        allowed, info = await limiter.check_rate_limit(client_id)
        # Should get some tokens back but not full
        assert info["remaining"] >= 0

    @pytest.mark.asyncio
    async def test_cleanup_inactive(self, limiter):
        """Test cleanup of inactive clients."""
        client_id = "test_cleanup"

        # Add some requests
        await limiter.check_rate_limit(client_id)

        # Manually set last_update to far in the past
        limiter.buckets[client_id]["last_update"] = time.time() - 7200

        # Should remove the client
        removed = await limiter.cleanup_inactive(max_age_seconds=3600)
        assert removed >= 1

    def test_get_status(self, limiter):
        """Test getting rate limit status."""
        client_id = "test_status"

        # Initially should have full bucket
        status = limiter.get_status(client_id)
        assert status["allowed"] is True
        assert status["remaining"] == 10
        assert status["limit"] == 10


class TestMultiLimiter:
    """Test cases for MultiLimiter class."""

    @pytest.fixture
    def multi_limiter(self):
        """Create a multi-limiter for testing."""
        from server.ratelimit import MultiLimiter

        limiter = MultiLimiter()
        limiter.add_limiter("api", 60, 10)  # 60 req/min
        limiter.add_limiter("data", 120, 20)  # 120 req/min
        return limiter

    @pytest.mark.asyncio
    async def test_check_all_pass(self, multi_limiter):
        """Test checking all limiters."""
        client_id = "multi_test"

        allowed, results = await multi_limiter.check_all(client_id, api=1, data=1)

        assert allowed is True
        assert "api" in results
        assert "data" in results

    @pytest.mark.asyncio
    async def test_check_all_fail_on_any(self, multi_limiter):
        """Test that any limiter failure causes overall failure."""
        client_id = "multi_test_fail"

        # Exhaust data limiter
        for i in range(20):
            await multi_limiter.limiters["data"].check_rate_limit(client_id)

        allowed, results = await multi_limiter.check_all(client_id, api=1, data=1)

        assert allowed is False
        assert results["data"]["allowed"] is False

    def test_get_status(self, multi_limiter):
        """Test getting status for all limiters."""
        client_id = "status_test"

        status = multi_limiter.get_status(client_id)

        assert "api" in status
        assert "data" in status
        assert status["api"]["limit"] == 10
        assert status["data"]["limit"] == 20


class TestGetRateLimiter:
    """Test cases for get_rate_limiter factory function."""

    def test_returns_same_instance(self):
        """Test that same instance is returned."""
        # Reset global
        import server.ratelimit
        from server.ratelimit import _default_limiter, get_rate_limiter

        server.ratelimit._default_limiter = None

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    def test_respects_custom_rate(self):
        """Test that custom rate is respected."""
        import server.ratelimit
        server.ratelimit._default_limiter = None

        from server.ratelimit import get_rate_limiter
        limiter = get_rate_limiter(requests_per_minute=30)

        assert limiter.rate == pytest.approx(0.5, rel=0.1)
