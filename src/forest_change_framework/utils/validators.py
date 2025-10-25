"""
Input validation utilities.

This module provides validators for common types of input validation including
file paths, configuration schemas, and component interfaces.
"""

import os
from typing import Any, Callable, Dict, Optional
import re

from ..core.exceptions import ValidationError
from ..interfaces.component import BaseComponent


def validate_path(
    path: str, must_exist: bool = False, is_file: bool = False, is_dir: bool = False
) -> str:
    """
    Validate a file or directory path.

    Args:
        path: Path to validate.
        must_exist: If True, the path must exist.
        is_file: If True, the path must be a file (only checked if must_exist=True).
        is_dir: If True, the path must be a directory (only checked if must_exist=True).

    Returns:
        The path (expanded and normalized).

    Raises:
        ValidationError: If validation fails.

    Example:
        >>> validate_path("/var/data/file.csv", must_exist=True, is_file=True)
        '/var/data/file.csv'
    """
    # Expand user home directory
    expanded_path = os.path.expanduser(path)

    if must_exist:
        if not os.path.exists(expanded_path):
            raise ValidationError(f"Path does not exist: {path}")

        if is_file and not os.path.isfile(expanded_path):
            raise ValidationError(f"Path is not a file: {path}")

        if is_dir and not os.path.isdir(expanded_path):
            raise ValidationError(f"Path is not a directory: {path}")

    return os.path.normpath(expanded_path)


def validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate a configuration dictionary against a schema.

    Basic schema validation that checks for required keys and types.
    Schema format:
        {
            "key_name": str,  # key_name must be present and be a string
            "optional_key?": int,  # optional key (? suffix), must be int if present
        }

    Args:
        config: Configuration dictionary to validate.
        schema: Validation schema.

    Returns:
        True if valid.

    Raises:
        ValidationError: If validation fails.

    Example:
        >>> config = {"host": "localhost", "port": 5432}
        >>> schema = {"host": str, "port": int}
        >>> validate_config(config, schema)
        True
    """
    for key, expected_type in schema.items():
        is_optional = key.endswith("?")
        clean_key = key.rstrip("?")

        if clean_key not in config:
            if not is_optional:
                raise ValidationError(f"Required configuration key missing: {clean_key}")
            continue

        value = config[clean_key]
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"Configuration key '{clean_key}' has wrong type. "
                f"Expected {expected_type.__name__}, got {type(value).__name__}"
            )

    return True


def validate_component_interface(component: Any) -> bool:
    """
    Validate that an object implements the BaseComponent interface.

    Args:
        component: Object to validate.

    Returns:
        True if component implements the interface.

    Raises:
        ValidationError: If component doesn't implement required interface.

    Example:
        >>> class MyComponent(BaseComponent): pass
        >>> validate_component_interface(MyComponent())
        True
    """
    if not isinstance(component, BaseComponent):
        raise ValidationError(
            f"Component must inherit from BaseComponent, got {type(component).__name__}"
        )

    required_methods = ["initialize", "execute", "cleanup"]
    required_properties = ["name", "version"]

    for method in required_methods:
        if not hasattr(component, method):
            raise ValidationError(f"Component missing required method: {method}")

    for prop in required_properties:
        if not hasattr(component, prop):
            raise ValidationError(f"Component missing required property: {prop}")

    return True


def validate_email(email: str) -> bool:
    """
    Validate an email address format.

    Args:
        email: Email address to validate.

    Returns:
        True if email format is valid.

    Raises:
        ValidationError: If email format is invalid.

    Example:
        >>> validate_email("user@example.com")
        True
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email format: {email}")
    return True


def validate_choice(value: Any, choices: list) -> bool:
    """
    Validate that a value is one of the allowed choices.

    Args:
        value: Value to validate.
        choices: List of allowed choices.

    Returns:
        True if value is in choices.

    Raises:
        ValidationError: If value is not in choices.

    Example:
        >>> validate_choice("production", ["development", "staging", "production"])
        True
    """
    if value not in choices:
        raise ValidationError(
            f"Value {value} not in allowed choices: {choices}"
        )
    return True


def validate_range(
    value: float, min_value: Optional[float] = None, max_value: Optional[float] = None
) -> bool:
    """
    Validate that a numeric value is within a range.

    Args:
        value: Value to validate.
        min_value: Minimum allowed value (inclusive).
        max_value: Maximum allowed value (inclusive).

    Returns:
        True if value is in range.

    Raises:
        ValidationError: If value is out of range.

    Example:
        >>> validate_range(50, min_value=0, max_value=100)
        True
    """
    if min_value is not None and value < min_value:
        raise ValidationError(f"Value {value} is below minimum {min_value}")

    if max_value is not None and value > max_value:
        raise ValidationError(f"Value {value} exceeds maximum {max_value}")

    return True
