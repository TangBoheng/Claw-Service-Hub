"""Key manager unit tests."""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.key_manager import KeyManager


@pytest.fixture
def key_manager():
    """Create a fresh key manager for each test."""
    return KeyManager()


def test_key_generation(key_manager):
    """Test generating a key."""
    key = key_manager.generate_key(service_id="test-service", consumer_id="test-consumer")

    assert key is not None
    assert len(key) > 0

    # Verify key info
    key_info = key_manager.get_key_info(key)
    assert key_info["service_id"] == "test-service"
    assert key_info["consumer_id"] == "test-consumer"
    assert key_info["is_active"] is True
    assert key_info["created_at"] is not None


def test_key_verification(key_manager):
    """Test key verification."""
    key = key_manager.generate_key(service_id="test-service", consumer_id="test-consumer")

    # Valid key for correct service
    result = key_manager.verify_key(key, "test-service")
    assert result["valid"] is True

    # Invalid key for wrong service
    result = key_manager.verify_key(key, "wrong-service")
    assert result["valid"] is False
    assert result["reason"] == "服务不匹配"


def test_key_expiration(key_manager):
    """Test key expiration based on duration."""
    key = key_manager.generate_key(
        service_id="test-service", consumer_id="test-consumer", duration_seconds=1  # 1 second
    )

    # Should be valid initially
    result = key_manager.verify_key(key, "test-service")
    assert result["valid"] is True

    # Wait for expiration
    import time

    time.sleep(1.1)

    # Should be expired
    result = key_manager.verify_key(key, "test-service")
    assert result["valid"] is False
    assert result["reason"] == "Key已过期"


def test_key_call_limit(key_manager):
    """Test key call limit."""
    key = key_manager.generate_key(
        service_id="test-service", consumer_id="test-consumer", max_calls=2
    )

    # First use
    key_manager.use_key(key)
    key_info = key_manager.get_key_info(key)
    assert key_info["remaining_calls"] == 1

    # Second use
    key_manager.use_key(key)
    key_info = key_manager.get_key_info(key)
    assert key_info["remaining_calls"] == 0

    # Third use should fail
    key_manager.use_key(key)
    result = key_manager.verify_key(key, "test-service")
    assert result["valid"] is False
    assert result["reason"] == "调用次数已用尽"


def test_key_revocation(key_manager):
    """Test key revocation."""
    key = key_manager.generate_key(service_id="test-service", consumer_id="test-consumer")

    # Should be valid initially
    result = key_manager.verify_key(key, "test-service")
    assert result["valid"] is True

    # Revoke key
    key_manager.revoke_key(key)

    # Should be invalid after revocation
    result = key_manager.verify_key(key, "test-service")
    assert result["valid"] is False
    assert result["reason"] == "Key已禁用"


def test_list_keys(key_manager):
    """Test listing keys."""
    # Generate multiple keys
    key1 = key_manager.generate_key("service1", "consumer1")
    key2 = key_manager.generate_key("service1", "consumer2")
    key3 = key_manager.generate_key("service2", "consumer1")

    # List all keys
    all_keys = key_manager.list_keys()
    assert len(all_keys) == 3

    # List keys for specific service
    service1_keys = key_manager.list_keys(service_id="service1")
    assert len(service1_keys) == 2

    # List only active keys
    active_keys = key_manager.list_keys(active_only=True)
    assert len(active_keys) == 3

    # Revoke one key and check
    key_manager.revoke_key(key1)
    active_keys = key_manager.list_keys(active_only=True)
    assert len(active_keys) == 2


def test_register_policy(key_manager):
    """Test registering lifecycle policy."""
    policy = {
        "default_duration_seconds": 3600,
        "default_max_calls": 100,
        "max_duration_seconds": 86400,
        "max_max_calls": 1000,
    }

    key_manager.register_policy("test-service", policy)

    # Verify policy was stored (check internal format)
    stored_policy = key_manager._service_policies.get("test-service")
    assert stored_policy is not None
    assert stored_policy["default"]["duration_seconds"] == 3600
    assert stored_policy["default"]["max_calls"] == 100


def test_generate_key_with_policy(key_manager):
    """Test generating key with policy defaults."""
    policy = {"default_duration_seconds": 1800, "default_max_calls": 50}  # 30 minutes

    key_manager.register_policy("test-service", policy)

    key = key_manager.generate_key("test-service", "test-consumer")
    key_info = key_manager.get_key_info(key)

    assert key_info["duration_seconds"] == 1800
    assert key_info["max_calls"] == 50


def test_key_storage_persistence():
    """Test key storage persistence."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_keys.db")

        # Create key manager with custom DB path
        km1 = KeyManager(db_path=db_path)
        key = km1.generate_key("test-service", "test-consumer")

        # Create another key manager with same DB path
        km2 = KeyManager(db_path=db_path)
        key_info = km2.get_key_info(key)

        assert key_info["service_id"] == "test-service"
        assert key_info["consumer_id"] == "test-consumer"
