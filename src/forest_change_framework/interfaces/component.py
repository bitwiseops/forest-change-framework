"""
Abstract base component interface.

This module defines the BaseComponent interface that all components must implement
to participate in the framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

from ..core.events import EventBus

logger = logging.getLogger(__name__)


class BaseComponent(ABC):
    """
    Abstract base class for all framework components.

    All components must inherit from BaseComponent and implement the required
    abstract methods. Components are configured via dependency injection and
    communicate with other components only through the event bus.

    Attributes:
        event_bus: Reference to the central event bus for publishing events.
    """

    def __init__(
        self, event_bus: EventBus, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the component.

        Args:
            event_bus: The central event bus for inter-component communication.
            config: Configuration dictionary for this component instance.
        """
        self.event_bus = event_bus
        self._config = config or {}
        logger.debug(f"Component {self.__class__.__name__} initialized")

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the component with configuration.

        This method is called after instantiation to set up the component based
        on its configuration. Components should validate configuration and prepare
        any resources needed for execution.

        Args:
            config: Configuration dictionary for this component.

        Raises:
            Exception: Subclasses should raise appropriate exceptions for config errors.

        Example:
            >>> def initialize(self, config):
            ...     required_key = config.get("required_key")
            ...     if not required_key:
            ...         raise ValueError("required_key not found in config")
        """
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the component's core functionality.

        This is the main method that performs the component's work. It should
        return results and may publish events to notify other components of
        its completion or status.

        Args:
            *args: Positional arguments specific to the component.
            **kwargs: Keyword arguments specific to the component.

        Returns:
            Component-specific return value. Can be any type.

        Raises:
            Exception: Subclasses should raise appropriate exceptions for runtime errors.

        Example:
            >>> def execute(self, input_path):
            ...     data = self._load_data(input_path)
            ...     self.event_bus.publish("data.loaded", {"size": len(data)})
            ...     return data
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up component resources.

        This method is called when the component is no longer needed. It should
        close connections, release locks, or perform any other cleanup operations.

        It's safe to leave this unimplemented if no cleanup is needed, but the
        method must be defined (even as a pass statement).

        Example:
            >>> def cleanup(self):
            ...     if hasattr(self, '_db_connection'):
            ...         self._db_connection.close()
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the component name.

        Returns:
            Unique name identifying this component type.

        Example:
            >>> @property
            ... def name(self) -> str:
            ...     return "my_component"
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Get the component version.

        Returns:
            Semantic version string (e.g., "1.0.0").

        Example:
            >>> @property
            ... def version(self) -> str:
            ...     return "1.0.0"
        """
        pass

    def publish_event(self, event_name: str, event_data: Any = None) -> None:
        """
        Publish an event through the framework event bus.

        Convenience method for publishing events. Components should use this
        to communicate with other components rather than direct imports.

        Args:
            event_name: Name of the event to publish.
            event_data: Optional data to include with the event.

        Example:
            >>> self.publish_event("component.complete", {"result": result})
        """
        self.event_bus.publish(event_name, event_data)

    def subscribe_event(self, event_name: str, callback: Any) -> None:
        """
        Subscribe to an event through the framework event bus.

        Allows this component to react to events from other components.

        Args:
            event_name: Name of the event to subscribe to.
            callback: Callable that receives (event_name, event_data).

        Example:
            >>> def on_data_loaded(event_name, data):
            ...     self.process_data(data)
            >>> self.subscribe_event("data.loaded", on_data_loaded)
        """
        self.event_bus.subscribe(event_name, callback)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value for this component.

        Args:
            key: Configuration key (supports dot notation for nested keys).
            default: Default value if key not found.

        Returns:
            Configuration value or default.

        Example:
            >>> output_path = self.get_config("output.path", "/tmp/output")
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value
