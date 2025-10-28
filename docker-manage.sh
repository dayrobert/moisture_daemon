#!/bin/bash
# Moisture Daemon Docker Management Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start          Start all services"
    echo "  stop           Stop all services"
    echo "  restart        Restart all services"
    echo "  logs           Show logs (add service name for specific service)"
    echo "  status         Show service status"
    echo "  build          Build application image"
    echo "  clean          Remove all containers and volumes"
    echo "  monitor        Start with monitoring services"
    echo "  shell          Open shell in moisture_daemon container"
    echo "  db-shell       Open MySQL shell"
    echo ""
    echo "Examples:"
    echo "  $0 start                 # Start core services"
    echo "  $0 monitor               # Start with monitoring"
    echo "  $0 logs moisture_daemon  # Show app logs"
    echo "  $0 shell                 # Open app shell"
}

ensure_env_file() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Creating .env file from template...${NC}"
        cp .env.docker .env
        echo -e "${GREEN}.env file created. Please review and modify as needed.${NC}"
    fi
}

case "$1" in
    start)
        ensure_env_file
        echo -e "${GREEN}Starting Moisture Daemon services...${NC}"
        docker-compose up -d
        echo -e "${GREEN}Services started! Use '$0 logs' to view logs.${NC}"
        ;;
    
    stop)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker-compose down
        echo -e "${GREEN}Services stopped.${NC}"
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        docker-compose restart
        echo -e "${GREEN}Services restarted.${NC}"
        ;;
    
    logs)
        if [ -n "$2" ]; then
            docker-compose logs -f "$2"
        else
            docker-compose logs -f
        fi
        ;;
    
    status)
        docker-compose ps
        ;;
    
    build)
        echo -e "${GREEN}Building application image...${NC}"
        docker-compose build
        echo -e "${GREEN}Build complete.${NC}"
        ;;
    
    clean)
        echo -e "${RED}This will remove all containers, networks, and volumes!${NC}"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            docker system prune -f
            echo -e "${GREEN}Cleanup complete.${NC}"
        else
            echo "Cancelled."
        fi
        ;;
    
    monitor)
        ensure_env_file
        echo -e "${GREEN}Starting services with monitoring...${NC}"
        docker-compose --profile monitoring up -d
        echo -e "${GREEN}Services started with monitoring!${NC}"
        echo -e "${GREEN}Grafana: http://localhost:3000 (admin/admin123)${NC}"
        echo -e "${GREEN}Prometheus: http://localhost:9090${NC}"
        ;;
    
    shell)
        echo -e "${GREEN}Opening shell in moisture_daemon container...${NC}"
        docker-compose exec moisture_daemon /bin/bash
        ;;
    
    db-shell)
        echo -e "${GREEN}Opening MySQL shell...${NC}"
        docker-compose exec mysql mysql -u root -p moisture_db
        ;;
    
    help|--help|-h)
        print_usage
        ;;
    
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac