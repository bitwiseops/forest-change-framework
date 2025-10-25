"""
Integration tests for component lifecycle and framework orchestration.

Tests the complete component lifecycle from registration through execution.
"""

import pytest
from forest_change_framework import BaseFramework, register_component
from forest_change_framework.interfaces import BaseComponent


@pytest.mark.integration
class TestComponentLifecycle:
    """Test component lifecycle management."""

    def test_component_initialization_sequence(self, framework, clean_registry):
        """Test component initialization sequence."""
        init_calls = []

        @register_component("test", "seq_test")
        class SequenceTestComponent(BaseComponent):
            @property
            def name(self):
                return "seq_test"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                init_calls.append(("initialize", config))

            def execute(self, *args, **kwargs):
                init_calls.append(("execute", args, kwargs))

            def cleanup(self):
                init_calls.append(("cleanup",))

        result = framework.execute_component(
            "test",
            "seq_test",
            {"test": "config"}
        )

        # Verify sequence
        assert len(init_calls) == 3
        assert init_calls[0][0] == "initialize"
        assert init_calls[1][0] == "execute"
        assert init_calls[2][0] == "cleanup"

    def test_component_cleanup_on_error(self, framework, clean_registry):
        """Test cleanup is called even on error."""
        cleanup_called = []

        @register_component("test", "error_test")
        class ErrorTestComponent(BaseComponent):
            @property
            def name(self):
                return "error_test"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                raise RuntimeError("Intentional error")

            def cleanup(self):
                cleanup_called.append(True)

        with pytest.raises(RuntimeError):
            framework.execute_component("test", "error_test")

        # Cleanup should still be called
        assert len(cleanup_called) == 1

    def test_event_driven_component_chain(self, framework, clean_registry, event_collector):
        """Test event-driven communication between components."""
        execution_order = []

        @register_component("stage1", "producer")
        class ProducerComponent(BaseComponent):
            @property
            def name(self):
                return "producer"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                execution_order.append("producer")
                self.publish_event("data.ready", {"data": "test_data"})
                return "produced_data"

            def cleanup(self):
                pass

        @register_component("stage2", "consumer")
        class ConsumerComponent(BaseComponent):
            def __init__(self, event_bus, config=None):
                super().__init__(event_bus, config)
                self.received_data = None

            @property
            def name(self):
                return "consumer"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                # Subscribe to producer event
                self.subscribe_event("data.ready", self.on_data_ready)

            def execute(self, *args, **kwargs):
                execution_order.append("consumer")
                return self.received_data

            def cleanup(self):
                pass

            def on_data_ready(self, event_name, data):
                self.received_data = data.get("data")

        # Setup event collector
        framework.subscribe_event("data.ready", event_collector.collect)

        # Execute producer
        result = framework.execute_component("stage1", "producer")

        assert "producer" in execution_order
        assert event_collector.has_event("data.ready")

    def test_multiple_components_same_category(self, framework, clean_registry):
        """Test multiple components in same category."""
        @register_component("process", "comp1")
        class Component1(BaseComponent):
            @property
            def name(self):
                return "comp1"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                return "result1"

            def cleanup(self):
                pass

        @register_component("process", "comp2")
        class Component2(BaseComponent):
            @property
            def name(self):
                return "comp2"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                return "result2"

            def cleanup(self):
                pass

        result1 = framework.execute_component("process", "comp1")
        result2 = framework.execute_component("process", "comp2")

        assert result1 == "result1"
        assert result2 == "result2"

    def test_component_configuration_inheritance(self, framework, clean_registry):
        """Test component configuration is properly passed."""
        received_config = []

        @register_component("config", "test")
        class ConfigTestComponent(BaseComponent):
            @property
            def name(self):
                return "test"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                received_config.append(config)

            def execute(self, *args, **kwargs):
                return self.get_config("key1")

            def cleanup(self):
                pass

        result = framework.execute_component(
            "config",
            "test",
            key1="value1",
            key2="value2"
        )

        assert result == "value1"
        assert received_config[0]["key1"] == "value1"
        assert received_config[0]["key2"] == "value2"


@pytest.mark.integration
class TestEventDrivenCommunication:
    """Test event-driven communication patterns."""

    def test_event_subscription_and_publishing(self, framework, event_collector):
        """Test basic event pub/sub."""
        framework.subscribe_event("test.event", event_collector.collect)

        framework.publish_event("test.event", {"key": "value"})

        assert event_collector.has_event("test.event")
        assert event_collector.events[0]["data"]["key"] == "value"

    def test_multiple_event_subscriptions(self, framework):
        """Test multiple subscriptions to different events."""
        events_received = []

        def collect1(event_name, data):
            events_received.append(("callback1", event_name))

        def collect2(event_name, data):
            events_received.append(("callback2", event_name))

        framework.subscribe_event("event1", collect1)
        framework.subscribe_event("event2", collect2)

        framework.publish_event("event1", {})
        framework.publish_event("event2", {})

        assert len(events_received) == 2
        assert ("callback1", "event1") in events_received
        assert ("callback2", "event2") in events_received

    def test_event_unsubscription(self, framework):
        """Test unsubscribing from events."""
        called = []

        def callback(event_name, data):
            called.append(event_name)

        framework.subscribe_event("test", callback)
        framework.publish_event("test", {})
        assert len(called) == 1

        framework.unsubscribe_event("test", callback)
        framework.publish_event("test", {})
        assert len(called) == 1  # Still 1, not 2


@pytest.mark.integration
class TestFrameworkIntegration:
    """Test framework integration with components."""

    def test_list_and_get_components(self, framework, clean_registry):
        """Test listing and retrieving components."""
        @register_component("analyze", "detector")
        class DetectorComponent(BaseComponent):
            @property
            def name(self):
                return "detector"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                return "detected"

            def cleanup(self):
                pass

        components = framework.list_components("analyze")
        assert "analyze" in components
        assert "detector" in components["analyze"]

        info = framework.get_component_info("analyze", "detector")
        assert info["name"] == "detector"
        assert info["version"] == "1.0.0"

    def test_error_handling_in_framework(self, framework, clean_registry):
        """Test framework error handling."""
        @register_component("error", "faulty")
        class FaultyComponent(BaseComponent):
            @property
            def name(self):
                return "faulty"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                raise ValueError("Component failed")

            def cleanup(self):
                pass

        with pytest.raises(ValueError):
            framework.execute_component("error", "faulty")

    def test_framework_with_custom_configuration(self, framework, sample_config):
        """Test framework with custom configuration."""
        framework_with_config = BaseFramework(sample_config)

        db_config = framework_with_config.config.get("database")
        assert db_config["host"] == "localhost"
        assert db_config["port"] == 5432
