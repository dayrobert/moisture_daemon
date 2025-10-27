#!/usr/bin/env python3
"""
Moisture Daemon MQTT Client

This daemon application listens to MQTT messages from moisture sensors and logs
the data to a MySQL database. Designed to run as a cron job on Ubuntu server.

Author: Bob Day
Date: October 2025
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt
import mysql.connector
from mysql.connector import Error
from configparser import ConfigParser


class MoistureClient:
    """Main class for handling MQTT messages and database operations."""
    
    def __init__(self, config_file: str = "config/config.ini"):
        """Initialize the moisture client with configuration."""
        self.config_file = config_file
        self.config = ConfigParser()
        self.mqtt_client = None
        self.db_connection = None
        self.running = False
        
        # Load configuration
        self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("MoistureClient initialized")
    
    def _load_config(self):
        """Load configuration from file and environment variables."""
        config_path = os.path.join(os.path.dirname(__file__), self.config_file)
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        self.config.read(config_path)
        
        # Override with environment variables if present
        self.mqtt_broker = os.getenv('MQTT_BROKER', self.config.get('mqtt', 'broker', fallback='localhost'))
        self.mqtt_port = int(os.getenv('MQTT_PORT', self.config.get('mqtt', 'port', fallback='1883')))
        self.mqtt_username = os.getenv('MQTT_USERNAME', self.config.get('mqtt', 'username', fallback=''))
        self.mqtt_password = os.getenv('MQTT_PASSWORD', self.config.get('mqtt', 'password', fallback=''))
        self.mqtt_topic = os.getenv('MQTT_TOPIC', self.config.get('mqtt', 'topic', fallback='moisture/+/data'))
        
        # Database configuration
        self.db_host = os.getenv('DB_HOST', self.config.get('database', 'host', fallback='localhost'))
        self.db_port = int(os.getenv('DB_PORT', self.config.get('database', 'port', fallback='3306')))
        self.db_name = os.getenv('DB_NAME', self.config.get('database', 'name', fallback='moisture_db'))
        self.db_user = os.getenv('DB_USER', self.config.get('database', 'user', fallback='root'))
        self.db_password = os.getenv('DB_PASSWORD', self.config.get('database', 'password', fallback=''))
        
        # Client configuration
        self.client_id = os.getenv('CLIENT_ID', self.config.get('client', 'id', fallback='moisture_client'))
        self.reconnect_delay = int(os.getenv('RECONNECT_DELAY', self.config.get('client', 'reconnect_delay', fallback='5')))
        self.max_runtime = int(os.getenv('MAX_RUNTIME', self.config.get('client', 'max_runtime', fallback='300')))  # 5 minutes default
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = os.getenv('LOG_LEVEL', self.config.get('logging', 'level', fallback='INFO'))
        log_file = os.getenv('LOG_FILE', self.config.get('logging', 'file', fallback='logs/moisture_client.log'))
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _connect_database(self) -> bool:
        """Connect to MySQL database."""
        try:
            self.db_connection = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                autocommit=True
            )
            
            if self.db_connection.is_connected():
                self.logger.info(f"Connected to MySQL database: {self.db_name}")
                return True
        except Error as e:
            self.logger.error(f"Error connecting to MySQL database: {e}")
            return False
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
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
            INDEX idx_timestamp (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(create_table_query)
            cursor.close()
            self.logger.info("Database tables verified/created successfully")
        except Error as e:
            self.logger.error(f"Error creating database tables: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker: {self.mqtt_broker}:{self.mqtt_port}")
            client.subscribe(self.mqtt_topic)
            self.logger.info(f"Subscribed to topic: {self.mqtt_topic}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection."""
        if rc != 0:
            self.logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")
        else:
            self.logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """Callback for received MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.debug(f"Received message on topic '{topic}': {payload}")
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in message: {e}")
                return
            
            # Extract sensor ID from topic (assuming format: moisture/{sensor_id}/data)
            topic_parts = topic.split('/')
            if len(topic_parts) >= 2:
                sensor_id = topic_parts[1]
            else:
                sensor_id = data.get('sensor_id', 'unknown')
            
            # Store data in database
            self._store_sensor_data(sensor_id, data, payload)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def _store_sensor_data(self, sensor_id: str, data: Dict[str, Any], raw_payload: str):
        """Store sensor data in MySQL database."""
        try:
            # Extract common sensor data fields
            moisture_level = data.get('moisture', data.get('moisture_level', 0.0))
            temperature = data.get('temperature', data.get('temp', None))
            humidity = data.get('humidity', None)
            battery_level = data.get('battery', data.get('battery_level', None))
            
            # Use provided timestamp or current time
            timestamp_str = data.get('timestamp', data.get('time'))
            if timestamp_str:
                try:
                    # Try parsing different timestamp formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                        try:
                            timestamp = datetime.strptime(timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format matches, use current time
                        timestamp = datetime.now()
                except Exception:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Insert data into database
            insert_query = """
            INSERT INTO moisture_readings 
            (sensor_id, timestamp, moisture_level, temperature, humidity, battery_level, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor = self.db_connection.cursor()
            cursor.execute(insert_query, (
                sensor_id,
                timestamp,
                float(moisture_level),
                float(temperature) if temperature is not None else None,
                float(humidity) if humidity is not None else None,
                float(battery_level) if battery_level is not None else None,
                raw_payload
            ))
            cursor.close()
            
            self.logger.info(f"Stored data for sensor {sensor_id}: moisture={moisture_level}")
            
        except Error as e:
            self.logger.error(f"Database error storing sensor data: {e}")
        except Exception as e:
            self.logger.error(f"Error storing sensor data: {e}")
    
    def _connect_mqtt(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self.mqtt_client = mqtt.Client(client_id=self.client_id)
            
            # Set credentials if provided
            if self.mqtt_username and self.mqtt_password:
                self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # Set callbacks
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_disconnect = self._on_disconnect
            self.mqtt_client.on_message = self._on_message
            
            # Connect to broker
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def run(self):
        """Main run loop for the moisture client."""
        self.logger.info("Starting MoistureClient...")
        
        # Connect to database
        if not self._connect_database():
            self.logger.error("Failed to connect to database. Exiting.")
            return False
        
        # Create tables if needed
        self._create_tables()
        
        # Connect to MQTT broker
        if not self._connect_mqtt():
            self.logger.error("Failed to connect to MQTT broker. Exiting.")
            return False
        
        # Start MQTT loop
        self.mqtt_client.loop_start()
        self.running = True
        
        start_time = time.time()
        
        try:
            # Run for specified duration or until interrupted
            while self.running:
                # Check if max runtime exceeded (useful for cron jobs)
                if time.time() - start_time > self.max_runtime:
                    self.logger.info(f"Max runtime ({self.max_runtime}s) reached. Shutting down.")
                    break
                
                # Check database connection
                if not self.db_connection.is_connected():
                    self.logger.warning("Database connection lost. Attempting to reconnect...")
                    if not self._connect_database():
                        self.logger.error("Failed to reconnect to database")
                        break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self._cleanup()
        
        self.logger.info("MoistureClient stopped")
        return True
    
    def _cleanup(self):
        """Clean up resources."""
        self.running = False
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.logger.info("MQTT client disconnected")
        
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            self.logger.info("Database connection closed")


def main():
    """Main entry point."""
    try:
        client = MoistureClient()
        success = client.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()