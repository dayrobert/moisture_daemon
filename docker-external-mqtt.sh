#!/bin/bash

# Moisture Daemon Docker Compose Manager (External MQTT)
# This script manages the Docker Compose setup that uses an external MQTT broker at 192.168.6.115

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.external-mqtt.yml"
ENV_FILE="$SCRIPT_DIR/.env.external-mqtt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check if docker and docker-compose are installed
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
}

# Test connectivity to external MQTT broker
test_mqtt_connectivity() {
    print_status "Testing connectivity to MQTT broker at 192.168.6.115..."
    
    if command -v nc &> /dev/null; then
        if nc -z -w5 192.168.6.115 1883 2>/dev/null; then
            print_status "✓ MQTT broker at 192.168.6.115:1883 is reachable"
        else
            print_warning "⚠ Cannot reach MQTT broker at 192.168.6.115:1883"
            print_warning "Please ensure:"
            print_warning "  1. The MQTT broker is running"
            print_warning "  2. Port 1883 is open"
            print_warning "  3. Your network allows access to 192.168.6.115"
        fi
    else
        print_warning "netcat (nc) not available - skipping connectivity test"
    fi
}

# Show usage information
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start all services"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show status of all services"
    echo "  logs      Show logs from all services"
    echo "  logs-app  Show logs from moisture_daemon only"
    echo "  build     Build/rebuild the application image"
    echo "  down      Stop and remove all containers, networks"
    echo "  monitor   Start with monitoring services (Prometheus/Grafana)"
    echo "  clean     Stop services and remove volumes (DESTRUCTIVE)"
    echo "  test      Test MQTT connectivity"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start basic services (app + database)"
    echo "  $0 monitor        # Start with monitoring enabled"
    echo "  $0 logs-app       # View application logs"
}

# Start services
start_services() {
    print_header "Starting Moisture Daemon Services (External MQTT)"
    test_mqtt_connectivity
    print_status "Starting services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    print_status "Services started successfully!"
    print_status "Application will be available once MySQL is ready and application connects to MQTT"
    echo ""
    echo "To view logs: $0 logs"
    echo "To check status: $0 status"
}

# Start with monitoring
start_with_monitoring() {
    print_header "Starting Moisture Daemon Services with Monitoring"
    test_mqtt_connectivity
    print_status "Starting services with monitoring..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --profile monitoring up -d
    print_status "Services started successfully!"
    print_status "Grafana will be available at http://localhost:3000 (admin/admin123)"
    print_status "Prometheus will be available at http://localhost:9090"
}

# Stop services
stop_services() {
    print_header "Stopping Moisture Daemon Services"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop
    print_status "Services stopped successfully!"
}

# Restart services
restart_services() {
    print_header "Restarting Moisture Daemon Services"
    stop_services
    start_services
}

# Show status
show_status() {
    print_header "Service Status"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
}

# Show logs
show_logs() {
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
}

# Show app logs only
show_app_logs() {
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f moisture_daemon
}

# Build application
build_app() {
    print_header "Building Application Image"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
    print_status "Build completed successfully!"
}

# Down services
down_services() {
    print_header "Stopping and Removing Services"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    print_status "Services removed successfully!"
}

# Clean everything (DESTRUCTIVE)
clean_all() {
    print_header "Cleaning All Data (DESTRUCTIVE OPERATION)"
    print_warning "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v --remove-orphans
        print_status "All data cleaned successfully!"
    else
        print_status "Operation cancelled"
    fi
}

# Main script logic
main() {
    check_dependencies
    
    case "${1:-}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        logs-app)
            show_app_logs
            ;;
        build)
            build_app
            ;;
        down)
            down_services
            ;;
        monitor)
            start_with_monitoring
            ;;
        clean)
            clean_all
            ;;
        test)
            test_mqtt_connectivity
            ;;
        help|--help|-h)
            show_usage
            ;;
        "")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"