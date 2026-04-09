"""Storage module unit tests."""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.utils.storage import Storage, get_storage, init_storage


@pytest.fixture
def storage():
    """Create a temporary storage for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = init_storage(db_path)
    yield store

    store.close()
    os.unlink(db_path)


@pytest.fixture
def sample_service():
    """Create sample service data."""
    return {
        "id": "test-service-1",
        "name": "Test Service",
        "description": "A test service",
        "version": "1.0.0",
        "endpoint": "ws://localhost:8765",
        "status": "online",
        "tags": ["test", "unit"],
        "metadata": {"test": True},
        "emoji": "🧪",
        "requires": {},
        "execution_mode": "local",
        "interface_spec": {},
        "skill_doc": "# Test Skill\nThis is a test.",
        "last_heartbeat": datetime.now(),
    }


# ========== Service Tests ==========


def test_save_and_get_service(storage, sample_service):
    """Test saving and retrieving a service."""
    storage.save_service(sample_service)

    retrieved = storage.get_service("test-service-1")

    assert retrieved is not None
    assert retrieved["id"] == sample_service["id"]
    assert retrieved["name"] == sample_service["name"]
    assert retrieved["description"] == sample_service["description"]
    assert retrieved["tags"] == ["test", "unit"]


def test_get_nonexistent_service(storage):
    """Test getting a service that doesn't exist."""
    result = storage.get_service("nonexistent")
    assert result is None


def test_get_all_services(storage, sample_service):
    """Test getting all services."""
    storage.save_service(sample_service)

    # Add another service
    sample_service["id"] = "test-service-2"
    sample_service["name"] = "Test Service 2"
    storage.save_service(sample_service)

    all_services = storage.get_all_services()
    assert len(all_services) == 2


def test_update_service(storage, sample_service):
    """Test updating an existing service."""
    storage.save_service(sample_service)

    # Update service
    sample_service["name"] = "Updated Name"
    sample_service["status"] = "offline"
    storage.save_service(sample_service)

    retrieved = storage.get_service("test-service-1")
    assert retrieved["name"] == "Updated Name"
    assert retrieved["status"] == "offline"


def test_delete_service(storage, sample_service):
    """Test deleting a service."""
    storage.save_service(sample_service)

    deleted = storage.delete_service("test-service-1")
    assert deleted is True

    retrieved = storage.get_service("test-service-1")
    assert retrieved is None


def test_delete_nonexistent_service(storage):
    """Test deleting a service that doesn't exist."""
    result = storage.delete_service("nonexistent")
    assert result is False


def test_find_services_by_name(storage, sample_service):
    """Test finding services by name."""
    storage.save_service(sample_service)

    sample_service["id"] = "test-service-2"
    sample_service["name"] = "Another Service"
    storage.save_service(sample_service)

    found = storage.find_services(name="Test")
    assert len(found) == 1
    assert found[0]["name"] == "Test Service"


def test_find_services_by_tags(storage, sample_service):
    """Test finding services by tags."""
    storage.save_service(sample_service)

    found = storage.find_services(tags=["test"])
    assert len(found) == 1

    found = storage.find_services(tags=["test", "unit"])
    assert len(found) == 1

    found = storage.find_services(tags=["nonexistent"])
    assert len(found) == 0


def test_find_services_by_status(storage, sample_service):
    """Test finding services by status."""
    storage.save_service(sample_service)

    sample_service["id"] = "offline-service"
    sample_service["status"] = "offline"
    storage.save_service(sample_service)

    online = storage.find_services(status="online")
    assert len(online) == 1
    assert online[0]["id"] == "test-service-1"

    offline = storage.find_services(status="offline")
    assert len(offline) == 1
    assert offline[0]["id"] == "offline-service"


# ========== API Key Tests ==========


def test_save_and_get_api_key(storage):
    """Test saving and retrieving an API key."""
    key_hash = "hashed_key_123"
    storage.save_api_key(key_hash, "Test Key")

    key_info = storage.get_api_key(key_hash)

    assert key_info is not None
    assert key_info["key_hash"] == key_hash
    assert key_info["name"] == "Test Key"
    assert key_info["is_active"] == 1


def test_get_expired_api_key(storage):
    """Test that expired API keys return None."""
    key_hash = "hashed_key_456"
    expired_at = datetime.now() - timedelta(days=1)
    storage.save_api_key(key_hash, "Expired Key", expires_at=expired_at)

    key_info = storage.get_api_key(key_hash)
    assert key_info is None


def test_get_nonexistent_api_key(storage):
    """Test getting a non-existent API key."""
    result = storage.get_api_key("nonexistent_hash")
    assert result is None


def test_update_key_usage(storage):
    """Test updating key lifecycle usage count."""
    # Save a key lifecycle
    storage.save_key(
        {
            "key": "test_key_123",
            "service_id": "test-service",
            "consumer_id": "test-consumer",
            "duration_seconds": 3600,
            "max_calls": 100,
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "call_count": 0,
        }
    )

    # Update usage count
    storage.update_key_usage("test_key_123")

    # Verify count was incremented
    key_info = storage.get_key("test_key_123")
    assert key_info["call_count"] == 1


def test_deactivate_api_key(storage):
    """Test deactivating an API key."""
    key_hash = "hashed_key_abc"
    storage.save_api_key(key_hash, "Test Key")

    storage.deactivate_api_key(key_hash)

    key_info = storage.get_api_key(key_hash)
    assert key_info is None


# ========== Request Log Tests ==========


def test_log_request(storage):
    """Test logging a request."""
    storage.log_request(
        service_id="test-service-1",
        method="GET",
        path="/api/health",
        status_code=200,
        duration_ms=15.5,
    )

    logs = storage.get_request_logs()
    assert len(logs) == 1
    assert logs[0]["method"] == "GET"
    assert logs[0]["status_code"] == 200


def test_log_request_with_error(storage):
    """Test logging a request with error."""
    storage.log_request(
        service_id="test-service-1",
        method="POST",
        path="/api/data",
        status_code=500,
        duration_ms=150.0,
        error="Internal Server Error",
    )

    logs = storage.get_request_logs()
    assert len(logs) == 1
    assert logs[0]["error"] == "Internal Server Error"


def test_get_request_logs_limit(storage):
    """Test request log limit."""
    for i in range(10):
        storage.log_request(
            service_id="test-service-1",
            method="GET",
            path=f"/api/test/{i}",
            status_code=200,
            duration_ms=10.0,
        )

    logs = storage.get_request_logs(limit=5)
    assert len(logs) == 5


def test_get_request_logs_by_service(storage):
    """Test filtering logs by service ID."""
    storage.log_request(
        service_id="service-1", method="GET", path="/api/test", status_code=200, duration_ms=10.0
    )

    storage.log_request(
        service_id="service-2", method="GET", path="/api/test", status_code=200, duration_ms=10.0
    )

    logs = storage.get_request_logs(service_id="service-1")
    assert len(logs) == 1
    assert logs[0]["service_id"] == "service-1"


# ========== Rating Tests ==========


def test_save_rating(storage):
    """Test saving a rating."""
    storage.save_rating("test-service-1", 5, "Great service!")

    ratings = storage.get_service_ratings("test-service-1")
    assert len(ratings) == 1
    assert ratings[0]["rating"] == 5
    assert ratings[0]["comment"] == "Great service!"


def test_get_service_average_rating(storage):
    """Test getting average rating."""
    storage.save_rating("test-service-1", 5)
    storage.save_rating("test-service-1", 3)
    storage.save_rating("test-service-1", 4)

    avg = storage.get_service_average_rating("test-service-1")
    assert avg == 4.0


def test_get_average_rating_no_ratings(storage):
    """Test average rating when no ratings exist."""
    avg = storage.get_service_average_rating("nonexistent-service")
    assert avg is None


def test_get_ratings_for_nonexistent_service(storage):
    """Test getting ratings for non-existent service."""
    ratings = storage.get_service_ratings("nonexistent-service")
    assert len(ratings) == 0


# ========== Utility Tests ==========


def test_vacuum(storage, sample_service):
    """Test vacuum operation."""
    # Add some data
    for i in range(5):
        sample_service["id"] = f"service-{i}"
        storage.save_service(sample_service)

    # Vacuum should not raise
    storage.vacuum()


def test_get_storage_singleton():
    """Test that get_storage returns singleton."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # First call creates instance
        s1 = init_storage(db_path)

        # Second call returns existing instance (same object)
        s2 = get_storage(db_path)

        # Should be the same instance
        assert s1 is s2

        s1.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
        # Reset global for other tests
        import server.utils.storage
        server.utils.storage._storage = None
