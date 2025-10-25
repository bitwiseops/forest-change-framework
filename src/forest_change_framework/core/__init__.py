"""
Core framework components and utilities.

This package contains the fundamental components of the forest-change-framework:
- BaseFramework: Main framework orchestrator
- ComponentRegistry: Component registration and discovery
- ConfigManager: Configuration management
- EventBus: Event-driven communication
- Exception hierarchy: Custom exceptions
"""

from .base import BaseFramework
from .registry import ComponentRegistry, get_registry, register_component
from .config import ConfigManager
from .events import EventBus
from .exceptions import (
    FrameworkError,
    ComponentError,
    RegistryError,
    ConfigError,
    ValidationError,
    EventError,
    PluginError,
)

__all__ = [
    "BaseFramework",
    "ComponentRegistry",
    "get_registry",
    "register_component",
    "ConfigManager",
    "EventBus",
    "FrameworkError",
    "ComponentError",
    "RegistryError",
    "ConfigError",
    "ValidationError",
    "EventError",
    "PluginError",
]
