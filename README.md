# Moisture Daemon

A Python daemon application that listens to MQTT messages from moisture sensors and logs the data to a MySQL database. Designed to run as a cron job on Ubuntu servers.

## Features

- **MQTT Client**: Connects to MQTT broker and subscribes to moisture sensor topics
- **MySQL Database**: Stores sensor readings with timestamps and metadata
- **Health Monitoring**: Monitors sensor health and generates alerts
- **Cron Job Ready**: Designed to run as scheduled tasks with proper logging
- **Configurable**: Supports configuration files and environment variables
- **Systemd Service**: Can run as a continuous service or scheduled job
- **Alert System**: Monitors thresholds and sensor connectivity

## Architecture

```
moisture_sensor (ESP32) → MQTT Broker → moisture_daemon → MySQL Database
                                             ↓
                                     Health Monitor → Alerts/Metrics
```

## Directory Structure

```
moisture_daemon/
├── moisture_client.py          # Main application
├── requirements.txt            # Python dependencies
├── config/
│   ├── config.ini             # Configuration file
│   └── .env.example           # Environment variables template
├── scripts/
│   ├── install.sh             # Ubuntu installation script
│   ├── setup_database.py      # Database setup script
│   └── health_monitor.py      # Health monitoring script
└── logs/                      # Log files directory
```

## Quick Start

### 1. Installation on Ubuntu Server

```bash
# Clone or copy the moisture_daemon directory to your server
cd /path/to/moisture_daemon

# Run the installation script (requires sudo)
sudo ./scripts/install.sh
```

This will:
- Install Python dependencies
- Create application user and directories
- Set up systemd service
- Configure cron job
- Set up log rotation

### 2. Configuration

Edit the configuration file:
```bash
sudo nano /opt/moisture-daemon/config/.env
```

Update with your settings:
```bash
# MQTT Configuration
MQTT_BROKER=your-mqtt-broker.local
MQTT_PORT=1883
MQTT_USERNAME=your-username
MQTT_PASSWORD=your-password
MQTT_TOPIC=moisture/+/data

# Database Configuration
DB_HOST=localhost
DB_NAME=moisture_db
DB_USER=moisture_user
DB_PASSWORD=your-secure-password
```

### 3. Database Setup

```bash
# Set up MySQL database and tables
cd /opt/moisture-daemon
sudo -u moisture ./venv/bin/python scripts/setup_database.py
```

### 4. Test and Start

```bash
# Test the application
sudo -u moisture /opt/moisture-daemon/venv/bin/python /opt/moisture-daemon/moisture_client.py

# Start as systemd service
sudo systemctl start moisture-daemon
sudo systemctl status moisture-daemon

# View logs
sudo journalctl -u moisture-daemon -f
```

## Configuration Options

### MQTT Settings
- `MQTT_BROKER`: MQTT broker hostname/IP
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `MQTT_USERNAME`: MQTT username (optional)
- `MQTT_PASSWORD`: MQTT password (optional)
- `MQTT_TOPIC`: MQTT topic pattern (default: `moisture/+/data`)

### Database Settings
- `DB_HOST`: MySQL host (default: localhost)
- `DB_PORT`: MySQL port (default: 3306)
- `DB_NAME`: Database name (default: moisture_db)
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password

### Application Settings
- `CLIENT_ID`: MQTT client ID
- `MAX_RUNTIME`: Maximum runtime in seconds (for cron jobs)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE`: Log file path

## Database Schema

### moisture_readings
Stores sensor data:
- `id`: Auto-increment primary key
- `sensor_id`: Sensor identifier
- `timestamp`: Reading timestamp
- `moisture_level`: Moisture percentage
- `temperature`: Temperature (optional)
- `humidity`: Humidity (optional)
- `battery_level`: Battery percentage (optional)
- `raw_data`: Original JSON payload
- `created_at`: Record creation timestamp

### sensors
Sensor metadata:
- `sensor_id`: Unique sensor identifier
- `name`: Human-readable name
- `location`: Physical location
- `description`: Description
- `is_active`: Active status

### alerts
Alert records:
- `sensor_id`: Related sensor
- `alert_type`: Type of alert
- `threshold_value`: Threshold that triggered alert
- `actual_value`: Actual sensor value
- `message`: Alert message
- `is_resolved`: Resolution status

## Running as Cron Job

The application is designed to run as a cron job with a maximum runtime (default: 5 minutes). This prevents long-running processes and ensures regular restarts.

Default cron job (runs every 5 minutes):
```bash
*/5 * * * * moisture cd /opt/moisture-daemon && /opt/moisture-daemon/venv/bin/python /opt/moisture-daemon/moisture_client.py >> /var/log/moisture-daemon/cron.log 2>&1
```

### Custom Cron Schedule

Edit the cron job:
```bash
sudo crontab -e -u moisture
```

Examples:
```bash
# Every minute
* * * * * /opt/moisture-daemon/venv/bin/python /opt/moisture-daemon/moisture_client.py

# Every 10 minutes
*/10 * * * * /opt/moisture-daemon/venv/bin/python /opt/moisture-daemon/moisture_client.py

# Hourly
0 * * * * /opt/moisture-daemon/venv/bin/python /opt/moisture-daemon/moisture_client.py
```

## Health Monitoring

Run health checks:
```bash
# Manual health check
sudo -u moisture /opt/moisture-daemon/venv/bin/python /opt/moisture-daemon/scripts/health_monitor.py

# Add to cron for regular monitoring
0 */6 * * * moisture /opt/moisture-daemon/venv/bin/python /opt/moisture-daemon/scripts/health_monitor.py
```

Health monitoring includes:
- Database connectivity
- Recent sensor activity
- Battery levels
- Moisture thresholds
- Sensor offline detection

## Expected MQTT Message Format

The application expects JSON messages on the configured topic pattern:

```json
{
  "sensor_id": "sensor_001",
  "timestamp": "2025-10-27T10:30:00",
  "moisture": 45.2,
  "temperature": 23.5,
  "humidity": 65.0,
  "battery": 85.5
}
```

Alternative field names are supported:
- `moisture_level` instead of `moisture`
- `temp` instead of `temperature`
- `battery_level` instead of `battery`
- `time` instead of `timestamp`

Your ESP32 moisture_sensor should publish JSON messages like this.

## Logging

Logs are stored in `/var/log/moisture-daemon/` with automatic rotation:
- `moisture_client.log`: Main application logs
- `cron.log`: Cron job execution logs
- `metrics.json`: Health monitoring metrics

Log levels: DEBUG, INFO, WARNING, ERROR

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check MySQL service
   sudo systemctl status mysql
   
   # Test database connection
   mysql -h localhost -u moisture_user -p moisture_db
   ```

2. **MQTT Connection Failed**
   ```bash
   # Test MQTT connection
   mosquitto_pub -h your-broker -t test -m "test message"
   ```

3. **Permission Issues**
   ```bash
   # Check file permissions
   ls -la /opt/moisture-daemon/
   
   # Fix permissions if needed
   sudo chown -R moisture:moisture /opt/moisture-daemon/
   ```

4. **Service Won't Start**
   ```bash
   # Check service status
   sudo systemctl status moisture-daemon
   
   # View detailed logs
   sudo journalctl -u moisture-daemon -n 50
   ```

### Log Analysis

```bash
# View recent logs
sudo tail -f /var/log/moisture-daemon/moisture_client.log

# Search for errors
sudo grep ERROR /var/log/moisture-daemon/moisture_client.log

# Monitor cron execution
sudo tail -f /var/log/moisture-daemon/cron.log
```

## Maintenance

### Regular Tasks

1. **Monitor Logs**
   ```bash
   # Check for errors weekly
   sudo grep -i error /var/log/moisture-daemon/*.log
   ```

2. **Database Maintenance**
   ```bash
   # Clean old data (older than 1 year)
   mysql -u root -p -e "DELETE FROM moisture_db.moisture_readings WHERE timestamp < DATE_SUB(NOW(), INTERVAL 1 YEAR);"
   ```

3. **Update Application**
   ```bash
   # Stop service
   sudo systemctl stop moisture-daemon
   
   # Update files
   sudo cp new_moisture_client.py /opt/moisture-daemon/
   
   # Start service
   sudo systemctl start moisture-daemon
   ```

### Backup

```bash
# Backup database
mysqldump -u root -p moisture_db > moisture_backup_$(date +%Y%m%d).sql

# Backup configuration
sudo cp -r /opt/moisture-daemon/config/ ~/moisture_config_backup/
```

## Security Considerations

1. **Database Security**
   - Use dedicated database user with minimal privileges
   - Use strong passwords
   - Enable SSL for database connections

2. **MQTT Security**
   - Use TLS/SSL for MQTT connections
   - Implement proper authentication
   - Use specific topic permissions

3. **File Permissions**
   - Configuration files should be readable only by the application user
   - Log files should have appropriate permissions

4. **Network Security**
   - Use firewall rules to restrict access
   - Consider VPN for remote access

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify configuration settings
3. Test network connectivity (MQTT and database)
4. Review the health monitoring output

## License

This project is created for personal use. Modify and distribute as needed.