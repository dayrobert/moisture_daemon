#!/bin/bash

# Moisture Daemon MQTT Client Setup Script
# Run this script on your Ubuntu server to set up the application

set -e

echo "========================================="
echo "Moisture Daemon Setup"
echo "========================================="

# Configuration
APP_NAME="moisture-daemon"
APP_USER="moisture"
APP_DIR="/opt/moisture-daemon"
LOG_DIR="/var/log/moisture-daemon"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
CRON_FILE="/etc/cron.d/${APP_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        mysql-client \
        git \
        curl \
        systemd \
        cron
    
    print_status "System dependencies installed successfully"
}

# Create application user
create_user() {
    print_status "Creating application user '${APP_USER}'..."
    
    if id "$APP_USER" &>/dev/null; then
        print_warning "User '${APP_USER}' already exists"
    else
        useradd -r -s /bin/false -d "$APP_DIR" "$APP_USER"
        print_status "User '${APP_USER}' created"
    fi
}

# Create directories
create_directories() {
    print_status "Creating application directories..."
    
    mkdir -p "$APP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "${APP_DIR}/config"
    mkdir -p "${APP_DIR}/scripts"
    
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$LOG_DIR"
    
    print_status "Directories created successfully"
}

# Install Python dependencies
install_python_deps() {
    print_status "Setting up Python virtual environment..."
    
    cd "$APP_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_status "Python dependencies installed from requirements.txt"
    else
        # Install basic dependencies
        pip install paho-mqtt==1.6.1 mysql-connector-python==8.2.0 python-dotenv==1.0.0
        print_status "Basic Python dependencies installed"
    fi
    
    deactivate
    
    chown -R "$APP_USER:$APP_USER" "$APP_DIR/venv"
}

# Copy application files
copy_files() {
    print_status "Copying application files..."
    
    # This assumes the script is run from the MoistureClient directory
    if [ -f "moisture_client.py" ]; then
        cp moisture_client.py "$APP_DIR/"
        chown "$APP_USER:$APP_USER" "$APP_DIR/moisture_client.py"
        chmod +x "$APP_DIR/moisture_client.py"
    fi
    
    if [ -f "config/config.ini" ]; then
        cp config/config.ini "$APP_DIR/config/"
        chown "$APP_USER:$APP_USER" "$APP_DIR/config/config.ini"
    fi
    
    if [ -f "scripts/setup_database.py" ]; then
        cp scripts/setup_database.py "$APP_DIR/scripts/"
        chown "$APP_USER:$APP_USER" "$APP_DIR/scripts/setup_database.py"
        chmod +x "$APP_DIR/scripts/setup_database.py"
    fi
    
    print_status "Application files copied"
}

# Create systemd service
create_service() {
    print_status "Creating systemd service..."
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Moisture Daemon MQTT Client
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/moisture_client.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $APP_DIR/logs

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable "$APP_NAME"
    
    print_status "Systemd service created and enabled"
}

# Create cron job
create_cron_job() {
    print_status "Creating cron job..."
    
    cat > "$CRON_FILE" << EOF
# Moisture Daemon MQTT Client - runs every 5 minutes
# Logs are written to $LOG_DIR/cron.log

*/5 * * * * $APP_USER cd $APP_DIR && $APP_DIR/venv/bin/python $APP_DIR/moisture_client.py >> $LOG_DIR/cron.log 2>&1
EOF
    
    chmod 0644 "$CRON_FILE"
    
    print_status "Cron job created (runs every 5 minutes)"
}

# Setup log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/${APP_NAME}" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    su $APP_USER $APP_USER
}
EOF
    
    print_status "Log rotation configured"
}

# Create configuration template
create_config_template() {
    print_status "Creating configuration template..."
    
    if [ ! -f "$APP_DIR/config/.env" ]; then
        cat > "$APP_DIR/config/.env" << EOF
# Moisture Daemon MQTT Client Configuration
# Update these values for your environment

# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_TOPIC=moisture/+/data

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=moisture_db
DB_USER=root
DB_PASSWORD=

# Client Configuration
CLIENT_ID=moisture_client_$(hostname)
MAX_RUNTIME=300
LOG_LEVEL=INFO
LOG_FILE=$LOG_DIR/moisture_client.log
EOF
        
        chown "$APP_USER:$APP_USER" "$APP_DIR/config/.env"
        chmod 600 "$APP_DIR/config/.env"
        
        print_warning "Configuration file created at $APP_DIR/config/.env"
        print_warning "Please edit this file with your actual configuration before starting the service"
    fi
}

# Main installation function
main() {
    print_status "Starting installation..."
    
    check_root
    install_dependencies
    create_user
    create_directories
    copy_files
    install_python_deps
    create_service
    create_cron_job
    setup_log_rotation
    create_config_template
    
    echo ""
    echo "========================================="
    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo "========================================="
    echo ""
    echo "Next steps:"
    echo "1. Edit the configuration file: $APP_DIR/config/.env"
    echo "2. Set up your MySQL database (run setup_database.py)"
    echo "3. Test the application: sudo -u $APP_USER $APP_DIR/venv/bin/python $APP_DIR/moisture_client.py"
    echo "4. Start the systemd service: sudo systemctl start $APP_NAME"
    echo "5. Check service status: sudo systemctl status $APP_NAME"
    echo "6. View logs: sudo journalctl -u $APP_NAME -f"
    echo ""
    echo "The cron job will run every 5 minutes automatically."
    echo "Logs are stored in: $LOG_DIR/"
}

# Run main function
main "$@"