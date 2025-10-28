"""Utility functions for GUI."""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import QMessageBox, QApplication, QStyle

logger = logging.getLogger(__name__)


def create_icon(name: str, size: int = 24, color: Optional[QColor] = None) -> QIcon:
    """Create an icon from resources or standard application icons.

    Args:
        name: Icon name (without extension)
        size: Icon size in pixels
        color: Optional color override

    Returns:
        QIcon object
    """
    # Try to load from resources first
    icon_path = Path(__file__).parent / "resources" / "icons" / f"{name}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))

    # Map icon names to standard application icons
    icon_map = {
        "new": QStyle.StandardPixmap.SP_FileDialogDetailedView,
        "open": QStyle.StandardPixmap.SP_DialogOpenButton,
        "save": QStyle.StandardPixmap.SP_DialogSaveButton,
        "play": QStyle.StandardPixmap.SP_MediaPlay,
        "stop": QStyle.StandardPixmap.SP_MediaStop,
        "delete": QStyle.StandardPixmap.SP_TrashIcon,
        "refresh": QStyle.StandardPixmap.SP_BrowserReload,
        "config": QStyle.StandardPixmap.SP_FileDialogDetailedView,
        "settings": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    }

    # Use standard application icon if available
    if name in icon_map and QApplication.instance():
        try:
            return QApplication.style().standardIcon(icon_map[name])
        except Exception:
            pass

    # Fallback: Return placeholder icon
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(128, 128, 128) if color is None else color)
    return QIcon(pixmap)


def show_error(title: str, message: str, parent=None) -> None:
    """Show error message dialog.

    Args:
        title: Dialog title
        message: Error message
        parent: Parent widget
    """
    logger.error(f"{title}: {message}")
    QMessageBox.critical(parent, title, message)


def show_warning(title: str, message: str, parent=None) -> None:
    """Show warning message dialog.

    Args:
        title: Dialog title
        message: Warning message
        parent: Parent widget
    """
    logger.warning(f"{title}: {message}")
    QMessageBox.warning(parent, title, message)


def show_info(title: str, message: str, parent=None) -> None:
    """Show info message dialog.

    Args:
        title: Dialog title
        message: Info message
        parent: Parent widget
    """
    logger.info(f"{title}: {message}")
    QMessageBox.information(parent, title, message)


def ask_yes_no(title: str, message: str, parent=None) -> bool:
    """Ask yes/no question.

    Args:
        title: Dialog title
        message: Question message
        parent: Parent widget

    Returns:
        True if user clicked Yes, False otherwise
    """
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes


def format_size(size_bytes: int) -> str:
    """Format byte size to human readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_number(num: float, decimals: int = 2) -> str:
    """Format number with thousand separators.

    Args:
        num: Number to format
        decimals: Number of decimal places

    Returns:
        Formatted number string
    """
    return f"{num:,.{decimals}f}"


def truncate_string(text: str, length: int = 50) -> str:
    """Truncate string to specified length.

    Args:
        text: Text to truncate
        length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) > length:
        return text[:length-3] + "..."
    return text


def get_app_data_dir() -> Path:
    """Get application data directory.

    Returns:
        Path to app data directory (~/.forest_change_framework)
    """
    app_dir = Path.home() / ".forest_change_framework"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_project_root() -> Path:
    """Get project root directory.

    Returns:
        Path to project root
    """
    return Path(__file__).parent.parent.parent.parent
