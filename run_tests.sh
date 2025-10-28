#!/bin/bash

# Test runner script for moisture_daemon
# This script sets up the environment and runs tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check if pytest is available
check_pytest() {
    # Try to find python and pytest
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed or not available"
        exit 1
    fi
    
    # Check if pytest is available with the python command
    if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
        print_error "pytest is not installed or not available"
        echo "Please install pytest: pip install pytest"
        exit 1
    fi
}

# Run tests with different options
run_tests() {
    local test_type="$1"
    
    case "$test_type" in
        "all")
            print_header "Running All Tests"
            $PYTHON_CMD -m pytest
            ;;
        "unit")
            print_header "Running Unit Tests"
            pytest -m "unit or not integration"
            ;;
        "integration")
            print_header "Running Integration Tests"
            pytest -m "integration"
            ;;
        "mqtt")
            print_header "Running MQTT Tests"
            pytest -m "mqtt" tests/test_mqtt.py
            ;;
        "database")
            print_header "Running Database Tests"
            pytest -m "database" tests/test_database.py
            ;;
        "config")
            print_header "Running Configuration Tests"
            pytest tests/test_config.py
            ;;
        "coverage")
            print_header "Running Tests with Coverage"
            pytest --cov=moisture_client --cov-report=html --cov-report=term
            ;;
        "quick")
            print_header "Running Quick Tests"
            $PYTHON_CMD test_quick.py
            ;;
        "verbose")
            print_header "Running Tests with Verbose Output"
            pytest -v -s
            ;;
        *)
            echo "Usage: $0 [test_type]"
            echo ""
            echo "Test types:"
            echo "  all         - Run all tests (default)"
            echo "  unit        - Run unit tests only"
            echo "  integration - Run integration tests only"
            echo "  mqtt        - Run MQTT-related tests"
            echo "  database    - Run database-related tests"
            echo "  config      - Run configuration tests"
            echo "  coverage    - Run tests with coverage report"
            echo "  quick       - Run quick tests (default, recommended)"
            echo "  verbose     - Run tests with verbose output"
            echo ""
            echo "Examples:"
            echo "  $0                # Run all tests"
            echo "  $0 unit          # Run unit tests"
            echo "  $0 coverage      # Run with coverage"
            echo "  $0 mqtt          # Run MQTT tests only"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    print_header "Moisture Daemon Test Runner"
    
    # Check dependencies
    check_pytest
    
    # Ensure we're in the right directory
    if [[ ! -f "moisture_client.py" ]]; then
        print_error "moisture_client.py not found. Are you in the right directory?"
        exit 1
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Set Python path
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
    
    # Run tests
    local test_type="${1:-quick}"
    run_tests "$test_type"
    
    # Check exit code and provide feedback
    if [[ $? -eq 0 ]]; then
        print_status "✅ All tests passed!"
        
        # If coverage was run, show where to find the report
        if [[ "$test_type" == "coverage" ]] && [[ -d "htmlcov" ]]; then
            print_status "📊 Coverage report generated in htmlcov/index.html"
        fi
    else
        print_error "❌ Some tests failed!"
        exit 1
    fi
}

main "$@"