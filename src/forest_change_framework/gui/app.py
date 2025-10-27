"""Forest Change Framework GUI Application - Main entry point."""

import sys
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer

from .main_window import MainWindow
from .theme import ThemeManager
from .config.gui_config import GUIConfig

logger = logging.getLogger(__name__)


class ForestChangeApp(QApplication):
    """Main application class for Forest Change Framework GUI.

    Handles:
    - Application initialization
    - Theme management
    - Configuration persistence
    - Main window creation
    """

    def __init__(
        self,
        argv: Optional[list] = None,
        theme: Optional[str] = None,
        debug: bool = False,
    ):
        """Initialize the application.

        Args:
            argv: Command line arguments (uses sys.argv if None)
            theme: Theme to use ("light" or "dark"), overrides config
            debug: Enable debug logging
        """
        if argv is None:
            argv = sys.argv

        super().__init__(argv)

        # Configure application
        self.setApplicationName("Forest Change Framework")
        self.setApplicationVersion("1.0.0")
        self.setApplicationAuthor("Forest Change Framework Team")

        # Enable debug logging if requested
        if debug:
            logging.getLogger("forest_change_framework").setLevel(logging.DEBUG)

        # Load configuration
        self.config = GUIConfig()
        self.config.load()

        # Override theme if provided
        if theme:
            self.config.set("theme", theme)

        # Initialize theme manager
        self.theme_manager = ThemeManager(self)
        self.theme_manager.set_theme(self.config.theme)

        # Create main window (will be shown by run())
        self.main_window: Optional[MainWindow] = None

        logger.info("Forest Change Framework GUI initialized")

    def run(self) -> int:
        """Run the application.

        Returns:
            Exit code
        """
        # Create splash screen (optional)
        # self._show_splash()

        # Create and show main window
        self.main_window = MainWindow(self.config)
        self.main_window.show()

        logger.info("Main window displayed")

        return self.exec()

    def _show_splash(self, duration_ms: int = 2000) -> None:
        """Show splash screen on startup.

        Args:
            duration_ms: How long to show splash screen
        """
        try:
            splash_path = Path(__file__).parent / "resources" / "splash.png"
            if splash_path.exists():
                splash_pixmap = QPixmap(str(splash_path))
                splash = QSplashScreen(splash_pixmap)
                splash.show()

                # Auto-close splash after duration
                QTimer.singleShot(duration_ms, splash.close)
                self.processEvents()
        except Exception as e:
            logger.warning(f"Could not display splash screen: {e}")

    def closeEvent(self, event) -> None:
        """Handle application close event.

        Args:
            event: Close event
        """
        if self.main_window:
            self.main_window.closeEvent(event)

        # Save configuration
        if hasattr(self, 'config'):
            self.config.save()

        logger.info("Forest Change Framework GUI closed")
        super().closeEvent(event)


def main():
    """Entry point for the application."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Forest Change Framework - Professional GUI for Forest Loss Analysis"
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        default="dark",
        help="Application theme"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run application
    app = ForestChangeApp()
    if args.theme:
        app.config.theme = args.theme

    exit_code = app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
