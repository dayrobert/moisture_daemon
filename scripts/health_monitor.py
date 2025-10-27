#!/usr/bin/env python3
"""
Health Monitor for MoistureSensor MQTT Client

This script monitors the health of the moisture client application
and can be used for alerting and metrics collection.

Author: Bob Day
Date: October 2025
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import mysql.connector
from mysql.connector import Error
from configparser import ConfigParser


class HealthMonitor:
    """Health monitoring for the moisture client application."""
    
    def __init__(self, config_file: str = "config/config.ini"):
        """Initialize the health monitor."""
        self.config_file = config_file
        self.config = ConfigParser()
        self._load_config()
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self):
        """Load configuration from file and environment variables."""
        config_path = os.path.join(os.path.dirname(__file__), '..', self.config_file)
        
        if os.path.exists(config_path):
            self.config.read(config_path)
        
        # Database configuration
        self.db_host = os.getenv('DB_HOST', self.config.get('database', 'host', fallback='localhost'))
        self.db_port = int(os.getenv('DB_PORT', self.config.get('database', 'port', fallback='3306')))
        self.db_name = os.getenv('DB_NAME', self.config.get('database', 'name', fallback='moisture_db'))
        self.db_user = os.getenv('DB_USER', self.config.get('database', 'user', fallback='root'))
        self.db_password = os.getenv('DB_PASSWORD', self.config.get('database', 'password', fallback=''))
        
        # Alert thresholds
        self.moisture_low = float(os.getenv('MOISTURE_LOW_THRESHOLD', 
                                           self.config.get('alerts', 'moisture_low_threshold', fallback='20.0')))
        self.moisture_high = float(os.getenv('MOISTURE_HIGH_THRESHOLD', 
                                            self.config.get('alerts', 'moisture_high_threshold', fallback='80.0')))
        self.battery_low = float(os.getenv('BATTERY_LOW_THRESHOLD', 
                                          self.config.get('alerts', 'battery_low_threshold', fallback='10.0')))
        self.sensor_offline = int(os.getenv('SENSOR_OFFLINE_THRESHOLD', 
                                           self.config.get('alerts', 'sensor_offline_threshold', fallback='3600')))
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _connect_database(self) -> Optional[mysql.connector.MySQLConnection]:
        """Connect to MySQL database."""
        try:
            connection = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            return connection
        except Error as e:
            self.logger.error(f"Error connecting to database: {e}")
            return None
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and recent activity."""
        health_status = {
            'database_connected': False,
            'recent_readings': 0,
            'last_reading_time': None,
            'total_readings': 0,
            'active_sensors': 0
        }
        
        connection = self._connect_database()
        if not connection:
            return health_status
        
        try:
            cursor = connection.cursor()
            
            # Check if connected
            health_status['database_connected'] = True
            
            # Get total readings count
            cursor.execute("SELECT COUNT(*) FROM moisture_readings")
            health_status['total_readings'] = cursor.fetchone()[0]
            
            # Get recent readings (last hour)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM moisture_readings 
                WHERE timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR)
            """)
            health_status['recent_readings'] = cursor.fetchone()[0]
            
            # Get last reading time
            cursor.execute("""
                SELECT MAX(timestamp) 
                FROM moisture_readings
            """)
            last_time = cursor.fetchone()[0]
            if last_time:
                health_status['last_reading_time'] = last_time.isoformat()
            
            # Get active sensors count
            cursor.execute("""
                SELECT COUNT(DISTINCT sensor_id) 
                FROM moisture_readings 
                WHERE timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            health_status['active_sensors'] = cursor.fetchone()[0]
            
            cursor.close()
            
        except Error as e:
            self.logger.error(f"Database health check error: {e}")
        finally:
            if connection.is_connected():
                connection.close()
        
        return health_status
    
    def check_sensor_health(self) -> List[Dict[str, Any]]:
        """Check individual sensor health and generate alerts."""
        sensor_status = []
        
        connection = self._connect_database()
        if not connection:
            return sensor_status
        
        try:
            cursor = connection.cursor()
            
            # Get all sensors and their latest readings
            cursor.execute("""
                SELECT 
                    s.sensor_id,
                    s.name,
                    s.location,
                    s.is_active,
                    mr.timestamp as last_reading,
                    mr.moisture_level,
                    mr.temperature,
                    mr.battery_level,
                    TIMESTAMPDIFF(SECOND, mr.timestamp, NOW()) as seconds_since_last
                FROM sensors s
                LEFT JOIN (
                    SELECT sensor_id, timestamp, moisture_level, temperature, battery_level,
                           ROW_NUMBER() OVER (PARTITION BY sensor_id ORDER BY timestamp DESC) as rn
                    FROM moisture_readings
                ) mr ON s.sensor_id = mr.sensor_id AND mr.rn = 1
                WHERE s.is_active = TRUE
            """)
            
            sensors = cursor.fetchall()
            
            for sensor in sensors:
                sensor_id, name, location, is_active, last_reading, moisture, temp, battery, seconds_since = sensor
                
                status = {
                    'sensor_id': sensor_id,
                    'name': name,
                    'location': location,
                    'is_active': bool(is_active),
                    'last_reading': last_reading.isoformat() if last_reading else None,
                    'moisture_level': float(moisture) if moisture is not None else None,
                    'temperature': float(temp) if temp is not None else None,
                    'battery_level': float(battery) if battery is not None else None,
                    'seconds_since_last': int(seconds_since) if seconds_since is not None else None,
                    'alerts': []
                }
                
                # Check for alerts
                if seconds_since is None or seconds_since > self.sensor_offline:
                    status['alerts'].append({
                        'type': 'sensor_offline',
                        'message': f'Sensor {sensor_id} has been offline for {seconds_since or "unknown"} seconds',
                        'severity': 'high'
                    })
                
                if moisture is not None:
                    if moisture < self.moisture_low:
                        status['alerts'].append({
                            'type': 'moisture_low',
                            'message': f'Low moisture level: {moisture}% (threshold: {self.moisture_low}%)',
                            'severity': 'medium'
                        })
                    elif moisture > self.moisture_high:
                        status['alerts'].append({
                            'type': 'moisture_high',
                            'message': f'High moisture level: {moisture}% (threshold: {self.moisture_high}%)',
                            'severity': 'medium'
                        })
                
                if battery is not None and battery < self.battery_low:
                    status['alerts'].append({
                        'type': 'battery_low',
                        'message': f'Low battery level: {battery}% (threshold: {self.battery_low}%)',
                        'severity': 'high'
                    })
                
                sensor_status.append(status)
            
            cursor.close()
            
        except Error as e:
            self.logger.error(f"Sensor health check error: {e}")
        finally:
            if connection.is_connected():
                connection.close()
        
        return sensor_status
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health summary report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'database': self.check_database_health(),
            'sensors': self.check_sensor_health(),
            'summary': {
                'total_alerts': 0,
                'high_severity_alerts': 0,
                'medium_severity_alerts': 0,
                'offline_sensors': 0,
                'healthy_sensors': 0
            }
        }
        
        # Calculate summary statistics
        for sensor in report['sensors']:
            if sensor['alerts']:
                report['summary']['total_alerts'] += len(sensor['alerts'])
                
                for alert in sensor['alerts']:
                    if alert['severity'] == 'high':
                        report['summary']['high_severity_alerts'] += 1
                    elif alert['severity'] == 'medium':
                        report['summary']['medium_severity_alerts'] += 1
                
                # Check if sensor is offline
                offline_alert = any(alert['type'] == 'sensor_offline' for alert in sensor['alerts'])
                if offline_alert:
                    report['summary']['offline_sensors'] += 1
                else:
                    report['summary']['healthy_sensors'] += 1
            else:
                report['summary']['healthy_sensors'] += 1
        
        return report
    
    def save_metrics(self, report: Dict[str, Any], metrics_file: str = "logs/metrics.json"):
        """Save metrics to a JSON file for monitoring systems."""
        try:
            metrics_path = os.path.join(os.path.dirname(__file__), '..', metrics_file)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
            
            with open(metrics_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Metrics saved to {metrics_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")
    
    def print_report(self, report: Dict[str, Any]):
        """Print a human-readable health report."""
        print("=" * 60)
        print("MoistureSensor Health Report")
        print("=" * 60)
        print(f"Generated: {report['timestamp']}")
        print()
        
        # Database status
        db = report['database']
        print("Database Status:")
        print(f"  Connected: {'✓' if db['database_connected'] else '✗'}")
        print(f"  Total readings: {db['total_readings']:,}")
        print(f"  Recent readings (1h): {db['recent_readings']}")
        print(f"  Active sensors: {db['active_sensors']}")
        print(f"  Last reading: {db['last_reading_time'] or 'None'}")
        print()
        
        # Summary
        summary = report['summary']
        print("Alert Summary:")
        print(f"  Total alerts: {summary['total_alerts']}")
        print(f"  High severity: {summary['high_severity_alerts']}")
        print(f"  Medium severity: {summary['medium_severity_alerts']}")
        print(f"  Offline sensors: {summary['offline_sensors']}")
        print(f"  Healthy sensors: {summary['healthy_sensors']}")
        print()
        
        # Sensor details
        print("Sensor Status:")
        for sensor in report['sensors']:
            status_icon = "✗" if sensor['alerts'] else "✓"
            print(f"  {status_icon} {sensor['sensor_id']} ({sensor['name'] or 'Unknown'})")
            
            if sensor['last_reading']:
                print(f"    Last reading: {sensor['last_reading']}")
                if sensor['moisture_level'] is not None:
                    print(f"    Moisture: {sensor['moisture_level']:.1f}%")
                if sensor['temperature'] is not None:
                    print(f"    Temperature: {sensor['temperature']:.1f}°C")
                if sensor['battery_level'] is not None:
                    print(f"    Battery: {sensor['battery_level']:.1f}%")
            else:
                print("    No readings available")
            
            for alert in sensor['alerts']:
                print(f"    ⚠️  {alert['message']} ({alert['severity']})")
            print()


def main():
    """Main entry point for health monitoring."""
    monitor = HealthMonitor()
    
    # Generate health report
    report = monitor.generate_summary_report()
    
    # Print report to console
    monitor.print_report(report)
    
    # Save metrics for monitoring systems
    monitor.save_metrics(report)
    
    # Exit with error code if there are high severity alerts
    if report['summary']['high_severity_alerts'] > 0:
        print("High severity alerts detected!")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()