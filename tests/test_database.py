"""
Unit tests for MoistureClient database functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from moisture_client import MoistureClient


class TestDatabaseConnection:
    """Test database connection functionality."""
    
    @patch('moisture_client.mysql.connector.connect')
    def test_database_connection_success(self, mock_connect, test_config_file):
        """Test successful database connection."""
        mock_connection = Mock()
        mock_connection.is_connected.return_value = True
        mock_connect.return_value = mock_connection
        
        client = MoistureClient(config_file=test_config_file)
        result = client._connect_database()
        
        assert result is True
        assert client.db_connection == mock_connection
        mock_connect.assert_called_once()
    
    @patch('moisture_client.mysql.connector.connect')
    def test_database_connection_failure(self, mock_connect, test_config_file):
        """Test database connection failure."""
        mock_connect.side_effect = Error("Connection failed")
        
        client = MoistureClient(config_file=test_config_file)
        result = client._connect_database()
        
        assert result is False
        assert client.db_connection is None
    
    @patch('moisture_client.mysql.connector.connect')
    def test_database_connection_with_auth_plugin(self, mock_connect, test_config_file):
        """Test database connection with authentication plugin."""
        mock_connection = Mock()
        mock_connection.is_connected.return_value = True
        mock_connect.return_value = mock_connection
        
        client = MoistureClient(config_file=test_config_file)
        client._connect_database()
        
        # Verify that the connection was called with auth plugin parameters
        call_args = mock_connect.call_args
        assert 'auth_plugin' in call_args.kwargs
        assert call_args.kwargs['auth_plugin'] == 'mysql_native_password'
        assert 'use_pure' in call_args.kwargs
        assert call_args.kwargs['use_pure'] is True


class TestDatabaseOperations:
    """Test database CRUD operations."""
    
    def test_insert_sensor_data_success(self, test_config_file, sample_mqtt_message):
        """Test successful sensor data insertion."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Mock database connection and cursor
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.is_connected.return_value = True
            client.db_connection = mock_connection
            
            # Test data insertion
            result = client._insert_sensor_data(sample_mqtt_message)
            
            assert result is True
            mock_cursor.execute.assert_called_once()
            mock_connection.commit.assert_called_once()
            mock_cursor.close.assert_called_once()
    
    def test_insert_sensor_data_database_error(self, test_config_file, sample_mqtt_message):
        """Test sensor data insertion with database error."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Mock database connection with error
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_cursor.execute.side_effect = Error("Database error")
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.is_connected.return_value = True
            client.db_connection = mock_connection
            
            # Test data insertion
            result = client._insert_sensor_data(sample_mqtt_message)
            
            assert result is False
    
    def test_insert_sensor_data_no_connection(self, test_config_file, sample_mqtt_message):
        """Test sensor data insertion without database connection."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            client.db_connection = None
            
            # Test data insertion
            result = client._insert_sensor_data(sample_mqtt_message)
            
            assert result is False
    
    def test_create_database_tables(self, test_config_file):
        """Test database table creation."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Mock database connection and cursor
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.is_connected.return_value = True
            client.db_connection = mock_connection
            
            # Test table creation
            client._create_tables()
            
            # Should execute CREATE TABLE statements
            assert mock_cursor.execute.called
            mock_connection.commit.assert_called_once()
            mock_cursor.close.assert_called_once()


class TestDatabaseDataValidation:
    """Test data validation before database insertion."""
    
    def test_validate_sensor_data_valid(self, test_config_file, sample_mqtt_message):
        """Test validation of valid sensor data."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            result = client._validate_sensor_data(sample_mqtt_message)
            assert result is True
    
    def test_validate_sensor_data_missing_required_fields(self, test_config_file):
        """Test validation of sensor data with missing required fields."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Test data missing required fields
            invalid_data = {"device_id": "sensor_01"}  # Missing timestamp, moisture, etc.
            
            result = client._validate_sensor_data(invalid_data)
            assert result is False
    
    def test_validate_sensor_data_invalid_types(self, test_config_file):
        """Test validation of sensor data with invalid data types."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Test data with invalid types
            invalid_data = {
                "device_id": "sensor_01",
                "timestamp": "2025-10-28T10:30:00Z",
                "moisture": "not_a_number",  # Should be float
                "temperature": 22.5,
                "humidity": 65.3,
                "battery": 87.5
            }
            
            result = client._validate_sensor_data(invalid_data)
            assert result is False
    
    def test_validate_sensor_data_out_of_range_values(self, test_config_file):
        """Test validation of sensor data with out-of-range values."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Test data with out-of-range values
            invalid_data = {
                "device_id": "sensor_01",
                "timestamp": "2025-10-28T10:30:00Z",
                "moisture": -10.0,  # Negative moisture (invalid)
                "temperature": 22.5,
                "humidity": 150.0,  # Humidity > 100% (invalid)
                "battery": 87.5
            }
            
            result = client._validate_sensor_data(invalid_data)
            assert result is False


class TestDatabaseQueries:
    """Test database query operations."""
    
    def test_get_latest_sensor_reading(self, test_config_file):
        """Test retrieving latest sensor reading."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Mock database connection and cursor
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = (
                1, "sensor_01", datetime.now(), 45.2, 22.5, 65.3, 87.5, -45
            )
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.is_connected.return_value = True
            client.db_connection = mock_connection
            
            # Test query
            result = client._get_latest_reading("sensor_01")
            
            assert result is not None
            mock_cursor.execute.assert_called_once()
            mock_cursor.fetchone.assert_called_once()
    
    def test_get_sensor_statistics(self, test_config_file):
        """Test retrieving sensor statistics."""
        with patch('moisture_client.mysql.connector.connect'):
            client = MoistureClient(config_file=test_config_file)
            
            # Mock database connection and cursor
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                ("sensor_01", 45.2, 22.5, 10),
                ("sensor_02", 55.1, 24.1, 8)
            ]
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.is_connected.return_value = True
            client.db_connection = mock_connection
            
            # Test query
            result = client._get_sensor_statistics()
            
            assert result is not None
            assert len(result) == 2
            mock_cursor.execute.assert_called_once()
            mock_cursor.fetchall.assert_called_once()