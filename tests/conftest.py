"""
Pytest configuration and fixtures for moisture_daemon tests.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, MagicMock
from configparser import ConfigParser


@pytest.fixture
def test_config():
    """Create a test configuration for testing."""
    config = ConfigParser()
    config.add_section('mqtt')
    config.set('mqtt', 'broker', 'test-mqtt-broker')
    config.set('mqtt', 'port', '1883')
    config.set('mqtt', 'username', 'test_user')
    config.set('mqtt', 'password', 'test_pass')
    config.set('mqtt', 'topic', 'moisture/+/data')
    config.set('mqtt', 'qos', '1')
    config.set('mqtt', 'keepalive', '60')
    
    config.add_section('database')
    config.set('database', 'host', 'test-db-host')
    config.set('database', 'port', '3306')
    config.set('database', 'name', 'test_moisture_db')
    config.set('database', 'user', 'test_user')
    config.set('database', 'password', 'test_pass')
    
    config.add_section('client')
    config.set('client', 'id', 'test_moisture_client')
    config.set('client', 'reconnect_delay', '5')
    config.set('client', 'max_runtime', '300')
    config.set('client', 'max_retries', '3')
    
    config.add_section('logging')
    config.set('logging', 'level', 'DEBUG')
    config.set('logging', 'file', 'tests/test.log')
    config.set('logging', 'max_size', '10485760')
    config.set('logging', 'backup_count', '5')
    config.set('logging', 'format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    return config


@pytest.fixture
def test_config_file(test_config):
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        test_config.write(f)
        config_file = f.name
    
    yield config_file
    
    # Cleanup
    if os.path.exists(config_file):
        os.unlink(config_file)


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client for testing."""
    mock_client = Mock()
    mock_client.connect.return_value = 0
    mock_client.disconnect.return_value = 0
    mock_client.subscribe.return_value = (0, 1)
    mock_client.publish.return_value = Mock(rc=0)
    mock_client.loop_start.return_value = None
    mock_client.loop_stop.return_value = None
    mock_client.is_connected.return_value = True
    return mock_client


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection for testing."""
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_connection.cursor.return_value = mock_cursor
    mock_connection.is_connected.return_value = True
    mock_connection.commit.return_value = None
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None
    mock_cursor.close.return_value = None
    return mock_connection


@pytest.fixture
def sample_mqtt_message():
    """Create a sample MQTT message for testing."""
    return {
        "device_id": "moisture_sensor_01",
        "timestamp": "2025-10-28T10:30:00Z",
        "moisture": 45.2,
        "temperature": 22.5,
        "humidity": 65.3,
        "battery": 87.5,
        "signal_strength": -45
    }


@pytest.fixture
def sample_mqtt_payload(sample_mqtt_message):
    """Create a sample MQTT payload as JSON string."""
    import json
    return json.dumps(sample_mqtt_message)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ['TESTING'] = '1'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_signal():
    """Mock signal handling for tests."""
    with pytest.MonkeyPatch().context() as m:
        mock_signal = Mock()
        m.setattr("signal.signal", mock_signal)
        yield mock_signal