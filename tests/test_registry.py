"""Registry module unit tests."""
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.registry import ServiceRegistry, ToolService


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return ServiceRegistry()


@pytest.fixture
def sample_service():
    """Create a sample service for testing."""
    return ToolService(
        id="test-service",
        name="Test Service",
        description="A test service",
        version="1.0.0",
        endpoint="ws://localhost:8765",
        tags=["test", "unit"],
        metadata={"test": True},
        emoji="🧪",
        requires={},
        execution_mode="local",
        interface_spec={}
    )


def test_service_creation(sample_service):
    """Test basic service creation."""
    assert sample_service.id == "test-service"
    assert sample_service.name == "Test Service"
    assert sample_service.status == "online"
    assert sample_service.last_heartbeat is not None


def test_registry_register(registry, sample_service):
    """Test registering a service."""
    skill_doc = "# Test Skill\nThis is a test skill document."
    
    service_id = asyncio.run(registry.register(sample_service, skill_doc))
    
    # Verify service was registered with correct ID
    assert service_id == "test-service"
    assert len(registry._services) == 1
    
    # Verify skill doc was stored
    stored_doc = registry.get_skill_doc(service_id)
    assert stored_doc == skill_doc


def test_registry_get(registry, sample_service):
    """Test getting a service by ID."""
    skill_doc = "# Test Skill"
    asyncio.run(registry.register(sample_service, skill_doc))
    
    retrieved = registry.get("test-service")
    assert retrieved is not None
    assert retrieved.id == "test-service"
    assert retrieved.name == "Test Service"


def test_registry_find_by_name(registry, sample_service):
    """Test finding services by name."""
    skill_doc = "# Test Skill"
    asyncio.run(registry.register(sample_service, skill_doc))
    
    # Exact match
    found = registry.find(name="Test Service")
    assert len(found) == 1
    assert found[0].id == "test-service"
    
    # Partial match
    found = registry.find(name="Test")
    assert len(found) == 1
    
    # No match
    found = registry.find(name="Nonexistent")
    assert len(found) == 0


def test_registry_find_by_tags(registry, sample_service):
    """Test finding services by tags."""
    skill_doc = "# Test Skill"
    asyncio.run(registry.register(sample_service, skill_doc))
    
    # Match single tag
    found = registry.find(tags=["test"])
    assert len(found) == 1
    
    # Match multiple tags (all must match)
    found = registry.find(tags=["test", "unit"])
    assert len(found) == 1
    
    # No match
    found = registry.find(tags=["prod"])
    assert len(found) == 0


def test_registry_heartbeat(registry, sample_service):
    """Test heartbeat functionality."""
    skill_doc = "# Test Skill"
    asyncio.run(registry.register(sample_service, skill_doc))
    
    original_time = sample_service.last_heartbeat
    
    # Update heartbeat
    asyncio.run(registry.heartbeat("test-service"))
    
    updated_service = registry.get("test-service")
    assert updated_service.last_heartbeat > original_time


def test_registry_cleanup_stale(registry, sample_service):
    """Test cleanup of stale services."""
    skill_doc = "# Test Skill"
    asyncio.run(registry.register(sample_service, skill_doc))
    
    # Make service stale by setting old heartbeat (as ISO string)
    service = registry.get("test-service")
    old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    service.last_heartbeat = old_time.isoformat()
    registry._services["test-service"] = service
    
    # Cleanup should remove stale service
    asyncio.run(registry.cleanup_stale())  # Uses default 5 minutes
    
    assert len(registry._services) == 0


def test_service_to_dict(sample_service):
    """Test service serialization to dict."""
    service_dict = sample_service.to_dict()
    
    assert service_dict["id"] == "test-service"
    assert service_dict["name"] == "Test Service"
    assert service_dict["status"] == "online"
    assert "last_heartbeat" in service_dict


def test_service_to_metadata_dict(sample_service):
    """Test service metadata serialization."""
    metadata_dict = sample_service.to_metadata_dict()
    
    # Metadata should contain expected fields
    expected_fields = {"id", "name", "description", "version", "tags", "emoji", "requires", "status", "tunnel_id", "execution_mode", "provider_client_id"}
    assert set(metadata_dict.keys()) == expected_fields
    assert metadata_dict["id"] == "test-service"


def test_service_to_skill_descriptor(sample_service):
    """Test service to skill descriptor conversion."""
    descriptor = sample_service.to_skill_descriptor()
    
    # skill_descriptor has service name in "name" field
    assert descriptor["name"] == "Test Service"
    assert descriptor["description"] == "A test service"
    assert descriptor["tags"] == ["test", "unit"]
    assert descriptor["execution_mode"] == "local"
    assert descriptor["skill_id"] == "test-service"
    assert "id" in descriptor
    assert "service_id" in descriptor