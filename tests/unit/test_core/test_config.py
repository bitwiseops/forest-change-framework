"""
Unit tests for ConfigManager.

Tests configuration loading, management, and validation.
"""

import pytest
import json
import tempfile
from pathlib import Path

from forest_change_framework.core import ConfigManager, ConfigError, ValidationError


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_from_dict(self, sample_config):
        """Test creating ConfigManager from dictionary."""
        manager = ConfigManager.from_dict(sample_config)
        assert manager.to_dict() == sample_config

    def test_from_json(self, temp_json_config, sample_config):
        """Test loading ConfigManager from JSON file."""
        manager = ConfigManager.from_json(temp_json_config)
        assert manager.to_dict() == sample_config

    def test_from_json_nonexistent_file_raises_error(self):
        """Test loading from nonexistent JSON file raises error."""
        with pytest.raises(ConfigError):
            ConfigManager.from_json("/nonexistent/file.json")

    def test_from_json_invalid_json_raises_error(self, tmp_path):
        """Test loading invalid JSON raises error."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{invalid json")

        with pytest.raises(ConfigError):
            ConfigManager.from_json(str(bad_json))

    def test_from_yaml(self, temp_yaml_config, sample_config):
        """Test loading ConfigManager from YAML file."""
        manager = ConfigManager.from_yaml(temp_yaml_config)
        assert manager.to_dict() == sample_config

    def test_from_yaml_without_pyyaml_raises_error(self, monkeypatch):
        """Test loading YAML without PyYAML raises error."""
        # Temporarily make HAS_YAML false
        import forest_change_framework.core.config
        original = forest_change_framework.core.config.HAS_YAML
        forest_change_framework.core.config.HAS_YAML = False

        try:
            with pytest.raises(ConfigError):
                ConfigManager.from_yaml("config.yaml")
        finally:
            forest_change_framework.core.config.HAS_YAML = original

    def test_get_with_dot_notation(self, sample_config):
        """Test getting values with dot notation."""
        manager = ConfigManager.from_dict(sample_config)

        assert manager.get("database.host") == "localhost"
        assert manager.get("database.port") == 5432
        assert manager.get("processing.threshold") == 0.7

    def test_get_with_default(self, sample_config):
        """Test get with default value."""
        manager = ConfigManager.from_dict(sample_config)

        assert manager.get("nonexistent.key", "default_value") == "default_value"

    def test_get_nonexistent_returns_default(self, sample_config):
        """Test get nonexistent key returns default."""
        manager = ConfigManager.from_dict(sample_config)

        result = manager.get("does.not.exist", "fallback")
        assert result == "fallback"

    def test_set_with_dot_notation(self):
        """Test setting values with dot notation."""
        manager = ConfigManager()

        manager.set("database.host", "example.com")
        manager.set("database.port", 3306)

        assert manager.get("database.host") == "example.com"
        assert manager.get("database.port") == 3306

    def test_set_creates_nested_structure(self):
        """Test set creates nested structure."""
        manager = ConfigManager()

        manager.set("deep.nested.value", 42)

        config = manager.to_dict()
        assert config["deep"]["nested"]["value"] == 42

    def test_merge_configs(self, sample_config):
        """Test merging configurations."""
        manager = ConfigManager.from_dict({"a": 1, "b": {"c": 2}})

        manager.merge({"b": {"d": 3}, "e": 4})

        config = manager.to_dict()
        assert config["a"] == 1
        assert config["b"]["c"] == 2
        assert config["b"]["d"] == 3
        assert config["e"] == 4

    def test_merge_deep_override(self):
        """Test deep merging with override."""
        manager = ConfigManager.from_dict({
            "db": {"host": "localhost", "port": 5432}
        })

        manager.merge({"db": {"port": 3306}})

        config = manager.to_dict()
        assert config["db"]["host"] == "localhost"
        assert config["db"]["port"] == 3306

    def test_to_dict(self, sample_config):
        """Test getting configuration as dictionary."""
        manager = ConfigManager.from_dict(sample_config)
        result = manager.to_dict()

        assert result == sample_config

    def test_validate_success(self, sample_config):
        """Test validation succeeds with valid config."""
        manager = ConfigManager.from_dict(sample_config)

        schema = {
            "database": dict,
            "processing": dict,
            "output": dict,
        }

        result = manager.validate(schema)
        assert result is True

    def test_validate_missing_required_key(self, sample_config):
        """Test validation fails with missing required key."""
        manager = ConfigManager.from_dict(sample_config)

        schema = {
            "database": dict,
            "required_key": str,
        }

        with pytest.raises(ConfigError):
            manager.validate(schema)

    def test_validate_wrong_type(self, sample_config):
        """Test validation fails with wrong type."""
        manager = ConfigManager.from_dict(sample_config)

        schema = {
            "database": str,  # Should be dict
        }

        with pytest.raises(ConfigError):
            manager.validate(schema)

    def test_validate_optional_key_with_question_mark(self, sample_config):
        """Test validation with optional keys (? suffix)."""
        manager = ConfigManager.from_dict(sample_config)

        schema = {
            "database": dict,
            "optional_key?": str,  # Optional
        }

        # Should not raise
        result = manager.validate(schema)
        assert result is True

    def test_empty_config(self):
        """Test working with empty configuration."""
        manager = ConfigManager()

        assert manager.to_dict() == {}
        assert manager.get("any.key") is None

    def test_config_copy_is_independent(self, sample_config):
        """Test that to_dict returns independent copy."""
        manager = ConfigManager.from_dict(sample_config)
        config_copy = manager.to_dict()

        config_copy["new_key"] = "new_value"

        assert "new_key" not in manager.to_dict()
