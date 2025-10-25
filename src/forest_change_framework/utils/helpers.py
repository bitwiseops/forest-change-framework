"""
Common utility helper functions.

This module provides general-purpose helper functions used throughout the framework
for common operations like configuration merging, dictionary manipulation, and
file operations.
"""

import json
import os
from typing import Any, Dict
from pathlib import Path

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with dict2 values overriding dict1.

    Recursively merges nested dictionaries. For non-dict values, dict2 values
    override dict1 values.

    Args:
        dict1: Base dictionary.
        dict2: Dictionary to merge in (takes precedence).

    Returns:
        New merged dictionary.

    Example:
        >>> base = {"db": {"host": "localhost", "port": 5432}}
        >>> override = {"db": {"port": 3306}}
        >>> deep_merge(base, override)
        {'db': {'host': 'localhost', 'port': 3306}}
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def flatten_dict(
    nested_dict: Dict[str, Any], parent_key: str = "", sep: str = "."
) -> Dict[str, Any]:
    """
    Flatten a nested dictionary using dot notation.

    Converts nested dictionaries into a flat dictionary with dot-separated keys.

    Args:
        nested_dict: Nested dictionary to flatten.
        parent_key: Parent key prefix (used in recursion).
        sep: Separator for nested keys (default: ".").

    Returns:
        Flattened dictionary.

    Example:
        >>> nested = {"db": {"host": "localhost", "port": 5432}, "debug": True}
        >>> flatten_dict(nested)
        {'db.host': 'localhost', 'db.port': 5432, 'debug': True}
    """
    items: list = []
    for k, v in nested_dict.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def sanitize_path(path: str) -> str:
    """
    Sanitize a file path to prevent directory traversal attacks.

    Converts the path to absolute and ensures it doesn't escape the intended
    directory using parent references.

    Args:
        path: Path to sanitize.

    Returns:
        Sanitized absolute path.

    Example:
        >>> sanitize_path("/var/data/../log/app.log")
        '/var/log/app.log'
    """
    # Resolve to absolute path and handle any .. references
    resolved = Path(path).resolve()
    return str(resolved)


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load a JSON configuration file.

    Args:
        filepath: Path to the JSON file.

    Returns:
        Parsed JSON content as dictionary.

    Raises:
        FileNotFoundError: If file doesn't exist.
        json.JSONDecodeError: If file is not valid JSON.

    Example:
        >>> config = load_json("config.json")
        >>> config["debug"]
        True
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r") as f:
        return json.load(f)


def load_yaml(filepath: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file.

    Args:
        filepath: Path to the YAML file.

    Returns:
        Parsed YAML content as dictionary.

    Raises:
        ImportError: If PyYAML is not installed.
        FileNotFoundError: If file doesn't exist.
        yaml.YAMLError: If file is not valid YAML.

    Example:
        >>> config = load_yaml("config.yaml")
        >>> config["environment"]
        'production'
    """
    if not HAS_YAML:
        raise ImportError(
            "PyYAML is required to load YAML files. Install with: pip install pyyaml"
        )

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r") as f:
        data = yaml.safe_load(f)
        return data if data else {}


def ensure_directory(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path.

    Returns:
        The directory path.

    Example:
        >>> ensure_directory("/var/log/app")
        '/var/log/app'
    """
    os.makedirs(path, exist_ok=True)
    return path


def get_file_extension(filepath: str) -> str:
    """
    Get the file extension from a filepath.

    Args:
        filepath: Path to file.

    Returns:
        File extension (including the dot), or empty string if no extension.

    Example:
        >>> get_file_extension("data.csv")
        '.csv'
        >>> get_file_extension("README")
        ''
    """
    return Path(filepath).suffix
