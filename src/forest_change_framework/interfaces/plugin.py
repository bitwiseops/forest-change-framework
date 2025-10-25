"""
Abstract plugin interface.

This module defines the BasePlugin interface for optional plugin systems
that can extend framework functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BasePlugin(ABC):
    """
    Abstract base class for framework plugins.

    Plugins provide optional functionality that can be loaded and unloaded
    at runtime. Unlike components, plugins are not part of the main processing
    pipeline but provide supporting functionality.

    Attributes:
        name: The plugin name.
        version: The plugin version.
    """

    def __init__(self, name: str, version: str = "1.0.0") -> None:
        """
        Initialize the plugin.

        Args:
            name: The plugin name.
            version: The plugin version (default: "1.0.0").
        """
        self.name = name
        self.version = version
        logger.debug(f"Plugin {name} initialized")

    @abstractmethod
    def load(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Load and initialize the plugin.

        This method is called when the plugin is being loaded into the framework.
        The plugin should initialize any resources it needs.

        Args:
            config: Optional configuration dictionary for the plugin.

        Raises:
            Exception: Subclasses should raise appropriate exceptions for load errors.

        Example:
            >>> def load(self, config):
            ...     self.api_key = config.get("api_key")
            ...     self.client = SomeClient(api_key=self.api_key)
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """
        Unload and clean up the plugin.

        This method is called when the plugin is being unloaded. The plugin
        should release any resources it allocated during load().

        Raises:
            Exception: Subclasses should raise appropriate exceptions for unload errors.

        Example:
            >>> def unload(self):
            ...     if hasattr(self, 'client'):
            ...         self.client.close()
        """
        pass

    def on_enable(self) -> None:
        """
        Hook called when the plugin is enabled.

        Override this if your plugin needs to perform actions when enabled.
        """
        pass

    def on_disable(self) -> None:
        """
        Hook called when the plugin is disabled.

        Override this if your plugin needs to perform actions when disabled.
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        Get plugin metadata.

        Returns:
            Dictionary containing plugin information.
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.__doc__ or "No description available",
        }
