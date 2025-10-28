# Moisture Daemon - Docker Setup with External MQTT Broker

This setup configures the Moisture Daemon to use an external MQTT broker located at **192.168.6.115** instead of running a local Mosquitto container.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│  Moisture       │    │   Docker Container   │    │  External MQTT      │
│  Sensor         │───▶│   moisture_daemon    │───▶│  Broker             │
│  (ESP32)        │    │                      │    │  192.168.6.115:1883│
└─────────────────┘    └──────────────────────┘    └─────────────────────┘
                              │
                              ▼
                       ┌──────────────────────┐
                       │   MySQL Database     │
                       │   (Docker Container) │
                       └──────────────────────┘
```

## 📋 Prerequisites

1. **Docker & Docker Compose** installed
2. **Network connectivity** to 192.168.6.115:1883
3. **MQTT broker running** at 192.168.6.115 (should accept connections on port 1883)

## 🚀 Quick Start

### 1. Test MQTT Connectivity
```bash
./docker-external-mqtt.sh test
```

### 2. Configure Environment (Optional)
Edit `.env.external-mqtt` if you need to:
- Set MQTT credentials (if your broker requires authentication)
- Change database passwords
- Modify log levels

### 3. Start Services
```bash
# Start basic services (app + database)
./docker-external-mqtt.sh start

# OR start with monitoring (includes Prometheus & Grafana)
./docker-external-mqtt.sh monitor
```

### 4. Check Status
```bash
./docker-external-mqtt.sh status
```

### 5. View Logs
```bash
# All services
./docker-external-mqtt.sh logs

# Application only
./docker-external-mqtt.sh logs-app
```

## 🛠️ Management Commands

| Command | Description |
|---------|-------------|
| `./docker-external-mqtt.sh start` | Start all services |
| `./docker-external-mqtt.sh stop` | Stop all services |
| `./docker-external-mqtt.sh restart` | Restart all services |
| `./docker-external-mqtt.sh status` | Show service status |
| `./docker-external-mqtt.sh logs` | Show all logs |
| `./docker-external-mqtt.sh logs-app` | Show app logs only |
| `./docker-external-mqtt.sh build` | Rebuild application image |
| `./docker-external-mqtt.sh down` | Stop and remove containers |
| `./docker-external-mqtt.sh monitor` | Start with monitoring services |
| `./docker-external-mqtt.sh clean` | Remove everything including data |
| `./docker-external-mqtt.sh test` | Test MQTT connectivity |

## 🔧 Configuration

### Environment Variables (.env.external-mqtt)
```bash
# Database Configuration
MYSQL_ROOT_PASSWORD=secure_root_password_123
MYSQL_DATABASE=moisture_db
MYSQL_USER=moisture_user
MYSQL_PASSWORD=secure_moisture_pass_456

# MQTT Configuration (External Broker)
MQTT_USERNAME=          # Set if broker requires auth
MQTT_PASSWORD=          # Set if broker requires auth

# Application Configuration
LOG_LEVEL=INFO
CLIENT_ID=moisture_client_docker
```

### MQTT Broker Requirements
Your MQTT broker at 192.168.6.115 should:
- Accept connections on port 1883
- Allow the topics that moisture_daemon will use
- Be accessible from your Docker host network

## 📊 Services

### Core Services
- **moisture_daemon**: Main application container
- **mysql**: MySQL database for storing sensor data

### Optional Monitoring Services
- **prometheus**: Metrics collection (port 9090)
- **grafana**: Visualization dashboard (port 3000)
- **health_monitor**: Application health monitoring

## 🔍 Troubleshooting

### MQTT Connection Issues
1. **Test connectivity**: `./docker-external-mqtt.sh test`
2. **Check broker status**: Ensure 192.168.6.115:1883 is accessible
3. **Firewall**: Verify port 1883 is open
4. **Network**: Ensure Docker can reach the external IP

### Application Issues
1. **Check logs**: `./docker-external-mqtt.sh logs-app`
2. **Verify database**: `./docker-external-mqtt.sh status`
3. **Restart services**: `./docker-external-mqtt.sh restart`

### Database Issues
1. **Check MySQL logs**: `docker logs moisture_mysql`
2. **Verify connection**: Database should be ready before app starts
3. **Reset database**: `./docker-external-mqtt.sh clean` (WARNING: destroys data)

## 🌐 Accessing Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin123 |
| Prometheus | http://localhost:9090 | No auth |
| MySQL | localhost:3306 | moisture_user / secure_moisture_pass_456 |

## 📝 Notes

1. **External MQTT**: This setup assumes your MQTT broker at 192.168.6.115 is properly configured and accessible
2. **Data Persistence**: MySQL data is stored in Docker volumes and persists between restarts
3. **Logs**: Application logs are stored in `./logs/` directory
4. **Configuration**: App configuration can be customized in `./docker/app/config.ini`

## 🔒 Security Considerations

1. **Change default passwords** in `.env.external-mqtt`
2. **Secure MQTT broker** if it's accessible from internet
3. **Network isolation** - consider using Docker networks appropriately
4. **Regular updates** of Docker images

## 📞 Support

If you encounter issues:
1. Check the logs: `./docker-external-mqtt.sh logs`
2. Test MQTT connectivity: `./docker-external-mqtt.sh test`
3. Verify your external MQTT broker is running and accessible