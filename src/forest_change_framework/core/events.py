"""
Event bus system for inter-component communication.

This module implements an event-driven architecture using a publish/subscribe pattern,
allowing components to communicate without direct dependencies on each other.
"""

from typing import Any, Callable, Dict, List
import logging

from .exceptions import EventError

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event bus for publish/subscribe communication between components.

    The EventBus implements a publish/subscribe pattern that allows components
    to emit events and subscribe to events from other components without
    creating direct dependencies.

    Attributes:
        _subscribers: Dictionary mapping event names to lists of subscriber callbacks.
    """

    def __init__(self) -> None:
        """Initialize the event bus with an empty subscriber registry."""
        self._subscribers: Dict[str, List[Callable[[str, Any], None]]] = {}
        logger.debug("EventBus initialized")

    def subscribe(self, event_name: str, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to an event.

        Args:
            event_name: The name of the event to subscribe to.
            callback: A callable that receives (event_name, event_data) when the event is published.

        Raises:
            EventError: If the callback is not callable.

        Example:
            >>> bus = EventBus()
            >>> def on_data_loaded(event_name, data):
            ...     print(f"Event {event_name} received with data: {data}")
            >>> bus.subscribe("data.loaded", on_data_loaded)
        """
        if not callable(callback):
            raise EventError(f"Callback must be callable, got {type(callback)}")

        if event_name not in self._subscribers:
            self._subscribers[event_name] = []

        self._subscribers[event_name].append(callback)
        logger.debug(f"Subscriber added for event: {event_name}")

    def unsubscribe(
        self, event_name: str, callback: Callable[[str, Any], None]
    ) -> None:
        """
        Unsubscribe from an event.

        Args:
            event_name: The name of the event to unsubscribe from.
            callback: The callback function to remove.

        Raises:
            EventError: If the event or callback is not found.

        Example:
            >>> bus = EventBus()
            >>> def handler(event_name, data): pass
            >>> bus.subscribe("data.loaded", handler)
            >>> bus.unsubscribe("data.loaded", handler)
        """
        if event_name not in self._subscribers:
            raise EventError(f"No subscribers for event: {event_name}")

        try:
            self._subscribers[event_name].remove(callback)
            logger.debug(f"Subscriber removed from event: {event_name}")
        except ValueError:
            raise EventError(f"Callback not found for event: {event_name}")

        # Clean up empty event entries
        if not self._subscribers[event_name]:
            del self._subscribers[event_name]

    def publish(self, event_name: str, event_data: Any = None) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_name: The name of the event to publish.
            event_data: Optional data to pass to subscribers.

        Example:
            >>> bus = EventBus()
            >>> def on_event(event_name, data):
            ...     print(f"Received: {data}")
            >>> bus.subscribe("test.event", on_event)
            >>> bus.publish("test.event", {"status": "success"})
            Received: {'status': 'success'}
        """
        logger.debug(f"Publishing event: {event_name} with data: {event_data}")

        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                try:
                    callback(event_name, event_data)
                except Exception as e:
                    logger.error(
                        f"Error in callback for event {event_name}: {str(e)}",
                        exc_info=True,
                    )

    def get_subscribers(self, event_name: str) -> List[Callable[[str, Any], None]]:
        """
        Get the list of subscribers for an event.

        Args:
            event_name: The name of the event.

        Returns:
            List of subscriber callbacks for the event, or empty list if none exist.

        Example:
            >>> bus = EventBus()
            >>> def handler(event_name, data): pass
            >>> bus.subscribe("test", handler)
            >>> len(bus.get_subscribers("test"))
            1
        """
        return self._subscribers.get(event_name, [])

    def clear(self) -> None:
        """Clear all subscribers. Useful for testing."""
        self._subscribers.clear()
        logger.debug("EventBus cleared")
