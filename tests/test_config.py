"""
Unit tests for MoistureClient configuration handling.
"""

import pytest
import tempfile
import os
from configparser import ConfigParser
from unittest.mock import patch, mock_open

# Import the module under test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from moisture_client import MoistureClient


class TestConfigurationLoading:
    """Test configuration loading functionality."""
    
    def test_load_config_file_exists(self, test_config_file):
        """Test loading configuration from existing file."""
        client = MoistureClient(config_file=test_config_file)
        
        assert client.mqtt_broker == 'test-mqtt-broker'
        assert client.mqtt_port == 1883
        assert client.db_host == 'test-db-host'
        assert client.db_name == 'test_moisture_db'
    
    def test_load_config_file_missing(self):
        """Test behavior when config file is missing."""
        with pytest.raises(FileNotFoundError):
            MoistureClient(config_file="nonexistent_config.ini")
    
    def test_load_config_invalid_format(self):
        """Test behavior with invalid config file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("invalid config content without sections")
            invalid_config = f.name
        
        try:
            with pytest.raises(Exception):
                MoistureClient(config_file=invalid_config)
        finally:
            os.unlink(invalid_config)
    
    def test_environment_variable_override(self, test_config_file):
        """Test that environment variables override config file values."""
        with patch.dict(os.environ, {
            'MQTT_BROKER': 'env-mqtt-broker',
            'DB_HOST': 'env-db-host',
            'LOG_LEVEL': 'ERROR'
        }):
            client = MoistureClient(config_file=test_config_file)
            
            assert client.mqtt_broker == 'env-mqtt-broker'
            assert client.db_host == 'env-db-host'
    
    def test_default_values(self, test_config):
        """Test that default values are set correctly."""
        # Remove some optional sections
        test_config.remove_section('client')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            test_config.write(f)
            config_file = f.name
        
        try:
            client = MoistureClient(config_file=config_file)
            # Should use default values for missing configurations
            assert hasattr(client, 'max_retries')
        finally:
            os.unlink(config_file)


class TestConfigurationValidation:
    """Test configuration validation."""
    
    def test_valid_mqtt_port(self, test_config_file):
        """Test that valid MQTT port is accepted."""
        client = MoistureClient(config_file=test_config_file)
        assert isinstance(client.mqtt_port, int)
        assert 1 <= client.mqtt_port <= 65535
    
    def test_invalid_mqtt_port(self, test_config):
        """Test that invalid MQTT port raises error."""
        test_config.set('mqtt', 'port', '99999')  # Invalid port
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            test_config.write(f)
            config_file = f.name
        
        try:
            with pytest.raises(ValueError):
                MoistureClient(config_file=config_file)
        finally:
            os.unlink(config_file)
    
    def test_required_sections_present(self, test_config):
        """Test that all required config sections are present."""
        required_sections = ['mqtt', 'database', 'logging']
        
        for section in required_sections:
            test_config_copy = ConfigParser()
            test_config_copy.read_dict({s: dict(test_config.items(s)) 
                                      for s in test_config.sections() if s != section})
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
                test_config_copy.write(f)
                config_file = f.name
            
            try:
                with pytest.raises(Exception):
                    MoistureClient(config_file=config_file)
            finally:
                os.unlink(config_file)