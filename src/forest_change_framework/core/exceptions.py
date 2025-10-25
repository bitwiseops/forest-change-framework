"""
Custom exceptions for the forest-change-framework.

This module defines the exception hierarchy for the framework, providing
specific exception types for different error conditions.
"""


class FrameworkError(Exception):
    """Base exception for all framework-related errors."""

    pass


class ComponentError(FrameworkError):
    """Raised when there's an error with component operations."""

    pass


class RegistryError(FrameworkError):
    """Raised when there's an error with component registration or discovery."""

    pass


class ConfigError(FrameworkError):
    """Raised when there's a configuration-related error."""

    pass


class ValidationError(FrameworkError):
    """Raised when validation of input data fails."""

    pass


class EventError(FrameworkError):
    """Raised when there's an error with event bus operations."""

    pass


class PluginError(FrameworkError):
    """Raised when there's an error with plugin operations."""

    pass
