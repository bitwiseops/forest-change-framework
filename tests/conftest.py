"""
Pytest configuration and shared fixtures for the test suite.

This module provides reusable fixtures for testing framework components.
"""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Any, Dict, Optional

from forest_change_framework import (
    BaseFramework,
    ComponentRegistry,
    ConfigManager,
    EventBus,
    register_component,
)
from forest_change_framework.interfaces import BaseComponent


# ========== FRAMEWORK FIXTURES ==========

@pytest.fixture
def clean_registry():
    """
    Provide a clean component registry for testing.

    Clears the global registry before the test and restores it after.
    """
    from forest_change_framework.core import get_registry

    registry = get_registry()
    original_components = {}

    # Save original components
    for category, comps in registry._components.items():
        original_components[category] = comps.copy()

    # Clear for test
    registry.clear()

    yield registry

    # Restore original components
    registry.clear()
    registry._components.update(original_components)


@pytest.fixture
def framework():
    """Provide a fresh BaseFramework instance for testing."""
    return BaseFramework()


@pytest.fixture
def event_bus():
    """Provide a fresh EventBus instance for testing."""
    return EventBus()


@pytest.fixture
def config_manager():
    """Provide a fresh ConfigManager instance for testing."""
    return ConfigManager()


# ========== CONFIGURATION FIXTURES ==========

@pytest.fixture
def sample_config():
    """Provide sample configuration dictionary."""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db",
        },
        "processing": {
            "threshold": 0.7,
            "method": "ndvi",
        },
        "output": {
            "format": "geojson",
            "path": "/tmp/output",
        }
    }


@pytest.fixture
def temp_json_config(tmp_path, sample_config):
    """Create a temporary JSON configuration file."""
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(sample_config, f)
    return str(config_file)


@pytest.fixture
def temp_yaml_config(tmp_path, sample_config):
    """Create a temporary YAML configuration file."""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_config, f)
    return str(config_file)


# ========== COMPONENT FIXTURES ==========

@pytest.fixture
def mock_component_class():
    """Provide a mock component class for testing."""

    class MockComponent(BaseComponent):
        def __init__(self, event_bus, config=None):
            super().__init__(event_bus, config)
            self.initialized = False
            self.executed = False
            self.execute_result = "mock_result"

        @property
        def name(self) -> str:
            return "mock_component"

        @property
        def version(self) -> str:
            return "1.0.0"

        def initialize(self, config: Dict[str, Any]) -> None:
            self._config = config
            self.initialized = True

        def execute(self, *args, **kwargs):
            self.executed = True
            self.publish_event("mock.complete", {"status": "success"})
            return self.execute_result

        def cleanup(self) -> None:
            pass

    return MockComponent


@pytest.fixture
def registered_mock_component(clean_registry, mock_component_class):
    """Provide a registered mock component."""
    from forest_change_framework.core import get_registry

    registry = get_registry()
    registry.register(
        mock_component_class,
        "mock_component",
        "test",
        version="1.0.0",
        description="Mock component for testing",
    )
    return mock_component_class


@pytest.fixture
def failing_component_class():
    """Provide a component that raises an error."""

    class FailingComponent(BaseComponent):
        @property
        def name(self) -> str:
            return "failing_component"

        @property
        def version(self) -> str:
            return "1.0.0"

        def initialize(self, config: Dict[str, Any]) -> None:
            pass

        def execute(self, *args, **kwargs):
            raise RuntimeError("Component execution failed")

        def cleanup(self) -> None:
            pass

    return FailingComponent


@pytest.fixture
def event_tracking_component_class():
    """Provide a component that publishes multiple events."""

    class EventTrackingComponent(BaseComponent):
        def __init__(self, event_bus, config=None):
            super().__init__(event_bus, config)
            self.events_published = []

        @property
        def name(self) -> str:
            return "event_tracker"

        @property
        def version(self) -> str:
            return "1.0.0"

        def initialize(self, config: Dict[str, Any]) -> None:
            pass

        def execute(self, *args, **kwargs):
            self.publish_event("tracker.start", {"status": "starting"})
            self.publish_event("tracker.progress", {"progress": 50})
            self.publish_event("tracker.complete", {"status": "success"})
            return "completed"

        def cleanup(self) -> None:
            pass

    return EventTrackingComponent


# ========== DATA FIXTURES ==========

@pytest.fixture
def sample_csv_data(tmp_path):
    """Create a sample CSV data file."""
    csv_file = tmp_path / "sample_data.csv"
    csv_content = """id,name,value,timestamp
1,record_a,100,2020-01-15
2,record_b,200,2020-02-20
3,record_c,150,2020-03-18
4,record_d,300,2020-04-22
5,record_e,250,2020-05-19"""

    with open(csv_file, "w") as f:
        f.write(csv_content)

    return str(csv_file)


@pytest.fixture
def sample_data_records():
    """Provide sample data records."""
    return [
        {"id": 1, "name": "record_a", "value": 100, "timestamp": "2020-01-15"},
        {"id": 2, "name": "record_b", "value": 200, "timestamp": "2020-02-20"},
        {"id": 3, "name": "record_c", "value": 150, "timestamp": "2020-03-18"},
        {"id": 4, "name": "record_d", "value": 300, "timestamp": "2020-04-22"},
        {"id": 5, "name": "record_e", "value": 250, "timestamp": "2020-05-19"},
    ]


# ========== UTILITY FIXTURES ==========

@pytest.fixture
def temp_directory():
    """Provide a temporary directory that's cleaned up after test."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def event_collector():
    """Provide a utility to collect events for testing."""

    class EventCollector:
        def __init__(self):
            self.events = []

        def collect(self, event_name, event_data):
            self.events.append({
                "name": event_name,
                "data": event_data,
            })

        def get_events(self, event_name=None):
            if event_name:
                return [e for e in self.events if e["name"] == event_name]
            return self.events

        def clear(self):
            self.events.clear()

        def has_event(self, event_name):
            return any(e["name"] == event_name for e in self.events)

    return EventCollector()


# ========== MARKERS ==========

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests"
    )
