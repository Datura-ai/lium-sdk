"""Tests for core API methods."""

import pytest
from unittest.mock import Mock, patch

from lium_sdk import Lium, LiumAuthError, LiumRateLimitError


def test_ls_returns_executors(mock_lium, mock_requests, sample_executor_data):
    # Arrange: mock successful API response with executor data
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = [sample_executor_data]
    mock_requests.request.return_value = mock_response
    
    # Act: get executors list
    executors = mock_lium.ls()
    
    # Assert: should return list with one ExecutorInfo because API returned one executor
    assert len(executors) == 1
    assert executors[0].id == "exec-123"
    assert executors[0].gpu_type == "RTX4090"
    assert executors[0].gpu_count == 2


def test_ls_filters_by_gpu_type(mock_lium, mock_requests):
    # Arrange: mock API response with different GPU types
    rtx_executor = {"id": "rtx-1", "machine_name": "RTX 4090", "specs": {"gpu": {"count": 1}}}
    h100_executor = {"id": "h100-1", "machine_name": "H100", "specs": {"gpu": {"count": 1}}}
    
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = [rtx_executor, h100_executor]
    mock_requests.request.return_value = mock_response
    
    # Act: filter by RTX GPU type
    executors = mock_lium.ls(gpu_type="RTX4090")
    
    # Assert: should return only RTX executor because we filtered by RTX4090
    assert len(executors) == 1
    assert executors[0].gpu_type == "RTX4090"


def test_ps_returns_pods(mock_lium, mock_requests, sample_pod_data):
    # Arrange: mock successful API response with pod data
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = [sample_pod_data]
    mock_requests.request.return_value = mock_response
    
    # Act: get pods list
    pods = mock_lium.ps()
    
    # Assert: should return list with one PodInfo because API returned one pod
    assert len(pods) == 1
    assert pods[0].id == "pod-456"
    assert pods[0].name == "test-pod"
    assert pods[0].status == "running"


def test_ps_updates_cache(mock_lium, mock_requests, sample_pod_data):
    # Arrange: mock API response
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = [sample_pod_data]
    mock_requests.request.return_value = mock_response
    
    # Act: get pods list
    mock_lium.ps()
    
    # Assert: should cache pod by different identifiers for quick lookup
    assert "pod-456" in mock_lium._pods_cache  # by ID
    assert "test-pod" in mock_lium._pods_cache  # by name


def test_templates_returns_list(mock_lium, mock_requests):
    # Arrange: mock API response with template data
    template_data = {
        "id": "template-123",
        "name": "ubuntu-22.04",
        "docker_image": "ubuntu",
        "docker_image_tag": "22.04",
        "category": "UBUNTU",
        "status": "active"
    }
    
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = [template_data]
    mock_requests.request.return_value = mock_response
    
    # Act: get templates list
    templates = mock_lium.templates()
    
    # Assert: should return list with one Template because API returned one template
    assert len(templates) == 1
    assert templates[0].name == "ubuntu-22.04"
    assert templates[0].docker_image == "ubuntu"


def test_request_handles_auth_error(mock_config):
    # Arrange: create fresh Lium instance and mock 401 response
    with patch('lium_sdk.requests') as mock_requests:
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_requests.request.return_value = mock_response
        
        # Create method without retry decorator
        lium = Lium(config=mock_config)
        
        # Act & Assert: should raise LiumAuthError because 401 means invalid API key  
        with pytest.raises(LiumAuthError, match="Invalid API key"):
            # Call internal method directly without retry
            lium._request.__wrapped__(lium, "GET", "/test")


def test_request_handles_rate_limit(mock_config):
    # Arrange: create fresh Lium instance and mock 429 response
    with patch('lium_sdk.requests') as mock_requests:
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_requests.request.return_value = mock_response
        
        # Create method without retry decorator
        lium = Lium(config=mock_config)
        
        # Act & Assert: should raise LiumRateLimitError because 429 means too many requests
        with pytest.raises(LiumRateLimitError, match="Rate limit exceeded"):
            # Call internal method directly without retry
            lium._request.__wrapped__(lium, "GET", "/test")


def test_resolve_pod_by_id(mock_lium):
    # Arrange: create test pod and add to cache
    from lium_sdk import PodInfo
    test_pod = PodInfo(
        id="pod-123", name="test", status="running", huid="test-huid",
        ssh_cmd=None, ports={}, created_at="", updated_at="",
        executor=None, template={}
    )
    mock_lium._pods_cache["pod-123"] = test_pod
    
    # Act: resolve pod by ID
    resolved = mock_lium._resolve_pod("pod-123")
    
    # Assert: should return the cached pod because ID matches
    assert resolved == test_pod
    assert resolved.id == "pod-123"


def test_resolve_pod_not_found(mock_lium, mock_requests):
    # Arrange: mock empty pods response
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = []
    mock_requests.request.return_value = mock_response
    
    # Act & Assert: should raise ValueError because pod doesn't exist
    with pytest.raises(ValueError, match="Pod 'nonexistent' not found"):
        mock_lium._resolve_pod("nonexistent")
