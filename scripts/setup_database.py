#!/usr/bin/env python3
"""
Database setup script for Moisture Daemon MQTT Client

This script creates the necessary database and tables for storing
moisture sensor data.

Author: Bob Day
Date: October 2025
"""

import mysql.connector
from mysql.connector import Error
import logging
import os
from configparser import ConfigParser


def setup_database():
    """Setup the MySQL database and tables."""
    
    # Load configuration
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.ini')
    config.read(config_path)
    
    # Database configuration
    db_host = os.getenv('DB_HOST', config.get('database', 'host', fallback='localhost'))
    db_port = int(os.getenv('DB_PORT', config.get('database', 'port', fallback='3306')))
    db_name = os.getenv('DB_NAME', config.get('database', 'name', fallback='moisture_db'))
    db_user = os.getenv('DB_USER', config.get('database', 'user', fallback='root'))
    db_password = os.getenv('DB_PASSWORD', config.get('database', 'password', fallback=''))
    
    connection = None
    
    try:
        # Connect to MySQL server (without specifying database)
        print(f"Connecting to MySQL server at {db_host}:{db_port}...")
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password
        )
        
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        print(f"Creating database '{db_name}' if it doesn't exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        # Use the database
        cursor.execute(f"USE {db_name}")
        
        # Create moisture_readings table
        print("Creating moisture_readings table...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS moisture_readings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sensor_id VARCHAR(50) NOT NULL,
            timestamp DATETIME NOT NULL,
            moisture_level FLOAT NOT NULL,
            temperature FLOAT,
            humidity FLOAT,
            battery_level FLOAT,
            raw_data JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sensor_timestamp (sensor_id, timestamp),
            INDEX idx_timestamp (timestamp),
            INDEX idx_sensor_id (sensor_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_query)
        
        # Create sensors table for sensor metadata
        print("Creating sensors table...")
        create_sensors_query = """
        CREATE TABLE IF NOT EXISTS sensors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sensor_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100),
            location VARCHAR(100),
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_sensor_id (sensor_id),
            INDEX idx_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_sensors_query)
        
        # Create alerts table for threshold monitoring
        print("Creating alerts table...")
        create_alerts_query = """
        CREATE TABLE IF NOT EXISTS alerts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sensor_id VARCHAR(50) NOT NULL,
            alert_type ENUM('moisture_low', 'moisture_high', 'battery_low', 'sensor_offline') NOT NULL,
            threshold_value FLOAT,
            actual_value FLOAT,
            message TEXT,
            is_resolved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP NULL,
            INDEX idx_sensor_id (sensor_id),
            INDEX idx_alert_type (alert_type),
            INDEX idx_created_at (created_at),
            INDEX idx_unresolved (is_resolved, created_at),
            FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_alerts_query)
        
        # Create summary statistics view
        print("Creating daily_summary view...")
        create_view_query = """
        CREATE OR REPLACE VIEW daily_summary AS
        SELECT 
            sensor_id,
            DATE(timestamp) as date,
            COUNT(*) as reading_count,
            AVG(moisture_level) as avg_moisture,
            MIN(moisture_level) as min_moisture,
            MAX(moisture_level) as max_moisture,
            AVG(temperature) as avg_temperature,
            AVG(humidity) as avg_humidity,
            AVG(battery_level) as avg_battery_level
        FROM moisture_readings
        GROUP BY sensor_id, DATE(timestamp)
        ORDER BY sensor_id, date DESC
        """
        
        cursor.execute(create_view_query)
        
        # Insert some default sensors if they don't exist
        print("Adding default sensor configurations...")
        default_sensors = [
            ('sensor_001', 'Garden Sensor 1', 'Front Garden', 'Main garden moisture sensor'),
            ('sensor_002', 'Garden Sensor 2', 'Back Garden', 'Back garden moisture sensor'),
            ('sensor_003', 'Indoor Plant 1', 'Living Room', 'Indoor plant monitoring'),
        ]
        
        insert_sensor_query = """
        INSERT IGNORE INTO sensors (sensor_id, name, location, description)
        VALUES (%s, %s, %s, %s)
        """
        
        for sensor in default_sensors:
            cursor.execute(insert_sensor_query, sensor)
        
        connection.commit()
        print(f"Database '{db_name}' setup completed successfully!")
        
        # Display table information
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"\nCreated tables in '{db_name}':")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        
    except Error as e:
        print(f"Error setting up database: {e}")
        if connection and connection.is_connected():
            connection.rollback()
        return False
        
    finally:
        if connection and connection.is_connected():
            connection.close()
            print("MySQL connection closed.")
    
    return True


def verify_database():
    """Verify database setup by checking tables and running a test query."""
    
    # Load configuration
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.ini')
    config.read(config_path)
    
    # Database configuration
    db_host = os.getenv('DB_HOST', config.get('database', 'host', fallback='localhost'))
    db_port = int(os.getenv('DB_PORT', config.get('database', 'port', fallback='3306')))
    db_name = os.getenv('DB_NAME', config.get('database', 'name', fallback='moisture_db'))
    db_user = os.getenv('DB_USER', config.get('database', 'user', fallback='root'))
    db_password = os.getenv('DB_PASSWORD', config.get('database', 'password', fallback=''))
    
    try:
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        cursor = connection.cursor()
        
        # Check table structures
        print(f"\nVerifying database '{db_name}'...")
        
        tables_to_check = ['moisture_readings', 'sensors', 'alerts']
        
        for table in tables_to_check:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            print(f"\nTable '{table}' structure:")
            for column in columns:
                print(f"  {column[0]} - {column[1]} ({column[2]})")
        
        # Check sensors
        cursor.execute("SELECT COUNT(*) FROM sensors")
        sensor_count = cursor.fetchone()[0]
        print(f"\nSensors configured: {sensor_count}")
        
        cursor.execute("SELECT sensor_id, name, location FROM sensors WHERE is_active = TRUE")
        sensors = cursor.fetchall()
        for sensor in sensors:
            print(f"  - {sensor[0]}: {sensor[1]} ({sensor[2]})")
        
        # Check recent readings
        cursor.execute("SELECT COUNT(*) FROM moisture_readings")
        reading_count = cursor.fetchone()[0]
        print(f"\nTotal readings in database: {reading_count}")
        
        if reading_count > 0:
            cursor.execute("""
                SELECT sensor_id, timestamp, moisture_level 
                FROM moisture_readings 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            recent_readings = cursor.fetchall()
            print("\nRecent readings:")
            for reading in recent_readings:
                print(f"  {reading[0]} - {reading[1]} - {reading[2]}%")
        
        cursor.close()
        connection.close()
        
        print(f"\nDatabase verification completed successfully!")
        return True
        
    except Error as e:
        print(f"Error verifying database: {e}")
        return False


if __name__ == "__main__":
    print("Moisture Daemon Database Setup")
    print("=" * 40)
    
    if setup_database():
        print("\n" + "=" * 40)
        verify_database()
    else:
        print("Database setup failed!")
        exit(1)