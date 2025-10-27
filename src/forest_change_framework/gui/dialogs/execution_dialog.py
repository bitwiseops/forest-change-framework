"""Execution progress dialog with real-time logging.

Shows component execution progress, logs, and provides cancellation controls.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..executors import ComponentExecutor
from ..widgets.log_viewer import LogViewer


class ExecutionDialog(QDialog):
    """Dialog showing component execution progress and logs."""

    # Signals
    execution_completed = pyqtSignal(dict)  # result
    execution_cancelled = pyqtSignal()

    def __init__(
        self,
        component_name: str,
        component_category: str,
        config: dict,
        output_base_dir: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize execution dialog.

        Args:
            component_name: Name of component to execute
            component_category: Category of component
            config: Component configuration
            output_base_dir: Base directory for outputs
            parent: Parent widget
        """
        super().__init__(parent)
        self.component_name = component_name
        self.component_category = component_category
        self.config = config
        self.output_base_dir = output_base_dir

        self.executor = ComponentExecutor(output_base_dir)
        self._setup_ui()
        self.setWindowTitle(f"Executing {component_name}")
        self.resize(600, 500)

        # Start execution
        self._start_execution()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"Executing: {self.component_name}")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Status label
        self.status_label = QLabel("Starting component...")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        # Log viewer
        log_label = QLabel("Execution Log:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(log_label)

        self.log_viewer = LogViewer()
        self.log_viewer.log_info(
            f"Starting execution of {self.component_name} ({self.component_category})"
        )
        layout.addWidget(self.log_viewer)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _start_execution(self) -> None:
        """Start component execution."""
        # Connect executor signals
        self.executor.execution_started.connect(self._on_execution_started)
        self.executor.progress_updated.connect(self._on_progress_updated)
        self.executor.execution_completed.connect(self._on_execution_completed)
        self.executor.execution_failed.connect(self._on_execution_failed)
        self.executor.execution_finished.connect(self._on_execution_finished)

        # Start execution
        self.executor.execute(
            self.component_category,
            self.component_name,
            self.config,
        )

    def _on_execution_started(self, category: str, name: str) -> None:
        """Handle execution start."""
        self.status_label.setText(f"Status: Running {name}...")
        self.log_viewer.log_info(f"Component execution started")

    def _on_progress_updated(self, message: str) -> None:
        """Handle progress update."""
        self.status_label.setText(f"Status: {message}")
        self.log_viewer.log_info(message, timestamp=False)

    def _on_execution_completed(self, result: dict) -> None:
        """Handle successful execution."""
        self.status_label.setText("Status: Completed successfully")
        self.log_viewer.log_info("Component execution completed successfully")
        self.execution_completed.emit(result)

    def _on_execution_failed(self, error_msg: str) -> None:
        """Handle execution error."""
        self.status_label.setText("Status: Failed")
        self.log_viewer.log_error(error_msg)
        self.log_viewer.log_error("Component execution failed")

    def _on_execution_finished(self) -> None:
        """Handle execution finish (cleanup)."""
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.executor.stop()
        self.log_viewer.log_warning("Execution cancelled by user")
        self.status_label.setText("Status: Cancelled")
        self.cancel_btn.setEnabled(False)
        self.execution_cancelled.emit()


class ProgressDialog(QDialog):
    """Simple progress dialog with indeterminate progress bar."""

    def __init__(
        self,
        title: str = "Processing",
        message: str = "Please wait...",
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize progress dialog.

        Args:
            title: Dialog title
            message: Status message
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(400, 120)

        layout = QVBoxLayout(self)

        # Message
        self.message_label = QLabel(message)
        layout.addWidget(self.message_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def set_message(self, message: str) -> None:
        """Update progress message."""
        self.message_label.setText(message)

    def set_progress(self, value: int, maximum: int = 100) -> None:
        """
        Set progress value.

        Args:
            value: Current progress
            maximum: Maximum progress
        """
        if self.progress_bar.maximum() != maximum:
            self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
