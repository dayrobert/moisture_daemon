"""
Unit tests for MoistureClient MQTT functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import paho.mqtt.client as mqtt

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from moisture_client import MoistureClient


class TestMQTTConnection:
    """Test MQTT connection functionality."""
    
    @patch('moisture_client.mqtt.Client')
    def test_mqtt_connection_success(self, mock_mqtt_class, test_config_file):
        """Test successful MQTT connection."""
        mock_client = Mock()
        mock_mqtt_class.return_value = mock_client
        mock_client.connect.return_value = 0  # Success
        
        client = MoistureClient(config_file=test_config_file)
        result = client._connect_mqtt()
        
        assert result is True
        mock_client.connect.assert_called_once()
        mock_client.loop_start.assert_called_once()
    
    @patch('moisture_client.mqtt.Client')
    def test_mqtt_connection_failure(self, mock_mqtt_class, test_config_file):
        """Test MQTT connection failure."""
        mock_client = Mock()
        mock_mqtt_class.return_value = mock_client
        mock_client.connect.return_value = 1  # Connection failed
        
        client = MoistureClient(config_file=test_config_file)
        result = client._connect_mqtt()
        
        assert result is False
        mock_client.connect.assert_called_once()
    
    @patch('moisture_client.mqtt.Client')
    def test_mqtt_subscription(self, mock_mqtt_class, test_config_file):
        """Test MQTT topic subscription."""
        mock_client = Mock()
        mock_mqtt_class.return_value = mock_client
        mock_client.connect.return_value = 0
        mock_client.subscribe.return_value = (0, 1)  # Success
        
        client = MoistureClient(config_file=test_config_file)
        client._connect_mqtt()
        
        # Check that subscription was called
        expected_topic = client.mqtt_topic
        mock_client.subscribe.assert_called_with(expected_topic, client.mqtt_qos)


class TestMQTTMessageHandling:
    """Test MQTT message processing."""
    
    def test_on_message_valid_json(self, test_config_file, sample_mqtt_payload):
        """Test processing valid JSON message."""
        with patch('moisture_client.mqtt.Client'):
            client = MoistureClient(config_file=test_config_file)
            
            # Mock database insertion
            with patch.object(client, '_insert_sensor_data') as mock_insert:
                mock_insert.return_value = True
                
                # Create mock message
                mock_message = Mock()
                mock_message.topic = "moisture/sensor_01/data"
                mock_message.payload.decode.return_value = sample_mqtt_payload
                
                # Process message
                client._on_message(None, None, mock_message)
                
                # Verify database insertion was called
                mock_insert.assert_called_once()
    
    def test_on_message_invalid_json(self, test_config_file):
        """Test processing invalid JSON message."""
        with patch('moisture_client.mqtt.Client'):
            client = MoistureClient(config_file=test_config_file)
            
            # Create mock message with invalid JSON
            mock_message = Mock()
            mock_message.topic = "moisture/sensor_01/data"
            mock_message.payload.decode.return_value = "invalid json content"
            
            # Process message - should not raise exception
            try:
                client._on_message(None, None, mock_message)
            except Exception as e:
                pytest.fail(f"Processing invalid JSON should not raise exception: {e}")
    
    def test_on_message_missing_fields(self, test_config_file):
        """Test processing message with missing required fields."""
        with patch('moisture_client.mqtt.Client'):
            client = MoistureClient(config_file=test_config_file)
            
            # Create message missing required fields
            incomplete_data = {"device_id": "sensor_01"}  # Missing other required fields
            
            mock_message = Mock()
            mock_message.topic = "moisture/sensor_01/data"
            mock_message.payload.decode.return_value = json.dumps(incomplete_data)
            
            # Mock database insertion
            with patch.object(client, '_insert_sensor_data') as mock_insert:
                client._on_message(None, None, mock_message)
                
                # Should handle gracefully - may or may not call insert depending on validation
                # The exact behavior depends on implementation
    
    def test_topic_parsing(self, test_config_file):
        """Test extraction of device ID from MQTT topic."""
        with patch('moisture_client.mqtt.Client'):
            client = MoistureClient(config_file=test_config_file)
            
            # Test various topic formats
            test_cases = [
                ("moisture/sensor_01/data", "sensor_01"),
                ("moisture/device_abc123/data", "device_abc123"),
                ("moisture/test-device/data", "test-device"),
            ]
            
            for topic, expected_device_id in test_cases:
                device_id = client._extract_device_id_from_topic(topic)
                assert device_id == expected_device_id


class TestMQTTCallbacks:
    """Test MQTT client callbacks."""
    
    def test_on_connect_callback(self, test_config_file):
        """Test MQTT on_connect callback."""
        with patch('moisture_client.mqtt.Client'):
            client = MoistureClient(config_file=test_config_file)
            
            # Test successful connection
            client._on_connect(None, None, None, 0)  # rc=0 means success
            
            # Test failed connection
            client._on_connect(None, None, None, 1)  # rc=1 means failure
    
    def test_on_disconnect_callback(self, test_config_file):
        """Test MQTT on_disconnect callback."""
        with patch('moisture_client.mqtt.Client'):
            client = MoistureClient(config_file=test_config_file)
            
            # Test disconnect callback
            client._on_disconnect(None, None, 0)
    
    def test_on_subscribe_callback(self, test_config_file):
        """Test MQTT on_subscribe callback."""
        with patch('moisture_client.mqtt.Client'):
            client = MoistureClient(config_file=test_config_file)
            
            # Test subscribe callback
            client._on_subscribe(None, None, 1, 0)  # mid=1, granted_qos=0