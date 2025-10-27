"""Theme management for light and dark mode support."""

import logging
from typing import Literal

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class ThemeManager:
    """Manages application themes (light and dark modes)."""

    THEMES = {
        "light": {
            "primary": "#2196F3",
            "primary_dark": "#1976D2",
            "accent": "#FF5722",
            "background": "#FAFAFA",
            "surface": "#FFFFFF",
            "text_primary": "#212121",
            "text_secondary": "#757575",
            "border": "#BDBDBD",
        },
        "dark": {
            "primary": "#1976D2",
            "primary_dark": "#1565C0",
            "accent": "#FF5722",
            "background": "#121212",
            "surface": "#1E1E1E",
            "text_primary": "#FFFFFF",
            "text_secondary": "#B0BEC5",
            "border": "#424242",
        },
    }

    def __init__(self, app: QApplication):
        """Initialize theme manager.

        Args:
            app: QApplication instance
        """
        self.app = app
        self.current_theme = "dark"

    def set_theme(self, theme: Literal["light", "dark"]) -> None:
        """Set application theme.

        Args:
            theme: Theme name ("light" or "dark")
        """
        if theme not in self.THEMES:
            logger.warning(f"Unknown theme: {theme}, using dark")
            theme = "dark"

        self.current_theme = theme
        colors = self.THEMES[theme]

        # Create palette
        palette = QPalette()

        # Set colors based on theme
        bg_color = QColor(colors["background"])
        surface_color = QColor(colors["surface"])
        text_color = QColor(colors["text_primary"])
        text_secondary = QColor(colors["text_secondary"])
        border_color = QColor(colors["border"])

        # Window/Background
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        palette.setColor(QPalette.ColorRole.Base, surface_color)
        palette.setColor(QPalette.ColorRole.AlternateBase, border_color)

        # Text
        palette.setColor(QPalette.ColorRole.Text, text_color)
        palette.setColor(QPalette.ColorRole.PlaceholderText, text_secondary)

        # Button
        palette.setColor(QPalette.ColorRole.Button, surface_color)
        palette.setColor(QPalette.ColorRole.ButtonText, text_color)

        # Input fields
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["primary"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["text_primary"]))

        # Other elements
        palette.setColor(QPalette.ColorRole.Link, QColor(colors["primary"]))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors["primary_dark"]))

        # Apply palette
        self.app.setPalette(palette)

        # Set stylesheet for additional styling
        self._apply_stylesheet(theme, colors)

        logger.info(f"Theme changed to: {theme}")

    def _apply_stylesheet(self, theme: str, colors: dict) -> None:
        """Apply stylesheet for consistent styling across all widgets.

        Args:
            theme: Theme name
            colors: Color dictionary
        """
        stylesheet = f"""
        QMainWindow {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
        }}

        QWidget {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
        }}

        QMenuBar {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border-bottom: 1px solid {colors['border']};
        }}

        QMenuBar::item:selected {{
            background-color: {colors['primary']};
        }}

        QMenu {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
        }}

        QMenu::item:selected {{
            background-color: {colors['primary']};
            color: white;
        }}

        QPushButton {{
            background-color: {colors['primary']};
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: {colors['primary_dark']};
        }}

        QPushButton:pressed {{
            background-color: {colors['primary_dark']};
        }}

        QPushButton:disabled {{
            background-color: {colors['border']};
            color: {colors['text_secondary']};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 3px;
            padding: 5px;
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {colors['primary']};
        }}

        QComboBox {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 3px;
            padding: 5px;
        }}

        QComboBox:hover {{
            border: 1px solid {colors['primary']};
        }}

        QComboBox::drop-down {{
            border: none;
        }}

        QTreeWidget, QListWidget {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            gridline-color: {colors['border']};
        }}

        QTreeWidget::item:selected, QListWidget::item:selected {{
            background-color: {colors['primary']};
            color: white;
        }}

        QHeaderView::section {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            padding: 5px;
            border: 1px solid {colors['border']};
        }}

        QTabBar::tab {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            padding: 8px 20px;
            border: 1px solid {colors['border']};
        }}

        QTabBar::tab:selected {{
            background-color: {colors['primary']};
            color: white;
            border-bottom: 2px solid {colors['accent']};
        }}

        QProgressBar {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 3px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {colors['primary']};
            border-radius: 2px;
        }}

        QScrollBar:vertical {{
            background-color: {colors['surface']};
            width: 12px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {colors['border']};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {colors['text_secondary']};
        }}

        QStatusBar {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border-top: 1px solid {colors['border']};
        }}

        QLabel {{
            color: {colors['text_primary']};
        }}
        """

        self.app.setStyleSheet(stylesheet)

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.set_theme(new_theme)

    def get_color(self, name: str) -> QColor:
        """Get a color from current theme.

        Args:
            name: Color name (e.g., 'primary', 'surface')

        Returns:
            QColor object
        """
        colors = self.THEMES[self.current_theme]
        if name in colors:
            return QColor(colors[name])
        return QColor(colors["primary"])  # Default to primary
