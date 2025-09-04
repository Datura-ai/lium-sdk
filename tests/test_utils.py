"""Tests for utility functions."""

import pytest

from lium_sdk import generate_huid, extract_gpu_type


def test_generate_huid_with_valid_id():
    # Arrange: we have a standard UUID
    test_id = "550e8400-e29b-41d4-a716-446655440000"
    
    # Act: generate human-readable ID
    result = generate_huid(test_id)
    
    # Assert: should be format "adjective-noun-XX" because MD5 hash produces predictable result
    assert isinstance(result, str)
    assert len(result.split("-")) == 3
    assert result.endswith("bd")  # last 2 chars of MD5 hash


def test_generate_huid_with_empty_string():
    # Arrange: empty ID string
    test_id = ""
    
    # Act: generate HUID
    result = generate_huid(test_id)
    
    # Assert: should return "invalid" for empty strings
    assert result == "invalid"


def test_extract_gpu_type_rtx_format():
    # Arrange: machine name with RTX GPU
    machine_name = "NVIDIA RTX 4090 Server"
    
    # Act: extract GPU type
    result = extract_gpu_type(machine_name)
    
    # Assert: should extract "RTX4090" format
    assert result == "RTX4090"


def test_extract_gpu_type_h100_format():
    # Arrange: machine name with H100 GPU
    machine_name = "Tesla H100 Machine"
    
    # Act: extract GPU type  
    result = extract_gpu_type(machine_name)
    
    # Assert: should extract "H100" format
    assert result == "H100"


def test_extract_gpu_type_a100_format():
    # Arrange: machine name with A100 GPU
    machine_name = "NVIDIA A100 80GB"
    
    # Act: extract GPU type
    result = extract_gpu_type(machine_name)
    
    # Assert: should extract "A100" format
    assert result == "A100"


def test_extract_gpu_type_unknown():
    # Arrange: machine name without recognizable GPU pattern
    machine_name = "Some Random Machine"
    
    # Act: extract GPU type
    result = extract_gpu_type(machine_name)
    
    # Assert: should return last word as fallback
    assert result == "Machine"


def test_extract_gpu_type_empty_string():
    # Arrange: empty machine name
    machine_name = ""
    
    # Act: extract GPU type
    result = extract_gpu_type(machine_name)
    
    # Assert: should return "Unknown" for empty strings
    assert result == "Unknown"