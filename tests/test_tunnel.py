"""Tunnel module unit tests."""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.tunnel import Tunnel, TunnelManager


@pytest.fixture
def tunnel_manager():
    """Create a fresh tunnel manager for each test."""
    return TunnelManager()


def test_tunnel_creation():
    """Test basic tunnel creation."""
    tunnel = Tunnel(id="test-tunnel", service_id="test-service", client_id="test-client")

    assert tunnel.id == "test-tunnel"
    assert tunnel.service_id == "test-service"
    assert tunnel.client_id == "test-client"
    assert tunnel.status == "active"


def test_tunnel_to_dict():
    """Test tunnel serialization to dict."""
    tunnel = Tunnel(id="test-tunnel", service_id="test-service", client_id="test-client")

    tunnel_dict = tunnel.to_dict()

    assert tunnel_dict["id"] == "test-tunnel"
    assert tunnel_dict["service_id"] == "test-service"
    assert tunnel_dict["client_id"] == "test-client"
    assert tunnel_dict["status"] == "active"
    assert "last_active" in tunnel_dict


@pytest.mark.asyncio
async def test_tunnel_manager_create_tunnel(tunnel_manager):
    """Test creating a tunnel."""
    tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")

    assert tunnel is not None
    assert tunnel.service_id == "test-service"
    assert tunnel.client_id == "test-client"
    assert len(tunnel_manager._tunnels) == 1


@pytest.mark.asyncio
async def test_tunnel_manager_get_tunnel(tunnel_manager):
    """Test getting a tunnel by ID."""
    created_tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")

    retrieved_tunnel = tunnel_manager.get_tunnel(created_tunnel.id)
    assert retrieved_tunnel.id == created_tunnel.id


@pytest.mark.asyncio
async def test_tunnel_manager_get_tunnel_by_client(tunnel_manager):
    """Test getting a tunnel by client ID."""
    created_tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")

    retrieved_tunnel = tunnel_manager.get_tunnel_by_client("test-client")
    assert retrieved_tunnel.id == created_tunnel.id


@pytest.mark.asyncio
async def test_tunnel_manager_list_tunnels(tunnel_manager):
    """Test listing all tunnels."""
    await tunnel_manager.create_tunnel("service1", "client1")
    await tunnel_manager.create_tunnel("service2", "client2")

    tunnels = tunnel_manager.list_tunnels()
    assert len(tunnels) == 2


@pytest.mark.asyncio
async def test_tunnel_manager_update_activity(tunnel_manager):
    """Test updating tunnel activity."""
    tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")
    original_time = tunnel.last_active

    await tunnel_manager.update_activity(tunnel.id)
    updated_tunnel = tunnel_manager.get_tunnel(tunnel.id)

    assert updated_tunnel.last_active > original_time


@pytest.mark.asyncio
async def test_tunnel_manager_close_tunnel(tunnel_manager):
    """Test closing a tunnel."""
    tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")
    tunnel_id = tunnel.id

    # Verify tunnel exists
    assert tunnel_manager.get_tunnel(tunnel_id) is not None

    await tunnel_manager.close_tunnel(tunnel_id)

    # Tunnel should be removed after close
    assert tunnel_manager.get_tunnel(tunnel_id) is None


@pytest.mark.skip(reason="Async callback integration test - requires full WebSocket setup")
@pytest.mark.asyncio
async def test_tunnel_manager_forward_request(tunnel_manager):
    """Test forwarding a request through a tunnel."""
    tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")

    # Mock the on_request callback
    mock_callback = AsyncMock()
    tunnel_manager.on("request", mock_callback)

    success = await tunnel_manager.forward_request(
        tunnel_id=tunnel.id, request_id="req-123", method="test_method", params={"param1": "value1"}
    )

    assert success is True
    mock_callback.assert_called_once()


@pytest.mark.skip(reason="Async callback integration test - requires full WebSocket setup")
@pytest.mark.asyncio
async def test_tunnel_manager_handle_response(tunnel_manager):
    """Test handling a response from a tunnel."""
    tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")

    # Mock the on_response callback
    mock_callback = AsyncMock()
    tunnel_manager.on("response", mock_callback)

    await tunnel_manager.handle_response("req-123", {"result": "success"})

    mock_callback.assert_called_once_with("req-123", {"result": "success"})


@pytest.mark.asyncio
async def test_tunnel_manager_cleanup_inactive(tunnel_manager):
    """Test cleanup of inactive tunnels."""
    tunnel = await tunnel_manager.create_tunnel("test-service", "test-client")

    # Make tunnel inactive by setting old activity time (ISO format string)
    tunnel.last_active = "2020-01-01T00:00:00"
    tunnel_manager._tunnels[tunnel.id] = tunnel

    # Cleanup should remove inactive tunnel
    await tunnel_manager.cleanup_inactive(max_age_seconds=3600)  # 1 hour

    assert len(tunnel_manager._tunnels) == 0
