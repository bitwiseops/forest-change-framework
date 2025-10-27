"""
Base framework class for managing the component lifecycle.

This module provides the main BaseFramework class that orchestrates component
registration, configuration, initialization, and execution.
"""

from typing import Any, Dict, Optional, Type
import logging
import os
from pathlib import Path

from .registry import ComponentRegistry, get_registry
from .config import ConfigManager
from .events import EventBus
from .exceptions import ComponentError, FrameworkError, ConfigError

logger = logging.getLogger(__name__)


class BaseFramework:
    """
    Main framework class for managing components and their lifecycle.

    The BaseFramework serves as the central orchestrator for the system, managing:
    - Component registration and discovery
    - Configuration management
    - Event bus for inter-component communication
    - Component initialization and execution
    - Directory structure validation (config/ must exist, data/ auto-created)

    Attributes:
        registry: The component registry.
        event_bus: The central event bus.
        config: The framework configuration.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_dir: str = "./config",
        data_dir: str = "./data",
    ) -> None:
        """
        Initialize the framework.

        Args:
            config: Initial framework configuration dictionary (optional).
            config_dir: Path to config directory (default: "./config").
                Must exist with framework.yaml and component-specific YAML files.
            data_dir: Path to data directory (default: "./data").
                Auto-created if missing.

        Raises:
            ConfigError: If config directory doesn't exist or framework.yaml is missing.
        """
        self.registry = get_registry()
        self.event_bus = EventBus()
        self._config_dir = config_dir
        self._data_dir = data_dir

        # Validate and setup directories
        self._validate_and_setup_directories()

        # Load framework config from config folder (unless custom config provided)
        if config:
            self.config = ConfigManager.from_dict(config)
            logger.info("BaseFramework initialized with custom configuration")
        else:
            try:
                self.config = ConfigManager.from_config_folder(config_dir)
                logger.info("BaseFramework initialized with config from folder")
            except ConfigError as e:
                logger.error(f"Framework initialization failed: {str(e)}")
                raise

        self._components: Dict[str, Any] = {}

        logger.info(
            f"BaseFramework initialized. "
            f"Config dir: {self._config_dir}, Data dir: {self._data_dir}"
        )

    def _validate_and_setup_directories(self) -> None:
        """
        Validate and setup required directories.

        Requirements:
        - config/ folder must exist (fail if missing) with framework.yaml
        - data/ folder will be auto-created if missing

        Raises:
            ConfigError: If config directory doesn't exist or framework.yaml is missing.
        """
        # Validate config directory exists
        if not os.path.exists(self._config_dir):
            raise ConfigError(
                f"Configuration directory not found: {self._config_dir}\n"
                f"Please create '{self._config_dir}' folder with:\n"
                f"  - {self._config_dir}/framework.yaml (required)\n"
                f"  - {self._config_dir}/<component_name>.yaml for each component"
            )

        # Validate framework.yaml exists
        framework_config_path = os.path.join(self._config_dir, "framework.yaml")
        if not os.path.exists(framework_config_path):
            raise ConfigError(
                f"Framework configuration not found: {framework_config_path}\n"
                f"Please create {framework_config_path} with framework settings"
            )

        # Auto-create data directory if missing
        data_path = Path(self._data_dir)
        try:
            data_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Data directory ensured: {self._data_dir}")
        except OSError as e:
            raise FrameworkError(
                f"Failed to create data directory {self._data_dir}: {str(e)}"
            )

    def get_component_class(self, category: str, name: str) -> Type:
        """
        Get a component class from the registry.

        Args:
            category: The component category.
            name: The component name.

        Returns:
            The component class.

        Raises:
            FrameworkError: If component not found.
        """
        try:
            return self.registry.get(category, name)
        except Exception as e:
            raise FrameworkError(f"Failed to get component: {str(e)}")

    def instantiate_component(
        self, category: str, name: str, instance_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Instantiate and initialize a component.

        Args:
            category: The component category.
            name: The component name.
            instance_config: Configuration for this component instance.

        Returns:
            The initialized component instance.

        Raises:
            ComponentError: If instantiation or initialization fails.

        Example:
            >>> framework = BaseFramework()
            >>> component = framework.instantiate_component("data_ingestion", "sample_component")
        """
        try:
            component_class = self.get_component_class(category, name)
            instance = component_class(
                event_bus=self.event_bus,
                config=instance_config or {},
                output_base_dir=self._data_dir,
            )

            # Initialize the component
            if hasattr(instance, 'initialize'):
                instance.initialize(instance_config or {})

            logger.info(f"Component instantiated: {category}/{name}")
            return instance
        except Exception as e:
            raise ComponentError(
                f"Failed to instantiate component {category}/{name}: {str(e)}"
            )

    def execute_component(
        self, category: str, name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a component's logic.

        Args:
            category: The component category.
            name: The component name.
            *args: Positional arguments to pass to component's execute method.
            **kwargs: Keyword arguments to pass to component's execute method.

        Returns:
            The component's execution result.

        Raises:
            ComponentError: If execution fails.

        Example:
            >>> framework = BaseFramework()
            >>> result = framework.execute_component("analysis", "my_analyzer", data=input_data)
        """
        try:
            component = self.instantiate_component(category, name)
            result = component.execute(*args, **kwargs)

            # Cleanup
            if hasattr(component, 'cleanup'):
                component.cleanup()

            logger.info(f"Component executed: {category}/{name}")
            return result
        except Exception as e:
            raise ComponentError(
                f"Failed to execute component {category}/{name}: {str(e)}"
            )

    def list_components(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        List registered components.

        Args:
            category: Optional category to filter by.

        Returns:
            Dictionary of components organized by category.

        Example:
            >>> framework = BaseFramework()
            >>> all_components = framework.list_components()
            >>> data_ingestion_comps = framework.list_components("data_ingestion")
        """
        return self.registry.list_components(category)

    def get_component_info(self, category: str, name: str) -> Dict[str, Any]:
        """
        Get metadata for a registered component.

        Args:
            category: The component category.
            name: The component name.

        Returns:
            Dictionary containing component information.

        Raises:
            FrameworkError: If component not found.
        """
        try:
            return self.registry.get_info(category, name)
        except Exception as e:
            raise FrameworkError(f"Failed to get component info: {str(e)}")

    def subscribe_event(self, event_name: str, callback: Any) -> None:
        """
        Subscribe to a framework event.

        Args:
            event_name: Name of the event to subscribe to.
            callback: Callable that receives (event_name, event_data).

        Example:
            >>> framework = BaseFramework()
            >>> def on_complete(event_name, data):
            ...     print(f"Component complete: {data}")
            >>> framework.subscribe_event("component.complete", on_complete)
        """
        self.event_bus.subscribe(event_name, callback)
        logger.debug(f"Event subscription added: {event_name}")

    def unsubscribe_event(self, event_name: str, callback: Any) -> None:
        """
        Unsubscribe from a framework event.

        Args:
            event_name: Name of the event.
            callback: The callback function to remove.
        """
        self.event_bus.unsubscribe(event_name, callback)
        logger.debug(f"Event subscription removed: {event_name}")

    def publish_event(self, event_name: str, event_data: Any = None) -> None:
        """
        Publish an event to the event bus.

        Args:
            event_name: Name of the event.
            event_data: Optional event data.

        Example:
            >>> framework = BaseFramework()
            >>> framework.publish_event("custom.event", {"status": "success"})
        """
        self.event_bus.publish(event_name, event_data)
