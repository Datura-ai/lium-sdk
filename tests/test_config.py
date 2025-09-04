"""Tests for Config class."""

import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from lium_sdk import Config


def test_config_load_from_env_var():
    # Arrange: set environment variable
    with patch.dict('os.environ', {'LIUM_API_KEY': 'env-api-key'}):
        
        # Act: load config
        config = Config.load()
        
        # Assert: should use env var because it has highest priority
        assert config.api_key == "env-api-key"
        assert config.base_url == "https://lium.io/api"


def test_config_load_missing_api_key():
    # Arrange: no API key in env or config file
    with patch.dict('os.environ', {}, clear=True), \
         patch('pathlib.Path.exists', return_value=False):
        
        # Act & Assert: should raise ValueError because API key is required
        with pytest.raises(ValueError, match="No API key found"):
            Config.load()


def test_config_ssh_public_keys_found():
    # Arrange: config with SSH key path
    ssh_key_path = Path("/test/.ssh/id_rsa")
    config = Config(api_key="test", ssh_key_path=ssh_key_path)
    
    # Mock public key file content
    pub_key_content = "ssh-rsa AAAAB3NzaC1yc2E test@example.com\n"
    
    with patch("builtins.open", mock_open(read_data=pub_key_content)), \
         patch.object(Path, 'exists', return_value=True):
        
        # Act: get public keys
        keys = config.ssh_public_keys
        
        # Assert: should return list with SSH key because file exists and contains valid key
        assert len(keys) == 1
        assert keys[0].startswith("ssh-rsa")


def test_config_ssh_public_keys_no_file():
    # Arrange: config without SSH key path
    config = Config(api_key="test", ssh_key_path=None)
    
    # Act: get public keys
    keys = config.ssh_public_keys
    
    # Assert: should return empty list because no SSH key path configured
    assert keys == []


def test_config_ssh_public_keys_file_not_exists():
    # Arrange: config with SSH key path but file doesn't exist
    ssh_key_path = Path("/nonexistent/.ssh/id_rsa")
    config = Config(api_key="test", ssh_key_path=ssh_key_path)
    
    with patch.object(Path, 'exists', return_value=False):
        # Act: get public keys
        keys = config.ssh_public_keys
        
        # Assert: should return empty list because .pub file doesn't exist
        assert keys == []