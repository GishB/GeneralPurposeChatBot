"""Tests for service-level endpoints in os_router."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.anyio
async def test_info_endpoint(async_client, monkeypatch):
    """``GET /info`` returns service metadata without crashing on missing fields."""
    mock_dist = MagicMock()
    mock_dist.metadata = {"Name": "UnionChatBot"}  # no Description key
    mock_dist.version = "0.3.0"
    monkeypatch.setattr("service.api.os_router.distribution", lambda name: mock_dist)

    response = await async_client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "UnionChatBot"
    assert data["type"] == "REST API"
    assert data["version"] == "0.3.0"
    assert data["description"] == ""
