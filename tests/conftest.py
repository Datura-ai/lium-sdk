"""Pytest configuration and fixtures for Lium SDK tests."""

import os
import time
import uuid
import pytest
import logging
from typing import Generator, Optional
from lium_sdk import Lium, PodInfo

# Suppress paramiko INFO logs (only show warnings and errors)
logging.getLogger("paramiko").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def lium_client() -> Lium:
    """Create a Lium client instance for testing."""
    # Try to create client - it will handle API key from env or config file
    try:
        client = Lium()
        # Verify we can actually connect
        executors = client.ls()
        if not executors:
            pytest.skip("No executors available - skipping integration tests")
        return client
    except ValueError as e:
        if "No API key found" in str(e):
            pytest.skip("No API key available - skipping integration tests")
        raise
    except Exception as e:
        pytest.skip(f"Cannot connect to Lium API: {e}")


@pytest.fixture(scope="function")
def test_pod_name() -> str:
    """Generate a unique test pod name."""
    # Use short UUID to avoid long names
    unique_id = str(uuid.uuid4())[:8]
    return f"test-pod-{unique_id}"


@pytest.fixture(scope="function")
def pod_lifecycle(lium_client: Lium, test_pod_name: str) -> Generator[Optional[PodInfo], None, None]:
    """
    Fixture that creates a pod, yields it for testing, then cleans up.
    
    This fixture handles the full lifecycle:
    1. Creates a pod with the cheapest available executor
    2. Waits for it to be ready
    3. Yields the pod for testing
    4. Cleans up by stopping and removing the pod
    """
    pod = None
    try:
        # Find the cheapest available executor
        executors = lium_client.ls()
        if not executors:
            pytest.skip("No executors available")
        
        # Sort by price and get the cheapest
        executor = sorted(executors, key=lambda x: x.price_per_hour)[0]
        print(f"\nUsing executor: {executor.huid} ({executor.gpu_type}) @ ${executor.price_per_hour}/h")
        
        # Use specific template that works
        # Template: PyTorch 2.4.0-py3.12-cuda12.2.0-devel-ubuntu22.04
        template_id = "8c273d47-33fc-4237-805f-e96e685c53b8"
        print(f"Using template ID: {template_id}")
        
        # Create the pod
        print(f"Creating pod: {test_pod_name}")
        pod = lium_client.up(
            executor_id=executor.id,
            pod_name=test_pod_name,
            template_id=template_id
        )
        
        # Wait for pod to be ready (30 minutes timeout)
        print("Waiting for pod to be ready (up to 30 minutes)...")
        pod = lium_client.wait_ready(pod, timeout=1800)  # 30 minutes
        if not pod:
            # Pod didn't become ready, but we still need to clean it up
            print(f"Pod {test_pod_name} failed to become ready within 30 minutes")
            # Try to get the pod info for cleanup
            pods = lium_client.ps()
            pod = next((p for p in pods if p.name == test_pod_name), None)
            if not pod:
                pytest.fail("Pod failed to become ready and cannot be found for cleanup")
            pytest.fail("Pod failed to become ready within 30 minutes")
        
        print(f"Pod {pod.name} is ready!")
        
        # Check if pod has default backup configuration
        try:
            existing_configs = lium_client.backup_list(pod=pod)
            if existing_configs:
                print(f"Note: Pod has {len(existing_configs)} default backup config(s)")
                for config in existing_configs:
                    print(f"  - Config {config.id}: path={config.backup_path}, freq={config.backup_frequency_hours}h")
        except Exception as e:
            print(f"Could not check for default backup configs: {e}")
        
        yield pod
        
    finally:
        # Cleanup: stop and remove the pod
        if pod:
            try:
                print(f"\nCleaning up pod: {pod.name}")
                lium_client.down(pod)
                time.sleep(2)  # Give it a moment to stop
                lium_client.rm(pod)
                print(f"Pod {pod.name} cleaned up successfully")
            except Exception as e:
                print(f"Warning: Failed to cleanup pod {pod.name}: {e}")


@pytest.fixture
def test_files_content() -> dict:
    """Test files with content for backup/restore testing."""
    # Generate unique content with timestamp and random ID to ensure uniqueness
    import random
    import datetime
    
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().isoformat()
    
    return {
        "/root/test_file1.txt": f"Test run ID: {unique_id}\nTimestamp: {timestamp}\nPierre's secret recipe #1\nLine 2 of file 1",
        "/root/test_file2.txt": f"Test run ID: {unique_id}\nTimestamp: {timestamp}\nPierre's baguette formula\nWith multiple lines\nAnd more data\nRandom: {random.randint(1000, 9999)}",
        "/root/test_dir/nested_file.txt": f"Test run ID: {unique_id}\nNested file in directory\nPierre's croissant technique\nTimestamp: {timestamp}",
    }