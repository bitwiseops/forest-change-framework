"""
Unit tests for EventBus pub/sub system.

Tests event publishing and subscription mechanisms.
"""

import pytest
from forest_change_framework.core import EventBus, EventError


@pytest.mark.unit
class TestEventBus:
    """Test EventBus functionality."""

    def test_subscribe_to_event(self, event_bus):
        """Test subscribing to an event."""
        called = []

        def callback(event_name, data):
            called.append((event_name, data))

        event_bus.subscribe("test.event", callback)
        assert "test.event" in event_bus._subscribers
        assert callback in event_bus._subscribers["test.event"]

    def test_subscribe_with_non_callable_raises_error(self, event_bus):
        """Test subscribing with non-callable raises error."""
        with pytest.raises(EventError):
            event_bus.subscribe("test.event", "not_callable")

    def test_publish_event(self, event_bus, event_collector):
        """Test publishing an event."""
        event_bus.subscribe("test.event", event_collector.collect)

        event_bus.publish("test.event", {"key": "value"})

        assert len(event_collector.events) == 1
        assert event_collector.events[0]["name"] == "test.event"
        assert event_collector.events[0]["data"]["key"] == "value"

    def test_publish_without_subscribers(self, event_bus):
        """Test publishing without subscribers doesn't raise error."""
        # Should not raise
        event_bus.publish("nonexistent.event", {"data": "value"})

    def test_publish_with_none_data(self, event_bus, event_collector):
        """Test publishing with None data."""
        event_bus.subscribe("test.event", event_collector.collect)

        event_bus.publish("test.event", None)

        assert len(event_collector.events) == 1
        assert event_collector.events[0]["data"] is None

    def test_unsubscribe_event(self, event_bus):
        """Test unsubscribing from event."""
        called = []

        def callback(event_name, data):
            called.append(event_name)

        event_bus.subscribe("test.event", callback)
        assert callback in event_bus._subscribers["test.event"]

        event_bus.unsubscribe("test.event", callback)
        assert callback not in event_bus._subscribers.get("test.event", [])

    def test_unsubscribe_nonexistent_raises_error(self, event_bus):
        """Test unsubscribing nonexistent event raises error."""
        def callback(event_name, data):
            pass

        with pytest.raises(EventError):
            event_bus.unsubscribe("nonexistent", callback)

    def test_unsubscribe_nonexistent_callback_raises_error(self, event_bus):
        """Test unsubscribing nonexistent callback raises error."""
        def callback1(event_name, data):
            pass

        def callback2(event_name, data):
            pass

        event_bus.subscribe("test.event", callback1)

        with pytest.raises(EventError):
            event_bus.unsubscribe("test.event", callback2)

    def test_multiple_subscribers(self, event_bus, event_collector):
        """Test multiple subscribers receiving same event."""
        called1 = []
        called2 = []

        def callback1(event_name, data):
            called1.append(event_name)

        def callback2(event_name, data):
            called2.append(event_name)

        event_bus.subscribe("test.event", callback1)
        event_bus.subscribe("test.event", callback2)

        event_bus.publish("test.event", {})

        assert len(called1) == 1
        assert len(called2) == 1

    def test_get_subscribers(self, event_bus):
        """Test getting list of subscribers."""
        def callback1(event_name, data):
            pass

        def callback2(event_name, data):
            pass

        event_bus.subscribe("test.event", callback1)
        event_bus.subscribe("test.event", callback2)

        subscribers = event_bus.get_subscribers("test.event")

        assert len(subscribers) == 2
        assert callback1 in subscribers
        assert callback2 in subscribers

    def test_get_subscribers_nonexistent_event(self, event_bus):
        """Test getting subscribers for nonexistent event returns empty."""
        subscribers = event_bus.get_subscribers("nonexistent")
        assert subscribers == []

    def test_clear_event_bus(self, event_bus):
        """Test clearing all subscribers."""
        def callback(event_name, data):
            pass

        event_bus.subscribe("event1", callback)
        event_bus.subscribe("event2", callback)

        assert len(event_bus._subscribers) > 0

        event_bus.clear()

        assert len(event_bus._subscribers) == 0

    def test_subscriber_exception_doesnt_break_bus(self, event_bus):
        """Test that exception in subscriber doesn't break event bus."""
        called = []

        def failing_callback(event_name, data):
            raise RuntimeError("Callback failed")

        def good_callback(event_name, data):
            called.append(event_name)

        event_bus.subscribe("test.event", failing_callback)
        event_bus.subscribe("test.event", good_callback)

        # This should not raise
        event_bus.publish("test.event", {})

        # Good callback should still be called
        assert len(called) == 1

    def test_different_events_independent(self, event_bus, event_collector):
        """Test that different events are independent."""
        event_bus.subscribe("event1", event_collector.collect)
        event_bus.subscribe("event2", event_collector.collect)

        event_bus.publish("event1", {"source": "event1"})
        event_bus.publish("event2", {"source": "event2"})

        assert len(event_collector.events) == 2
        assert event_collector.events[0]["name"] == "event1"
        assert event_collector.events[1]["name"] == "event2"
