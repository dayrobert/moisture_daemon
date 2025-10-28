# Moisture Daemon Docker Setup

This document explains how to run the Moisture Daemon using Docker Compose.

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.docker .env
   ```

2. **Edit environment variables** in `.env` file as needed

3. **Start the services:**
   ```bash
   docker-compose up -d
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f moisture_daemon
   ```

## Services

### Core Services
- **moisture_daemon**: Main Python application
- **mysql**: MySQL 8.0 database
- **mosquitto**: Eclipse Mosquitto MQTT broker

### Optional Services (monitoring profile)
- **health_monitor**: Health monitoring service
- **prometheus**: Metrics collection
- **grafana**: Data visualization

## Usage

### Basic Usage
```bash
# Start core services
docker-compose up -d

# View all logs
docker-compose logs -f

# Stop services
docker-compose down
```

### With Monitoring
```bash
# Start with monitoring services
docker-compose --profile monitoring up -d

# Access Grafana at http://localhost:3000
# Default credentials: admin/admin123 (configurable in .env)
```

### Development Mode
```bash
# Build and start with live code changes
docker-compose up --build

# Run with specific service
docker-compose up moisture_daemon
```

## Configuration

### Environment Variables
Edit `.env` file to customize:
- Database credentials
- MQTT settings
- Log levels
- Grafana password

### Application Config
The Docker version uses `docker/app/config.ini` which is configured for container networking.

### MQTT Configuration
- **Internal**: Services communicate via container names
- **External**: MQTT broker exposed on port 1883
- **WebSocket**: Available on port 9001

### Database Access
- **Internal**: Services use container name `mysql`
- **External**: MySQL exposed on port 3306
- **Credentials**: Configured in `.env` file

## Data Persistence

Data is persisted in Docker volumes:
- `mysql_data`: MySQL database files
- `prometheus_data`: Prometheus metrics
- `grafana_data`: Grafana dashboards and settings

## Health Checks

All services include health checks:
- **MySQL**: Connection test
- **Application**: Python import test
- **Monitoring**: Service-specific checks

## Logs

Logs are available in:
- Container logs: `docker-compose logs [service]`
- Application logs: `./logs/` directory
- MQTT logs: `./docker/mosquitto/log/`

## Troubleshooting

### Common Issues

1. **Database connection failed**
   ```bash
   # Check MySQL health
   docker-compose ps mysql
   docker-compose logs mysql
   ```

2. **MQTT connection issues**
   ```bash
   # Check Mosquitto logs
   docker-compose logs mosquitto
   ```

3. **Permission issues**
   ```bash
   # Fix log directory permissions
   sudo chown -R $(id -u):$(id -g) logs/
   ```

### Reset Everything
```bash
# Stop and remove all containers, networks, and volumes
docker-compose down -v
docker-compose up -d
```

## Security Notes

- Change default passwords in `.env` file
- Enable MQTT authentication if needed
- Use proper firewall rules for exposed ports
- Consider using Docker secrets for production

## Monitoring

With monitoring profile enabled:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## Production Deployment

For production:
1. Use strong passwords in `.env`
2. Enable MQTT authentication
3. Configure proper backup strategies
4. Use Docker secrets for sensitive data
5. Set up log rotation
6. Configure firewall rules