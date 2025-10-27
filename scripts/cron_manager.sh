#!/bin/bash

# MoistureSensor MQTT Client - Cron Job Helper Script
# This script provides easy management of the cron job

APP_USER="moisture"
APP_DIR="/opt/moisture-client"
CRON_FILE="/etc/cron.d/moisture-client"

print_usage() {
    echo "Usage: $0 {install|uninstall|status|logs|test}"
    echo ""
    echo "Commands:"
    echo "  install   - Install/update the cron job"
    echo "  uninstall - Remove the cron job"
    echo "  status    - Show cron job status"
    echo "  logs      - Show recent cron logs"
    echo "  test      - Test the application manually"
    exit 1
}

install_cron() {
    echo "Installing cron job..."
    
    cat > "$CRON_FILE" << EOF
# MoistureSensor MQTT Client - runs every 5 minutes
# Logs are written to /var/log/moisture-client/cron.log

*/5 * * * * $APP_USER cd $APP_DIR && $APP_DIR/venv/bin/python $APP_DIR/moisture_client.py >> /var/log/moisture-client/cron.log 2>&1
EOF
    
    chmod 0644 "$CRON_FILE"
    systemctl reload cron
    
    echo "Cron job installed successfully"
    echo "The application will run every 5 minutes"
}

uninstall_cron() {
    echo "Removing cron job..."
    
    if [ -f "$CRON_FILE" ]; then
        rm "$CRON_FILE"
        systemctl reload cron
        echo "Cron job removed successfully"
    else
        echo "Cron job not found"
    fi
}

show_status() {
    echo "Cron Job Status:"
    echo "=================="
    
    if [ -f "$CRON_FILE" ]; then
        echo "✓ Cron job is installed"
        echo ""
        echo "Current schedule:"
        cat "$CRON_FILE" | grep -v "^#"
        echo ""
        echo "Recent executions:"
        grep "moisture_client.py" /var/log/cron.log 2>/dev/null | tail -5 || echo "No recent executions found in /var/log/cron.log"
    else
        echo "✗ Cron job is not installed"
    fi
    
    echo ""
    echo "Application status:"
    if [ -f "$APP_DIR/moisture_client.py" ]; then
        echo "✓ Application is installed"
    else
        echo "✗ Application not found"
    fi
    
    echo ""
    echo "Recent application logs:"
    if [ -f "/var/log/moisture-client/cron.log" ]; then
        tail -10 /var/log/moisture-client/cron.log
    else
        echo "No cron logs found"
    fi
}

show_logs() {
    echo "Recent Cron Logs:"
    echo "=================="
    
    if [ -f "/var/log/moisture-client/cron.log" ]; then
        tail -50 /var/log/moisture-client/cron.log
    else
        echo "No cron logs found at /var/log/moisture-client/cron.log"
    fi
    
    echo ""
    echo "Recent Application Logs:"
    echo "========================"
    
    if [ -f "/var/log/moisture-client/moisture_client.log" ]; then
        tail -20 /var/log/moisture-client/moisture_client.log
    else
        echo "No application logs found"
    fi
}

test_application() {
    echo "Testing application..."
    echo "======================"
    
    if [ ! -f "$APP_DIR/moisture_client.py" ]; then
        echo "✗ Application not found at $APP_DIR/moisture_client.py"
        exit 1
    fi
    
    echo "Running application as user '$APP_USER'..."
    echo "This will run for maximum 5 minutes (MAX_RUNTIME setting)"
    echo ""
    
    # Run as the application user
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" "$APP_DIR/moisture_client.py"
    
    echo ""
    echo "Test completed. Check the logs above for any errors."
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# Parse command line arguments
case "${1:-}" in
    install)
        install_cron
        ;;
    uninstall)
        uninstall_cron
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        test_application
        ;;
    *)
        print_usage
        ;;
esac