"""Main application window for Forest Change Framework GUI."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenu, QMenuBar, QToolBar, QTextEdit
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from .config.gui_config import GUIConfig
from .panels.component_panel import ComponentPanel
from .utils import create_icon

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window.

    Layout:
    ┌─────────────────────────────┐
    │ Menu Bar                    │
    ├──────────┬──────────────────┤
    │ Toolbar  │                  │
    ├──────────┤                  │
    │ Left     │  Main Content    │
    │ Panel    │  (Component      │
    │          │   Config)        │
    ├──────────┴──────────────────┤
    │ Status Bar (Logs, Progress) │
    └─────────────────────────────┘
    """

    # Signals
    component_executed = pyqtSignal(str)  # component_name
    workflow_loaded = pyqtSignal(str)    # workflow_path
    results_updated = pyqtSignal(str)    # results_dir

    def __init__(self, config: GUIConfig):
        """Initialize main window.

        Args:
            config: GUI configuration
        """
        super().__init__()

        self.config = config
        self.setWindowTitle("Forest Change Framework")
        self.setWindowIcon(create_icon("app"))

        # Restore window state
        self._restore_window_state()

        # Create UI
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

        logger.info("Main window created")

    def _restore_window_state(self) -> None:
        """Restore window size, position, and state."""
        self.move(self.config.window_x, self.config.window_y)
        self.resize(self.config.window_width, self.config.window_height)

        if self.config.window_maximized:
            self.showMaximized()

    def _create_menu_bar(self) -> None:
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_workflow = QAction("&New Workflow", self)
        new_workflow.triggered.connect(self._new_workflow)
        file_menu.addAction(new_workflow)

        open_workflow = QAction("&Open Workflow", self)
        open_workflow.triggered.connect(self._open_workflow)
        file_menu.addAction(open_workflow)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        toggle_theme = QAction("Toggle &Theme", self)
        toggle_theme.setShortcut("Ctrl+T")
        toggle_theme.triggered.connect(self._toggle_theme)
        view_menu.addAction(toggle_theme)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        clear_cache = QAction("Clear &Cache", self)
        clear_cache.triggered.connect(self._clear_cache)
        tools_menu.addAction(clear_cache)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about = QAction("&About", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _create_toolbar(self) -> None:
        """Create application toolbar."""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))

        # New workflow
        new_action = QAction(create_icon("new"), "New Workflow", self)
        new_action.triggered.connect(self._new_workflow)
        toolbar.addAction(new_action)

        # Open workflow
        open_action = QAction(create_icon("open"), "Open Workflow", self)
        open_action.triggered.connect(self._open_workflow)
        toolbar.addAction(open_action)

        # Save
        save_action = QAction(create_icon("save"), "Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_workflow)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Run
        run_action = QAction(create_icon("play"), "Run Component", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self._run_component)
        toolbar.addAction(run_action)

        # Stop
        stop_action = QAction(create_icon("stop"), "Stop Execution", self)
        stop_action.triggered.connect(self._stop_execution)
        toolbar.addAction(stop_action)

    def _create_central_widget(self) -> None:
        """Create central widget with panels."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Components
        self.component_panel = ComponentPanel()
        splitter.addWidget(self.component_panel)

        # Right panel - Main content (placeholder for now)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self._create_placeholder())
        splitter.addWidget(right_panel)

        # Set initial sizes
        splitter.setSizes([
            self.config.left_panel_width,
            800 - self.config.left_panel_width
        ])

        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)

    def _create_placeholder(self) -> QWidget:
        """Create placeholder for main content.

        Returns:
            QWidget
        """
        placeholder = QTextEdit()
        placeholder.setPlainText(
            "Forest Change Framework\n"
            "========================\n\n"
            "Select a component from the left panel to begin.\n\n"
            "This is the main content area where you will:\n"
            "- Configure components\n"
            "- View component output\n"
            "- Visualize results on maps\n"
            "- Analyze statistics"
        )
        placeholder.setReadOnly(True)
        return placeholder

    def _create_status_bar(self) -> None:
        """Create status bar."""
        status_bar = self.statusBar()
        status_bar.setStyleSheet("QStatusBar { border-top: 1px solid #424242; }")
        status_bar.showMessage("Ready")

    def _new_workflow(self) -> None:
        """Create new workflow."""
        logger.info("New workflow requested")
        # TODO: Implement workflow creation dialog

    def _open_workflow(self) -> None:
        """Open existing workflow."""
        logger.info("Open workflow requested")
        # TODO: Implement workflow open dialog

    def _save_workflow(self) -> None:
        """Save current workflow."""
        logger.info("Save workflow requested")
        # TODO: Implement workflow save

    def _run_component(self) -> None:
        """Run selected component."""
        logger.info("Run component requested")
        # TODO: Implement component execution

    def _stop_execution(self) -> None:
        """Stop running execution."""
        logger.info("Stop execution requested")
        # TODO: Implement stop execution

    def _toggle_theme(self) -> None:
        """Toggle between light and dark theme."""
        from .app import QApplication
        app = QApplication.instance()
        if app and hasattr(app, 'theme_manager'):
            app.theme_manager.toggle_theme()
            self.config.theme = app.theme_manager.current_theme

    def _clear_cache(self) -> None:
        """Clear application cache."""
        logger.info("Clear cache requested")
        # TODO: Implement cache clearing

    def _show_about(self) -> None:
        """Show about dialog."""
        logger.info("About dialog requested")
        # TODO: Implement about dialog

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event
        """
        # Save window state
        if not self.isMaximized():
            self.config.window_x = self.x()
            self.config.window_y = self.y()
            self.config.window_width = self.width()
            self.config.window_height = self.height()
        self.config.window_maximized = self.isMaximized()

        logger.info("Main window closed")
        super().closeEvent(event)
