# Tests for Moisture Daemon

This directory contains unit tests for the moisture_daemon project.

## Structure

- `test_moisture_client.py` - Tests for the main MoistureClient class
- `test_config.py` - Configuration loading and validation tests
- `test_database.py` - Database connection and operations tests
- `test_mqtt.py` - MQTT client functionality tests
- `conftest.py` - Pytest configuration and fixtures

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test file:
```bash
pytest tests/test_moisture_client.py
```

### Run with coverage:
```bash
pytest --cov=moisture_client --cov-report=html
```

### Run with verbose output:
```bash
pytest -v
```

## Test Configuration

Tests use a separate test configuration to avoid interfering with production settings.
See `conftest.py` for test fixtures and configuration.