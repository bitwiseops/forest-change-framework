"""
Configuration management system.

This module provides configuration loading and validation from various sources
(dict, JSON, YAML), with support for nested configurations and environment
variable expansion.
"""

from typing import Any, Dict, Optional, Union
import json
import logging
import os

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .exceptions import ConfigError

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration from multiple sources.

    The ConfigManager supports loading configuration from dictionaries, JSON files,
    and YAML files. It provides convenient access to configuration values with
    support for nested keys and environment variable expansion.

    Attributes:
        _config: The underlying configuration dictionary.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the configuration manager.

        Args:
            config: Initial configuration dictionary (default: empty dict).
        """
        self._config = config or {}
        logger.debug("ConfigManager initialized")

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "ConfigManager":
        """
        Create a ConfigManager from a dictionary.

        Args:
            config: Configuration dictionary.

        Returns:
            ConfigManager instance.

        Example:
            >>> config = ConfigManager.from_dict({"key": "value"})
        """
        return cls(config)

    @classmethod
    def from_json(cls, filepath: str) -> "ConfigManager":
        """
        Load configuration from a JSON file.

        Args:
            filepath: Path to the JSON configuration file.

        Returns:
            ConfigManager instance.

        Raises:
            ConfigError: If the file doesn't exist or is invalid JSON.

        Example:
            >>> config = ConfigManager.from_json("config.json")
        """
        if not os.path.exists(filepath):
            raise ConfigError(f"Configuration file not found: {filepath}")

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            logger.info(f"Configuration loaded from JSON: {filepath}")
            return cls(data)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file: {str(e)}")

    @classmethod
    def from_yaml(cls, filepath: str) -> "ConfigManager":
        """
        Load configuration from a YAML file.

        Args:
            filepath: Path to the YAML configuration file.

        Returns:
            ConfigManager instance.

        Raises:
            ConfigError: If YAML is not installed, file doesn't exist, or is invalid YAML.

        Example:
            >>> config = ConfigManager.from_yaml("config.yaml")
        """
        if not HAS_YAML:
            raise ConfigError(
                "PyYAML is required for YAML configuration. Install with: pip install pyyaml"
            )

        if not os.path.exists(filepath):
            raise ConfigError(f"Configuration file not found: {filepath}")

        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f) or {}
            logger.info(f"Configuration loaded from YAML: {filepath}")
            return cls(data)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in configuration file: {str(e)}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Supports nested keys using dot notation (e.g., "database.host").

        Args:
            key: Configuration key (supports dot notation for nested keys).
            default: Default value if key not found.

        Returns:
            Configuration value or default if not found.

        Example:
            >>> config = ConfigManager.from_dict({"db": {"host": "localhost"}})
            >>> config.get("db.host")
            'localhost'
            >>> config.get("db.port", 5432)
            5432
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

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value by key.

        Supports nested keys using dot notation. Creates intermediate dicts as needed.

        Args:
            key: Configuration key (supports dot notation for nested keys).
            value: The value to set.

        Example:
            >>> config = ConfigManager()
            >>> config.set("db.host", "localhost")
            >>> config.get("db.host")
            'localhost'
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        logger.debug(f"Configuration updated: {key} = {value}")

    def merge(self, other: Dict[str, Any]) -> None:
        """
        Merge another configuration dictionary into this one.

        Args:
            other: Dictionary to merge.

        Example:
            >>> config = ConfigManager.from_dict({"a": 1})
            >>> config.merge({"b": 2})
            >>> config.to_dict()
            {'a': 1, 'b': 2}
        """
        self._config = self._deep_merge(self._config, other)
        logger.debug("Configuration merged")

    def to_dict(self) -> Dict[str, Any]:
        """
        Get the entire configuration as a dictionary.

        Returns:
            Configuration dictionary.

        Example:
            >>> config = ConfigManager.from_dict({"key": "value"})
            >>> config.to_dict()
            {'key': 'value'}
        """
        return self._config.copy()

    def validate(self, schema: Dict[str, Any]) -> bool:
        """
        Validate the configuration against a schema.

        Basic validation that checks for required keys and types.

        Args:
            schema: Validation schema dictionary with required keys and types.

        Returns:
            True if valid.

        Raises:
            ConfigError: If validation fails.

        Example:
            >>> config = ConfigManager.from_dict({"host": "localhost", "port": 5432})
            >>> schema = {"host": str, "port": int}
            >>> config.validate(schema)
            True
        """
        for key, expected_type in schema.items():
            value = self.get(key)
            if value is None:
                raise ConfigError(f"Required configuration key missing: {key}")
            if not isinstance(value, expected_type):
                raise ConfigError(
                    f"Configuration key '{key}' has wrong type. "
                    f"Expected {expected_type.__name__}, got {type(value).__name__}"
                )
        return True

    @staticmethod
    def _deep_merge(
        dict1: Dict[str, Any], dict2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with dict2 values overriding dict1.

        Args:
            dict1: Base dictionary.
            dict2: Dictionary to merge in.

        Returns:
            Merged dictionary.
        """
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
