-- Initialize Moisture Database Schema
-- This script runs automatically when the MySQL container starts

CREATE DATABASE IF NOT EXISTS moisture_db;
USE moisture_db;

-- Moisture readings table
CREATE TABLE IF NOT EXISTS moisture_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    moisture_level FLOAT NOT NULL,
    temperature FLOAT,
    humidity FLOAT,
    battery_level FLOAT,
    signal_strength INT,
    location VARCHAR(100),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sensor_timestamp (sensor_id, timestamp),
    INDEX idx_timestamp (timestamp)
);

-- Sensor status table
CREATE TABLE IF NOT EXISTS sensor_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL UNIQUE,
    last_seen DATETIME,
    status ENUM('active', 'inactive', 'error') DEFAULT 'active',
    location VARCHAR(100),
    battery_level FLOAT,
    firmware_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sensor_id (sensor_id),
    INDEX idx_status (status)
);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(50),
    alert_type ENUM('low_moisture', 'low_battery', 'sensor_offline', 'high_temperature') NOT NULL,
    message TEXT,
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP NULL,
    INDEX idx_sensor_alert (sensor_id, alert_type),
    INDEX idx_created (created_at),
    INDEX idx_acknowledged (acknowledged)
);

-- System health table
CREATE TABLE IF NOT EXISTS system_health (
    id INT AUTO_INCREMENT PRIMARY KEY,
    component VARCHAR(50) NOT NULL,
    status ENUM('healthy', 'warning', 'error') DEFAULT 'healthy',
    message TEXT,
    metrics JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_component (component),
    INDEX idx_timestamp (timestamp)
);

-- Insert some sample data (optional)
INSERT IGNORE INTO sensor_status (sensor_id, location, status) VALUES 
('sensor_001', 'Garden Zone 1', 'active'),
('sensor_002', 'Garden Zone 2', 'active'),
('sensor_003', 'Greenhouse', 'active');

-- Create views for reporting
CREATE OR REPLACE VIEW v_latest_readings AS
SELECT 
    mr.sensor_id,
    ss.location,
    mr.moisture_level,
    mr.temperature,
    mr.humidity,
    mr.battery_level,
    mr.timestamp,
    ss.status
FROM moisture_readings mr
INNER JOIN (
    SELECT sensor_id, MAX(timestamp) as max_timestamp
    FROM moisture_readings
    GROUP BY sensor_id
) latest ON mr.sensor_id = latest.sensor_id AND mr.timestamp = latest.max_timestamp
LEFT JOIN sensor_status ss ON mr.sensor_id = ss.sensor_id;

CREATE OR REPLACE VIEW v_daily_summary AS
SELECT 
    sensor_id,
    DATE(timestamp) as reading_date,
    COUNT(*) as reading_count,
    AVG(moisture_level) as avg_moisture,
    MIN(moisture_level) as min_moisture,
    MAX(moisture_level) as max_moisture,
    AVG(temperature) as avg_temperature,
    AVG(humidity) as avg_humidity,
    MIN(battery_level) as min_battery
FROM moisture_readings
GROUP BY sensor_id, DATE(timestamp);

-- Grant permissions to moisture_user
GRANT SELECT, INSERT, UPDATE, DELETE ON moisture_db.* TO 'moisture_user'@'%';
FLUSH PRIVILEGES;