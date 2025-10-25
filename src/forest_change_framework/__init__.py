"""
Forest Change Framework - A modular, extensible framework for forest change detection.

This framework provides a pluggable architecture for building forest change detection
and analysis workflows. It supports multiple data sources, preprocessing methods,
analysis algorithms, and output formats.

Key Features:
- Modular component architecture: Build workflows from independent components
- Event-driven communication: Components communicate via pub/sub events
- Configuration-driven: All components fully configurable
- Auto-discovery: Components self-register using decorators
- Extensible: Easy to add new components, plugins, and middleware

Basic Usage:
    >>> from forest_change_framework import BaseFramework
    >>> framework = BaseFramework()
    >>> components = framework.list_components()
    >>> data = framework.execute_component("data_ingestion", "sample_component")
"""

from .core import (
    BaseFramework,
    ComponentRegistry,
    get_registry,
    register_component,
    ConfigManager,
    EventBus,
    FrameworkError,
    ComponentError,
    RegistryError,
    ConfigError,
    ValidationError,
    EventError,
    PluginError,
)

from .interfaces import (
    BaseComponent,
    BasePlugin,
    BaseMiddleware,
)

from .utils import (
    setup_logging,
    get_logger,
    LoggerMixin,
)

__version__ = "0.1.0"
__author__ = "Flavio Cordari"
__license__ = "MIT"

__all__ = [
    # Core
    "BaseFramework",
    "ComponentRegistry",
    "get_registry",
    "register_component",
    "ConfigManager",
    "EventBus",
    # Exceptions
    "FrameworkError",
    "ComponentError",
    "RegistryError",
    "ConfigError",
    "ValidationError",
    "EventError",
    "PluginError",
    # Interfaces
    "BaseComponent",
    "BasePlugin",
    "BaseMiddleware",
    # Utils
    "setup_logging",
    "get_logger",
    "LoggerMixin",
]
