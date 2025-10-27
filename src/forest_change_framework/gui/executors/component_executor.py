"""Component executor with threading support.

This module provides background execution of components with progress tracking,
logging, and cancellation support using Qt threads.
"""

import logging
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from forest_change_framework.core import BaseFramework
from forest_change_framework.core.registry import ComponentRegistry

logger = logging.getLogger(__name__)


class ExecutionWorker(QObject):
    """Worker object that runs component execution in a thread.

    Signals:
        started: Emitted when execution begins
        progress: Emitted during execution with progress info
        completed: Emitted when execution finishes successfully
        error: Emitted when execution fails
        finished: Emitted when thread finishes (cleanup signal)
    """

    # Signals
    started = pyqtSignal(str, str)  # category, component_name
    progress = pyqtSignal(str)  # progress_message
    completed = pyqtSignal(dict)  # result
    error = pyqtSignal(str, str)  # error_message, traceback
    finished = pyqtSignal()

    def __init__(self) -> None:
        """Initialize worker."""
        super().__init__()
        self.is_running = True
        self.registry = ComponentRegistry()

    def execute_component(
        self,
        category: str,
        component_name: str,
        config: Dict[str, Any],
        output_base_dir: Optional[str] = None,
    ) -> None:
        """
        Execute a component with given configuration.

        Args:
            category: Component category
            component_name: Component name
            config: Configuration dictionary
            output_base_dir: Base directory for component output
        """
        try:
            self.started.emit(category, component_name)

            # Create framework
            framework = BaseFramework(output_base_dir=output_base_dir or "./data")

            # Get component class
            comp_class = self.registry.get_component(category, component_name)
            if not comp_class:
                raise ValueError(
                    f"Component not found: {category}/{component_name}"
                )

            self.progress.emit(f"Initializing {component_name}...")

            # Create component instance
            component = comp_class(
                event_bus=framework.event_bus,
                config=config,
            )

            # Subscribe to component events
            def on_progress(event_data: Dict[str, Any]) -> None:
                if self.is_running:
                    message = event_data.get("message", "Processing...")
                    progress_pct = event_data.get("progress", 0)
                    if progress_pct:
                        msg = f"{message} ({progress_pct}%)"
                    else:
                        msg = message
                    self.progress.emit(msg)

            framework.subscribe_event(f"{component_name}.progress", on_progress)

            # Initialize component
            self.progress.emit(f"Configuring {component_name}...")
            component.initialize(config)

            if not self.is_running:
                return

            # Execute component
            self.progress.emit(f"Running {component_name}...")
            result = component.execute()

            if not self.is_running:
                return

            # Cleanup
            self.progress.emit(f"Cleaning up {component_name}...")
            component.cleanup()

            # Emit success
            self.progress.emit(f"{component_name} completed successfully")
            self.completed.emit({
                "component": component_name,
                "category": category,
                "status": "success",
                "result": result,
            })

        except Exception as e:
            if not self.is_running:
                return

            error_msg = f"Failed to execute {component_name}: {str(e)}"
            error_traceback = traceback.format_exc()
            logger.error(error_msg)
            logger.error(error_traceback)

            self.error.emit(error_msg, error_traceback)

        finally:
            self.finished.emit()

    def stop(self) -> None:
        """Request execution to stop."""
        self.is_running = False


class ComponentExecutor(QObject):
    """High-level component executor with threading.

    Manages background execution of components and emits signals for GUI updates.

    Signals:
        execution_started: Emitted when execution begins
        progress_updated: Emitted during execution
        execution_completed: Emitted when execution finishes
        execution_failed: Emitted when execution fails
    """

    # Signals
    execution_started = pyqtSignal(str, str)  # category, component_name
    progress_updated = pyqtSignal(str)  # progress_message
    execution_completed = pyqtSignal(dict)  # result
    execution_failed = pyqtSignal(str)  # error_message
    execution_finished = pyqtSignal()  # cleanup signal

    def __init__(self, output_base_dir: Optional[str] = None) -> None:
        """
        Initialize component executor.

        Args:
            output_base_dir: Base directory for component outputs
        """
        super().__init__()
        self.output_base_dir = output_base_dir or "./data"
        self._thread: Optional[QThread] = None
        self._worker: Optional[ExecutionWorker] = None
        self._is_executing = False

    def execute(
        self,
        category: str,
        component_name: str,
        config: Dict[str, Any],
    ) -> bool:
        """
        Execute a component in background.

        Args:
            category: Component category
            component_name: Component name
            config: Configuration dictionary

        Returns:
            True if execution started, False if already executing
        """
        if self._is_executing:
            logger.warning("Execution already in progress")
            return False

        self._is_executing = True

        # Create worker and thread
        self._worker = ExecutionWorker()
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._thread.started.connect(
            lambda: self._worker.execute_component(
                category, component_name, config, self.output_base_dir
            )
        )
        self._worker.started.connect(self.execution_started)
        self._worker.progress.connect(self.progress_updated)
        self._worker.completed.connect(self._on_execution_completed)
        self._worker.error.connect(self._on_execution_error)
        self._worker.finished.connect(self._on_execution_finished)

        # Start thread
        self._thread.start()
        logger.info(f"Started execution: {category}/{component_name}")

        return True

    def _on_execution_completed(self, result: Dict[str, Any]) -> None:
        """Handle successful execution."""
        self.execution_completed.emit(result)

    def _on_execution_error(self, error_msg: str, error_traceback: str) -> None:
        """Handle execution error."""
        self.execution_failed.emit(error_msg)

    def _on_execution_finished(self) -> None:
        """Handle execution finish (cleanup)."""
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        self._worker = None
        self._is_executing = False
        self.execution_finished.emit()

    def stop(self) -> None:
        """Stop current execution."""
        if self._worker:
            self._worker.stop()
            logger.info("Execution stop requested")

    def is_executing(self) -> bool:
        """Check if execution is in progress."""
        return self._is_executing

    def wait(self) -> None:
        """Wait for execution to complete."""
        if self._thread:
            self._thread.wait()
