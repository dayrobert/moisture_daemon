"""
Main unit tests for MoistureClient class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys

# Import the module under test
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from moisture_client import MoistureClient


class TestMoistureClientInitialization:
    """Test MoistureClient initialization."""
    
    def test_init_with_valid_config(self, test_config_file):
        """Test initialization with valid configuration file."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            
            assert client.config_file == test_config_file
            assert client.mqtt_client is not None
            assert client.running is False
            assert hasattr(client, 'logger')
    
    def test_init_with_missing_config(self):
        """Test initialization with missing configuration file."""
        with pytest.raises(Exception):  # Should raise some kind of configuration error
            MoistureClient(config_file="nonexistent.ini")
    
    def test_init_default_config_path(self):
        """Test initialization with default configuration path."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'), \
             patch.object(MoistureClient, '_load_config'):
            
            client = MoistureClient()
            assert client.config_file == "config/config.ini"


class TestMoistureClientMainLoop:
    """Test main application loop functionality."""
    
    @patch('moisture_client.mqtt.Client')
    @patch('moisture_client.mysql.connector.connect')
    def test_start_success(self, mock_db_connect, mock_mqtt_class, test_config_file):
        """Test successful application start."""
        # Mock successful connections
        mock_mqtt_client = Mock()
        mock_mqtt_client.connect.return_value = 0
        mock_mqtt_class.return_value = mock_mqtt_client
        
        mock_db_connection = Mock()
        mock_db_connection.is_connected.return_value = True
        mock_db_connect.return_value = mock_db_connection
        
        client = MoistureClient(config_file=test_config_file)
        
        with patch.object(client, '_connect_mqtt', return_value=True), \
             patch.object(client, '_connect_database', return_value=True):
            
            result = client.start()
            assert result is True
            assert client.running is True
    
    @patch('moisture_client.mqtt.Client')
    @patch('moisture_client.mysql.connector.connect')
    def test_start_mqtt_failure(self, mock_db_connect, mock_mqtt_class, test_config_file):
        """Test application start with MQTT connection failure."""
        mock_mqtt_client = Mock()
        mock_mqtt_client.connect.return_value = 1  # Connection failed
        mock_mqtt_class.return_value = mock_mqtt_client
        
        client = MoistureClient(config_file=test_config_file)
        
        with patch.object(client, '_connect_mqtt', return_value=False), \
             patch.object(client, '_connect_database', return_value=True):
            
            result = client.start()
            assert result is False
            assert client.running is False
    
    @patch('moisture_client.mqtt.Client')
    @patch('moisture_client.mysql.connector.connect')
    def test_start_database_failure(self, mock_db_connect, mock_mqtt_class, test_config_file):
        """Test application start with database connection failure."""
        mock_mqtt_client = Mock()
        mock_mqtt_client.connect.return_value = 0
        mock_mqtt_class.return_value = mock_mqtt_client
        
        client = MoistureClient(config_file=test_config_file)
        
        with patch.object(client, '_connect_mqtt', return_value=True), \
             patch.object(client, '_connect_database', return_value=False):
            
            result = client.start()
            assert result is False
            assert client.running is False
    
    def test_stop(self, test_config_file):
        """Test application stop functionality."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            client.running = True
            
            # Mock connections
            client.mqtt_client = Mock()
            client.db_connection = Mock()
            client.db_connection.is_connected.return_value = True
            
            client.stop()
            
            assert client.running is False
            client.mqtt_client.loop_stop.assert_called_once()
            client.mqtt_client.disconnect.assert_called_once()
            client.db_connection.close.assert_called_once()


class TestMoistureClientSignalHandling:
    """Test signal handling for graceful shutdown."""
    
    def test_signal_handler(self, test_config_file):
        """Test signal handler for graceful shutdown."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            client.running = True
            
            with patch.object(client, 'stop') as mock_stop:
                client._signal_handler(2, None)  # SIGINT
                mock_stop.assert_called_once()


class TestMoistureClientRuntime:
    """Test runtime behavior and error handling."""
    
    def test_run_with_max_runtime(self, test_config_file):
        """Test running with maximum runtime limit."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            client.max_runtime = 1  # 1 second for testing
            
            with patch.object(client, 'start', return_value=True), \
                 patch('time.sleep') as mock_sleep, \
                 patch('time.time', side_effect=[0, 0.5, 1.1]):  # Simulate time passing
                
                client.run()
                
                # Should have stopped due to max runtime
                assert client.running is False
    
    def test_run_with_exception_handling(self, test_config_file):
        """Test runtime exception handling."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            
            with patch.object(client, 'start', side_effect=Exception("Test exception")):
                # Should handle exception gracefully
                try:
                    client.run()
                except Exception:
                    pytest.fail("Runtime exception should be handled gracefully")
    
    def test_reconnection_logic(self, test_config_file):
        """Test automatic reconnection logic."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            client.max_retries = 2
            client.reconnect_delay = 0.1  # Short delay for testing
            
            with patch.object(client, '_connect_mqtt', side_effect=[False, False, True]), \
                 patch.object(client, '_connect_database', return_value=True), \
                 patch('time.sleep') as mock_sleep:
                
                result = client._attempt_reconnection()
                
                # Should have attempted reconnection
                assert mock_sleep.called
                assert result is True  # Eventually succeeded


class TestMoistureClientIntegration:
    """Integration tests for complete workflow."""
    
    def test_complete_message_processing_workflow(self, test_config_file, sample_mqtt_message):
        """Test complete message processing from MQTT to database."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            
            # Mock successful database insertion
            with patch.object(client, '_insert_sensor_data', return_value=True) as mock_insert, \
                 patch.object(client, '_validate_sensor_data', return_value=True):
                
                # Create mock MQTT message
                mock_message = Mock()
                mock_message.topic = "moisture/sensor_01/data"
                mock_message.payload.decode.return_value = json.dumps(sample_mqtt_message)
                
                # Process the message
                client._on_message(None, None, mock_message)
                
                # Verify the workflow
                mock_insert.assert_called_once()
    
    def test_error_recovery_workflow(self, test_config_file):
        """Test error recovery and retry logic."""
        with patch('moisture_client.mqtt.Client'), \
             patch('moisture_client.mysql.connector.connect'):
            
            client = MoistureClient(config_file=test_config_file)
            client.max_retries = 2
            
            # Test database reconnection on error
            with patch.object(client, '_connect_database', side_effect=[False, True]), \
                 patch('time.sleep'):
                
                result = client._ensure_database_connection()
                assert result is True