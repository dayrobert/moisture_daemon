# MQTT Broker Removal - Docker Compose Update

## Changes Made

### 🗑️ Removed Services
- **mosquitto** service completely removed from docker-compose.yml
- Container `moisture_mosquitto` will no longer be created
- Ports 1883 and 9001 no longer exposed by Docker

### 🔧 Updated Dependencies  
- Removed `mosquitto: condition: service_started` dependency from moisture_daemon
- moisture_daemon now only depends on MySQL database

### ⚙️ Environment Configuration
- Removed hardcoded MQTT environment variables from docker-compose.yml:
  - `MQTT_BROKER: mosquitto` 
  - `MQTT_PORT: 1883`
  - `MQTT_USERNAME: ${MQTT_USERNAME:-}`
  - `MQTT_PASSWORD: ${MQTT_PASSWORD:-}`

## Configuration Source

The application now reads MQTT settings from:
- **File**: `/app/config/config.ini` (mounted from `./docker/app/config.ini`)
- **Current Settings**:
  ```ini
  [mqtt]
  broker = 192.168.6.115
  port = 1883
  username = 
  password = 
  topic = moisture/+/data
  qos = 1
  keepalive = 60
  ```

## External MQTT Broker Requirement

⚠️ **Important**: Your application now requires an external MQTT broker running at:
- **Host**: `192.168.6.115` 
- **Port**: `1883`

## Usage Instructions

### Start Services (Without Local MQTT)
```bash
./docker-manage.sh start
```

### Update MQTT Configuration
Edit the MQTT broker settings in:
```bash
# Edit the Docker configuration
nano docker/app/config.ini

# Or edit the local configuration  
nano config/config.ini
```

### Apply Configuration Changes
After changing config.ini:
```bash
./docker-manage.sh restart
```

## Benefits

✅ **Reduced Resource Usage**: No local Mosquitto container  
✅ **Simplified Deployment**: Fewer services to manage  
✅ **Flexible Configuration**: Easy to change MQTT broker via config files  
✅ **External Integration**: Can connect to any MQTT broker on your network  

## Migration Notes

- If you were using the local Mosquitto broker, ensure your external broker at `192.168.6.115:1883` is running
- Update your sensor devices to publish to the external broker  
- The application will fail to start if it cannot connect to the configured MQTT broker

## Troubleshooting

If the application fails to connect to MQTT:
1. Verify the external broker is running: `telnet 192.168.6.115 1883`
2. Check firewall settings on the broker host
3. Update `docker/app/config.ini` with correct broker details
4. Restart services: `./docker-manage.sh restart`