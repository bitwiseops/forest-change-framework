"""Form generation from component schemas.

This module provides automatic PyQt6 form generation from component configuration
schemas, handling type-aware widgets, validation, and file pickers.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .schemas import ComponentSchema, FieldSchema, FieldType


class FormWidget(QWidget):
    """Auto-generated form widget from component schema."""

    def __init__(
        self,
        schema: ComponentSchema,
        initial_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize form widget.

        Args:
            schema: Component configuration schema
            initial_config: Initial configuration values to populate
            parent: Parent widget
        """
        super().__init__(parent)
        self.schema = schema
        self.initial_config = initial_config or {}
        self._widgets: Dict[str, QWidget] = {}
        self._file_widgets: Dict[str, tuple[QLineEdit, QPushButton]] = {}

        self._create_form()

    def _create_form(self) -> None:
        """Create the form layout from schema."""
        main_layout = QVBoxLayout(self)

        # Group fields by group
        grouped_fields: Dict[str, list[FieldSchema]] = {}
        for field in self.schema.fields:
            if field.group not in grouped_fields:
                grouped_fields[field.group] = []
            grouped_fields[field.group].append(field)

        # If only one group, use QGroupBox; otherwise use QTabWidget
        if len(grouped_fields) == 1:
            group_name = list(grouped_fields.keys())[0]
            group_box = self._create_group_box(group_name, grouped_fields[group_name])
            main_layout.addWidget(group_box)
        else:
            tab_widget = QTabWidget()
            for group_name, fields in grouped_fields.items():
                group_box = self._create_group_box(group_name, fields)
                tab_widget.addTab(group_box, group_name)
            main_layout.addWidget(tab_widget)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_group_box(self, group_name: str, fields: list[FieldSchema]) -> QGroupBox:
        """Create a group box with form fields."""
        group_box = QGroupBox(group_name)
        layout = QFormLayout()

        for field in fields:
            widget = self._create_field_widget(field)
            self._widgets[field.name] = widget

            # Add label and widget
            label = QLabel(field.label)
            if field.description:
                label.setToolTip(field.description)

            layout.addRow(label, widget)

        group_box.setLayout(layout)
        return group_box

    def _create_field_widget(self, field: FieldSchema) -> QWidget:
        """Create appropriate widget for field type."""
        initial_value = self.initial_config.get(
            field.name, field.default
        )

        # File/Directory picker
        if field.widget_type == "file":
            return self._create_file_picker(field, initial_value)
        elif field.widget_type == "directory":
            return self._create_directory_picker(field, initial_value)

        # Combo box (choices)
        elif field.widget_type == "combo" or field.choices:
            combo = QComboBox()
            if field.choices:
                for choice in field.choices:
                    combo.addItem(str(choice), choice)
                if initial_value is not None:
                    index = combo.findData(initial_value)
                    if index >= 0:
                        combo.setCurrentIndex(index)
            return combo

        # Boolean checkbox
        elif field.type_ is bool:
            checkbox = QCheckBox()
            checkbox.setChecked(bool(initial_value))
            return checkbox

        # Numeric inputs
        elif field.type_ is int:
            spin = QSpinBox()
            if field.min_value is not None:
                spin.setMinimum(int(field.min_value))
            else:
                spin.setMinimum(-999999)
            if field.max_value is not None:
                spin.setMaximum(int(field.max_value))
            else:
                spin.setMaximum(999999)
            if initial_value is not None:
                spin.setValue(int(initial_value))
            return spin

        elif field.type_ is float:
            spin = QDoubleSpinBox()
            if field.min_value is not None:
                spin.setMinimum(float(field.min_value))
            else:
                spin.setMinimum(-999999.0)
            if field.max_value is not None:
                spin.setMaximum(float(field.max_value))
            else:
                spin.setMaximum(999999.0)
            spin.setDecimals(4)
            if initial_value is not None:
                spin.setValue(float(initial_value))
            return spin

        # String/text input (default)
        else:
            line_edit = QLineEdit()
            if initial_value is not None:
                line_edit.setText(str(initial_value))
            if field.max_length:
                line_edit.setMaxLength(field.max_length)
            return line_edit

    def _create_file_picker(
        self, field: FieldSchema, initial_value: Any
    ) -> QWidget:
        """Create a file picker widget with button."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit()
        if initial_value:
            line_edit.setText(str(initial_value))

        button = QPushButton("Browse...")
        button.clicked.connect(
            lambda: self._on_file_browse(field, line_edit)
        )

        layout.addWidget(line_edit)
        layout.addWidget(button)

        self._file_widgets[field.name] = (line_edit, button)
        return container

    def _create_directory_picker(
        self, field: FieldSchema, initial_value: Any
    ) -> QWidget:
        """Create a directory picker widget with button."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit()
        if initial_value:
            line_edit.setText(str(initial_value))

        button = QPushButton("Browse...")
        button.clicked.connect(
            lambda: self._on_directory_browse(field, line_edit)
        )

        layout.addWidget(line_edit)
        layout.addWidget(button)

        self._file_widgets[field.name] = (line_edit, button)
        return container

    def _on_file_browse(self, field: FieldSchema, line_edit: QLineEdit) -> None:
        """Handle file picker button click."""
        file_filter = field.file_filter or "All Files (*)"
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {field.label}",
            "",
            file_filter,
        )
        if path:
            line_edit.setText(path)

    def _on_directory_browse(
        self, field: FieldSchema, line_edit: QLineEdit
    ) -> None:
        """Handle directory picker button click."""
        path = QFileDialog.getExistingDirectory(
            self,
            f"Select {field.label}",
        )
        if path:
            line_edit.setText(path)

    def get_config(self) -> Dict[str, Any]:
        """Extract configuration from form."""
        config = {}

        for field in self.schema.fields:
            if field.name not in self._widgets:
                # File/directory picker - get from file widgets
                if field.name in self._file_widgets:
                    line_edit, _ = self._file_widgets[field.name]
                    value = line_edit.text()
                    if value:
                        config[field.name] = value
                continue

            widget = self._widgets[field.name]

            if isinstance(widget, QCheckBox):
                config[field.name] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                config[field.name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                config[field.name] = widget.value()
            elif isinstance(widget, QComboBox):
                config[field.name] = widget.currentData()
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if text:
                    config[field.name] = text
            else:
                # Extract from container widget (file/directory picker)
                if hasattr(widget, "layout"):
                    layout = widget.layout()
                    if layout.count() > 0:
                        item = layout.itemAt(0)
                        if item and isinstance(item.widget(), QLineEdit):
                            text = item.widget().text().strip()
                            if text:
                                config[field.name] = text

        return config

    def validate(self) -> tuple[bool, str]:
        """
        Validate form input.

        Returns:
            Tuple of (is_valid, error_message)
        """
        config = self.get_config()

        for field in self.schema.fields:
            # Check required fields
            if field.required and field.name not in config:
                return False, f"Required field missing: {field.label}"

            if field.name not in config:
                continue

            value = config[field.name]

            # Type validation
            if field.type_ is int and not isinstance(value, int):
                try:
                    int(value)
                except (ValueError, TypeError):
                    return False, f"{field.label} must be an integer"

            elif field.type_ is float and not isinstance(value, float):
                try:
                    float(value)
                except (ValueError, TypeError):
                    return False, f"{field.label} must be a number"

            # Range validation
            if isinstance(value, (int, float)):
                if field.min_value is not None and value < field.min_value:
                    return (
                        False,
                        f"{field.label} must be >= {field.min_value}",
                    )
                if field.max_value is not None and value > field.max_value:
                    return (
                        False,
                        f"{field.label} must be <= {field.max_value}",
                    )

            # String validation
            if isinstance(value, str):
                if field.min_length and len(value) < field.min_length:
                    return (
                        False,
                        f"{field.label} must be at least "
                        f"{field.min_length} characters",
                    )
                if field.max_length and len(value) > field.max_length:
                    return (
                        False,
                        f"{field.label} must be at most "
                        f"{field.max_length} characters",
                    )

            # File/path validation
            if field.widget_type == "file" or field.widget_type == "directory":
                path = Path(value) if isinstance(value, str) else value
                if not path.exists():
                    return False, f"Path does not exist: {field.label}"

        return True, ""
