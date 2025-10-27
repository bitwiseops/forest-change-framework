"""Component configuration dialog.

This module provides a dialog for configuring component parameters
using auto-generated forms from component schemas.
"""

from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..forms import FormWidget
from ..schemas import ComponentSchema, get_schema


class ComponentConfigDialog(QDialog):
    """Dialog for configuring component parameters."""

    # Signals
    config_submitted = pyqtSignal(dict)  # Emitted when config is submitted

    def __init__(
        self,
        component_name: str,
        component_category: str,
        initial_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize configuration dialog.

        Args:
            component_name: Name of component to configure
            component_category: Category of component
            initial_config: Initial configuration to populate form
            parent: Parent widget
        """
        super().__init__(parent)
        self.component_name = component_name
        self.component_category = component_category
        self.initial_config = initial_config or {}

        # Get schema for component
        self.schema = get_schema(component_name)
        if not self.schema:
            # Create a generic schema if none defined
            from ..schemas import ComponentSchema

            self.schema = ComponentSchema(
                component_name=component_name,
                category=component_category,
                fields=[],
                description="Generic component configuration",
            )

        self._form_widget: Optional[FormWidget] = None
        self._setup_ui()
        self.setWindowTitle(f"Configure {component_name}")
        self.resize(500, 600)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(self.schema.component_name)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Description
        if self.schema.description:
            description = QLabel(self.schema.description)
            description.setWordWrap(True)
            layout.addWidget(description)

        # Create form from schema
        self._form_widget = FormWidget(
            self.schema, self.initial_config, parent=self
        )
        layout.addWidget(self._form_widget)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _on_ok(self) -> None:
        """Handle OK button click."""
        # Validate form
        is_valid, error_msg = self._form_widget.validate()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_msg)
            return

        # Get configuration
        config = self._form_widget.get_config()

        # Emit signal
        self.config_submitted.emit(config)

        # Accept dialog
        self.accept()

    def get_config(self) -> Dict[str, Any]:
        """
        Get the final configuration.

        This is typically called after exec() returns QDialog.Accepted.

        Returns:
            Configuration dictionary
        """
        if self._form_widget:
            return self._form_widget.get_config()
        return {}


class QuickConfigDialog(QDialog):
    """Quick configuration dialog for components without detailed schemas."""

    config_submitted = pyqtSignal(dict)

    def __init__(
        self,
        component_name: str,
        component_info: Dict[str, Any],
        initial_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize quick config dialog.

        Args:
            component_name: Name of component
            component_info: Component metadata from registry
            initial_config: Initial configuration
            parent: Parent widget
        """
        super().__init__(parent)
        self.component_name = component_name
        self.component_info = component_info
        self.initial_config = initial_config or {}

        self._setup_ui()
        self.setWindowTitle(f"Configure {component_name}")
        self.resize(400, 300)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(self.component_name)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Description
        description = self.component_info.get("description", "")
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Info message
        info = QLabel(
            "No predefined configuration schema available.\n"
            "Add configuration parameters in data/config/ folder."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)


def show_config_dialog(
    component_name: str,
    component_category: str,
    component_info: Optional[Dict[str, Any]] = None,
    initial_config: Optional[Dict[str, Any]] = None,
    parent: Optional[QWidget] = None,
) -> Optional[Dict[str, Any]]:
    """
    Show configuration dialog for a component.

    Args:
        component_name: Name of component
        component_category: Category of component
        component_info: Component metadata
        initial_config: Initial configuration values
        parent: Parent widget

    Returns:
        Configuration dictionary if accepted, None if cancelled
    """
    # Try to show detailed config dialog
    dialog = ComponentConfigDialog(
        component_name,
        component_category,
        initial_config,
        parent,
    )

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_config()

    return None
