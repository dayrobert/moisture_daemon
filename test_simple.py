#!/usr/bin/env python3
"""
Simple unit tests for moisture_daemon that actually work.

This is a focused test suite that tests the actual methods and structure
of the MoistureClient class as it exists.
"""

import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock
from configparser import ConfigParser

# Add the parent directory to the path to import moisture_client
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from moisture_client import MoistureClient
except ImportError as e:
    print(f"Cannot import moisture_client: {e}")
    print("Make sure you're running from the moisture_daemon directory")
    sys.exit(1)


@pytest.fixture
def simple_config_file():
    """Create a simple test configuration file."""
    config = ConfigParser()
    
    # MQTT section
    config.add_section('mqtt')
    config.set('mqtt', 'broker', 'test-broker')
    config.set('mqtt', 'port', '1883')
    config.set('mqtt', 'username', '')
    config.set('mqtt', 'password', '')
    config.set('mqtt', 'topic', 'moisture/+/data')
    config.set('mqtt', 'qos', '1')
    config.set('mqtt', 'keepalive', '60')
    
    # Database section
    config.add_section('database')
    config.set('database', 'host', 'test-host')
    config.set('database', 'port', '3306')
    config.set('database', 'name', 'test_db')
    config.set('database', 'user', 'test_user')
    config.set('database', 'password', 'test_pass')
    
    # Client section
    config.add_section('client')
    config.set('client', 'id', 'test_client')
    config.set('client', 'reconnect_delay', '5')
    config.set('client', 'max_runtime', '300')
    config.set('client', 'max_retries', '3')
    
    # Logging section (without % interpolation)
    config.add_section('logging')
    config.set('logging', 'level', 'DEBUG')
    config.set('logging', 'file', 'test.log')
    config.set('logging', 'max_size', '1000000')
    config.set('logging', 'backup_count', '3')
    config.set('logging', 'format', 'simple')
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        config.write(f)
        config_file = f.name
    
    yield config_file
    
    # Cleanup
    if os.path.exists(config_file):
        os.unlink(config_file)


class TestMoistureClientBasics:
    """Test basic MoistureClient functionality."""
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_initialization(self, mock_mqtt, mock_db, simple_config_file):
        """Test that MoistureClient initializes without errors."""
        # Mock successful database connection
        mock_db_conn = Mock()
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        # Mock MQTT client
        mock_mqtt_client = Mock()
        mock_mqtt.return_value = mock_mqtt_client
        
        # Initialize client
        client = MoistureClient(config_file=simple_config_file)
        
        # Basic assertions
        assert client.config_file == simple_config_file
        assert hasattr(client, 'logger')
        assert hasattr(client, 'running')
        assert client.running is False
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_database_connection(self, mock_mqtt, mock_db, simple_config_file):
        """Test database connection method."""
        # Mock successful database connection
        mock_db_conn = Mock()
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        client = MoistureClient(config_file=simple_config_file)
        result = client._connect_database()
        
        assert result is True
        assert client.db_connection is not None
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_mqtt_connection(self, mock_mqtt_class, mock_db, simple_config_file):
        """Test MQTT connection method."""
        # Mock database
        mock_db_conn = Mock()
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        # Mock MQTT client
        mock_mqtt_client = Mock()
        mock_mqtt_client.connect.return_value = 0  # Success
        mock_mqtt_class.return_value = mock_mqtt_client
        
        client = MoistureClient(config_file=simple_config_file)
        result = client._connect_mqtt()
        
        assert result is True
        mock_mqtt_client.connect.assert_called_once()
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_signal_handler(self, mock_mqtt, mock_db, simple_config_file):
        """Test signal handler for graceful shutdown."""
        # Mock connections
        mock_db_conn = Mock()
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        mock_mqtt_client = Mock()
        mock_mqtt.return_value = mock_mqtt_client
        
        client = MoistureClient(config_file=simple_config_file)
        client.running = True
        
        # Test signal handler
        client._signal_handler(2, None)  # SIGINT
        assert client.running is False
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_cleanup(self, mock_mqtt, mock_db, simple_config_file):
        """Test cleanup method."""
        # Mock connections
        mock_db_conn = Mock()
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        mock_mqtt_client = Mock()
        mock_mqtt.return_value = mock_mqtt_client
        
        client = MoistureClient(config_file=simple_config_file)
        client.mqtt_client = mock_mqtt_client
        client.db_connection = mock_db_conn
        
        # Test cleanup
        client._cleanup()
        
        # Verify cleanup calls
        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()
        mock_db_conn.close.assert_called_once()


class TestMoistureClientMQTT:
    """Test MQTT-specific functionality."""
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_on_connect_callback(self, mock_mqtt_class, mock_db, simple_config_file):
        """Test MQTT on_connect callback."""
        # Mock database
        mock_db_conn = Mock()
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        # Mock MQTT client
        mock_mqtt_client = Mock()
        mock_mqtt_class.return_value = mock_mqtt_client
        
        client = MoistureClient(config_file=simple_config_file)
        
        # Test successful connection callback
        client._on_connect(mock_mqtt_client, None, None, 0)
        
        # Should subscribe to topic
        mock_mqtt_client.subscribe.assert_called_once()
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_on_message_callback(self, mock_mqtt_class, mock_db, simple_config_file):
        """Test MQTT on_message callback with valid JSON."""
        # Mock database
        mock_db_conn = Mock()
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        mock_mqtt_client = Mock()
        mock_mqtt_class.return_value = mock_mqtt_client
        
        client = MoistureClient(config_file=simple_config_file)
        
        # Create mock message
        mock_message = Mock()
        mock_message.topic = "moisture/sensor_01/data"
        test_data = {
            "device_id": "sensor_01",
            "moisture": 45.2,
            "temperature": 22.5,
            "battery": 87.5
        }
        mock_message.payload.decode.return_value = '{"device_id": "sensor_01", "moisture": 45.2}'
        
        # Mock the _store_sensor_data method to avoid database calls
        with patch.object(client, '_store_sensor_data', return_value=True) as mock_store:
            client._on_message(mock_mqtt_client, None, mock_message)
            # Should attempt to store data
            mock_store.assert_called_once()


class TestMoistureClientDatabase:
    """Test database-specific functionality."""
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_store_sensor_data(self, mock_mqtt, mock_db, simple_config_file):
        """Test storing sensor data to database."""
        # Mock database connection and cursor
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        client = MoistureClient(config_file=simple_config_file)
        client.db_connection = mock_db_conn
        
        # Test data
        test_data = {
            "moisture": 45.2,
            "temperature": 22.5,
            "battery": 87.5
        }
        
        # Call store method
        result = client._store_sensor_data("sensor_01", test_data, "raw_payload")
        
        # Should execute database insert
        mock_cursor.execute.assert_called_once()
        mock_db_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('moisture_client.mysql.connector.connect')
    @patch('moisture_client.mqtt.Client')
    def test_create_tables(self, mock_mqtt, mock_db, simple_config_file):
        """Test database table creation."""
        # Mock database connection and cursor
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_conn.is_connected.return_value = True
        mock_db.return_value = mock_db_conn
        
        client = MoistureClient(config_file=simple_config_file)
        client.db_connection = mock_db_conn
        
        # Call create tables
        client._create_tables()
        
        # Should execute CREATE TABLE statements
        assert mock_cursor.execute.called


def test_import_works():
    """Simple test to ensure the module imports correctly."""
    assert MoistureClient is not None


if __name__ == "__main__":
    print("Running simple moisture_daemon tests...")
    pytest.main([__file__, "-v"])