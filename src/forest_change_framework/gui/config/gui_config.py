"""GUI Configuration management - persists user preferences."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GUIConfig:
    """Manages GUI configuration and preferences.

    Stores:
    - Theme preference
    - Window size and position
    - Recent files
    - Panel visibility
    - Column widths
    """

    DEFAULT_CONFIG = {
        "theme": "dark",
        "window": {
            "width": 1400,
            "height": 900,
            "x": 100,
            "y": 100,
            "maximized": False,
        },
        "panels": {
            "left_panel_width": 250,
            "show_log": True,
        },
        "recent_files": [],
        "auto_save_interval": 30,  # seconds
    }

    def __init__(self):
        """Initialize configuration."""
        self.config_dir = Path.home() / ".forest_change_framework"
        self.config_file = self.config_dir / "gui_config.json"
        self.data: Dict[str, Any] = self.DEFAULT_CONFIG.copy()

    def load(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    saved_config = json.load(f)
                    # Merge with defaults (in case new keys were added)
                    self._deep_merge(self.data, saved_config)
                logger.info(f"Loaded GUI config from {self.config_file}")
            else:
                logger.info("No existing config found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")

    def save(self) -> None:
        """Save configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.data, f, indent=2)
            logger.info(f"Saved GUI config to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation.

        Args:
            key: Configuration key (e.g., 'window.width' or 'theme')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value with dot notation.

        Args:
            key: Configuration key (e.g., 'window.width' or 'theme')
            value: Value to set
        """
        keys = key.split(".")

        # Navigate to parent
        config = self.data
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]

        # Set value
        config[keys[-1]] = value

    @property
    def theme(self) -> str:
        """Get current theme."""
        return self.get("theme", "dark")

    @theme.setter
    def theme(self, value: str) -> None:
        """Set theme."""
        self.set("theme", value)

    @property
    def window_width(self) -> int:
        """Get window width."""
        return self.get("window.width", 1400)

    @window_width.setter
    def window_width(self, value: int) -> None:
        """Set window width."""
        self.set("window.width", value)

    @property
    def window_height(self) -> int:
        """Get window height."""
        return self.get("window.height", 900)

    @window_height.setter
    def window_height(self, value: int) -> None:
        """Set window height."""
        self.set("window.height", value)

    @property
    def window_x(self) -> int:
        """Get window x position."""
        return self.get("window.x", 100)

    @window_x.setter
    def window_x(self, value: int) -> None:
        """Set window x position."""
        self.set("window.x", value)

    @property
    def window_y(self) -> int:
        """Get window y position."""
        return self.get("window.y", 100)

    @window_y.setter
    def window_y(self, value: int) -> None:
        """Set window y position."""
        self.set("window.y", value)

    @property
    def window_maximized(self) -> bool:
        """Get window maximized state."""
        return self.get("window.maximized", False)

    @window_maximized.setter
    def window_maximized(self, value: bool) -> None:
        """Set window maximized state."""
        self.set("window.maximized", value)

    @property
    def left_panel_width(self) -> int:
        """Get left panel width."""
        return self.get("panels.left_panel_width", 250)

    @left_panel_width.setter
    def left_panel_width(self, value: int) -> None:
        """Set left panel width."""
        self.set("panels.left_panel_width", value)

    def add_recent_file(self, filepath: str) -> None:
        """Add file to recent files list.

        Args:
            filepath: Path to file
        """
        recent = self.get("recent_files", [])
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        # Keep only last 10
        recent = recent[:10]
        self.set("recent_files", recent)

    def get_recent_files(self) -> list:
        """Get recent files list.

        Returns:
            List of recent file paths
        """
        return self.get("recent_files", [])

    def _deep_merge(self, target: dict, source: dict) -> None:
        """Deep merge source dict into target dict.

        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
