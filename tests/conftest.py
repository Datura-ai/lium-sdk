"""Test fixtures for Lium SDK."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from lium_sdk import Config, Lium


@pytest.fixture
def mock_config():
    """Mock config with test values."""
    config = Config(
        api_key="test-api-key",
        base_url="https://test-api.lium.io",
        ssh_key_path=Path("/test/.ssh/id_rsa")
    )
    return config


@pytest.fixture
def mock_lium(mock_config):
    """Mock Lium client."""
    return Lium(config=mock_config)


@pytest.fixture
def mock_requests():
    """Mock requests module."""
    with patch('lium_sdk.requests') as mock:
        yield mock


@pytest.fixture
def sample_executor_data():
    """Sample executor API response."""
    return {
        "id": "exec-123",
        "machine_name": "RTX 4090 Machine",
        "specs": {
            "gpu": {"count": 2, "details": [{"name": "RTX 4090"}]},
            "sysbox_runtime": True
        },
        "price_per_hour": 2.5,
        "location": {"country": "US"},
        "status": "available"
    }


@pytest.fixture
def sample_pod_data():
    """Sample pod API response."""
    return {
        "id": "pod-456",
        "pod_name": "test-pod",
        "status": "running",
        "ssh_connect_cmd": "ssh user@host.com -p 2222",
        "ports_mapping": {"22": 2222},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "executor": {
            "id": "exec-123",
            "machine_name": "RTX 4090 Machine"
        },
        "template": {"id": "template-789", "name": "ubuntu"}
    }