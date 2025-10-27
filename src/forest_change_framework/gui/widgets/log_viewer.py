"""Log viewer widget for displaying execution logs.

Provides a read-only text display with colored log levels and timestamp support.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtWidgets import QTextEdit, QWidget


class LogViewer(QTextEdit):
    """Text widget for displaying execution logs with color coding."""

    # Color scheme for log levels
    LOG_COLORS = {
        "DEBUG": QColor(128, 128, 128),  # Gray
        "INFO": QColor(0, 0, 0),  # Black
        "WARNING": QColor(255, 165, 0),  # Orange
        "ERROR": QColor(255, 0, 0),  # Red
        "CRITICAL": QColor(139, 0, 0),  # Dark red
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize log viewer.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier", 10))
        self._max_lines = 1000  # Limit log size
        self._line_count = 0

    def log(
        self,
        message: str,
        level: str = "INFO",
        timestamp: bool = True,
    ) -> None:
        """
        Add a log message.

        Args:
            message: Log message text
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            timestamp: Whether to include timestamp
        """
        # Format message
        if timestamp:
            ts = datetime.now().strftime("%H:%M:%S")
            formatted = f"[{ts}] [{level:8s}] {message}"
        else:
            formatted = f"[{level:8s}] {message}"

        # Get color for log level
        color = self.LOG_COLORS.get(level, QColor(0, 0, 0))

        # Move cursor to end
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

        # Insert formatted text
        self.setTextColor(color)
        self.append(formatted)

        # Track line count
        self._line_count += 1

        # Trim if too many lines
        if self._line_count > self._max_lines:
            self._trim_lines()

    def log_info(self, message: str, timestamp: bool = True) -> None:
        """Log info message."""
        self.log(message, "INFO", timestamp)

    def log_warning(self, message: str, timestamp: bool = True) -> None:
        """Log warning message."""
        self.log(message, "WARNING", timestamp)

    def log_error(self, message: str, timestamp: bool = True) -> None:
        """Log error message."""
        self.log(message, "ERROR", timestamp)

    def log_debug(self, message: str, timestamp: bool = True) -> None:
        """Log debug message."""
        self.log(message, "DEBUG", timestamp)

    def clear_log(self) -> None:
        """Clear all log messages."""
        self.clear()
        self._line_count = 0

    def _trim_lines(self, keep_lines: int = 500) -> None:
        """Trim log to keep only recent lines.

        Args:
            keep_lines: Number of lines to keep
        """
        doc = self.document()
        block = doc.findBlockByLineNumber(self._line_count - keep_lines)

        if block.isValid():
            cursor = self.textCursor()
            cursor.setPosition(block.position())
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.movePosition(
                QTextCursor.MoveOperation.StartOfBlock,
                QTextCursor.MoveSelectionMode.KeepAnchor,
            )
            cursor.removeSelectedText()

        self._line_count = keep_lines
