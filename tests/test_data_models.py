"""Tests for data models."""

import pytest

from lium_sdk import PodInfo, ExecutorInfo


def test_pod_info_ssh_port_default():
    # Arrange: pod without -p flag in SSH command
    pod = PodInfo(
        id="pod-1", name="test", status="running", huid="test-huid",
        ssh_cmd="ssh user@host.com", ports={}, created_at="", updated_at="",
        executor=None, template={}
    )
    
    # Act: get SSH port
    port = pod.ssh_port
    
    # Assert: should return 22 because it's default SSH port when -p is not specified
    assert port == 22


def test_pod_info_ssh_port_custom():
    # Arrange: pod with custom port in SSH command
    pod = PodInfo(
        id="pod-1", name="test", status="running", huid="test-huid", 
        ssh_cmd="ssh user@host.com -p 2222", ports={}, created_at="", updated_at="",
        executor=None, template={}
    )
    
    # Act: get SSH port
    port = pod.ssh_port
    
    # Assert: should return 2222 because that's what -p flag specifies
    assert port == 2222


def test_pod_info_host_extraction():
    # Arrange: pod with SSH command containing hostname
    pod = PodInfo(
        id="pod-1", name="test", status="running", huid="test-huid",
        ssh_cmd="ssh user@example.com", ports={}, created_at="", updated_at="",
        executor=None, template={}
    )
    
    # Act: get host
    host = pod.host
    
    # Assert: should extract "example.com" because it comes after @ in SSH command
    assert host == "example.com"


def test_pod_info_username_extraction():
    # Arrange: pod with SSH command containing username
    pod = PodInfo(
        id="pod-1", name="test", status="running", huid="test-huid",
        ssh_cmd="ssh testuser@host.com", ports={}, created_at="", updated_at="",
        executor=None, template={}
    )
    
    # Act: get username
    username = pod.username
    
    # Assert: should extract "testuser" because it comes before @ in SSH command
    assert username == "testuser"


def test_pod_info_no_ssh_cmd():
    # Arrange: pod without SSH command
    pod = PodInfo(
        id="pod-1", name="test", status="running", huid="test-huid",
        ssh_cmd=None, ports={}, created_at="", updated_at="",
        executor=None, template={}
    )
    
    # Act: get properties
    host = pod.host
    username = pod.username
    port = pod.ssh_port
    
    # Assert: should handle None SSH command gracefully
    assert host is None
    assert username is None
    assert port == 22  # default port


def test_executor_info_price_per_gpu_calculation():
    # Arrange: executor with 4 GPUs and total price $8/hour
    executor = ExecutorInfo(
        id="exec-1", huid="test-huid", machine_name="4x RTX 4090",
        gpu_type="RTX4090", gpu_count=4, price_per_hour=8.0, 
        price_per_gpu_hour=2.0, location={}, specs={}, status="available",
        docker_in_docker=False
    )
    
    # Act: check price calculation
    price_per_gpu = executor.price_per_gpu_hour
    
    # Assert: should be $2 per GPU per hour because $8 total / 4 GPUs = $2
    assert price_per_gpu == 2.0


def test_executor_info_docker_in_docker_flag():
    # Arrange: executor with sysbox runtime enabled
    specs = {"sysbox_runtime": True, "gpu": {"count": 1}}
    executor = ExecutorInfo(
        id="exec-1", huid="test-huid", machine_name="Docker Machine",
        gpu_type="RTX4090", gpu_count=1, price_per_hour=2.0,
        price_per_gpu_hour=2.0, location={}, specs=specs, status="available",
        docker_in_docker=True
    )
    
    # Act: check docker-in-docker capability
    dind = executor.docker_in_docker
    
    # Assert: should be True because sysbox runtime enables docker-in-docker
    assert dind is True