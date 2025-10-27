"""GUI Dialogs module.

Dialog windows for configuration, file operations, and user interactions.
"""

from .config_dialog import (
    ComponentConfigDialog,
    QuickConfigDialog,
    show_config_dialog,
)

__all__ = [
    "ComponentConfigDialog",
    "QuickConfigDialog",
    "show_config_dialog",
]
