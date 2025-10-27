"""Component panel - displays available components."""

import logging
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QPushButton, QLabel, QTextEdit, QSplitter,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from forest_change_framework.core.registry import ComponentRegistry
from ..dialogs import show_config_dialog

logger = logging.getLogger(__name__)


class ComponentPanel(QWidget):
    """Panel displaying available components organized by category.

    Displays:
    - Component tree (organized by category)
    - Component search
    - Component details
    """

    # Signals
    component_selected = pyqtSignal(str, str)  # category, component_name
    component_executed = pyqtSignal(str, str)  # category, component_name

    def __init__(self, parent=None):
        """Initialize component panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.registry = ComponentRegistry()
        self._component_config: Optional[Dict] = None
        self._selected_component: Optional[tuple] = None
        self._setup_ui()
        self._load_components()

    def _setup_ui(self) -> None:
        """Set up user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Components")
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Search box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search components...")
        self.search_input.textChanged.connect(self._filter_components)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Splitter for tree and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Component tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._on_component_selected)
        splitter.addWidget(self.tree)

        # Component details
        details_label = QLabel("Details")
        details_label.setStyleSheet("font-weight: bold; margin: 5px;")

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(120)
        splitter.addWidget(self.details_text)

        layout.addWidget(splitter)

        # Action buttons
        button_layout = QHBoxLayout()

        self.configure_btn = QPushButton("Configure")
        self.configure_btn.setEnabled(False)
        self.configure_btn.clicked.connect(self._configure_component)
        button_layout.addWidget(self.configure_btn)

        self.run_btn = QPushButton("Run")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._run_component)
        button_layout.addWidget(self.run_btn)

        layout.addLayout(button_layout)

    def _load_components(self) -> None:
        """Load components from registry."""
        self.tree.clear()

        # Get all categories
        try:
            categories = [
                "data_ingestion",
                "preprocessing",
                "analysis",
                "visualization",
                "export"
            ]

            for category in categories:
                components = self.registry.list_components(category).get(category, {})

                if components:
                    # Create category item
                    category_item = QTreeWidgetItem()
                    category_item.setText(0, category.replace("_", " ").title())
                    category_item.setExpanded(True)
                    self.tree.addTopLevelItem(category_item)

                    # Add components to category
                    for comp_name in sorted(components.keys()):
                        comp_item = QTreeWidgetItem()
                        comp_item.setText(0, comp_name)
                        comp_item.setData(0, Qt.ItemDataRole.UserRole, (category, comp_name))
                        category_item.addChild(comp_item)

        except Exception as e:
            logger.error(f"Failed to load components: {e}")

    def _filter_components(self, search_text: str) -> None:
        """Filter components based on search text.

        Args:
            search_text: Search query
        """
        search_text = search_text.lower()

        # Iterate through all items
        for i in range(self.tree.topLevelItemCount()):
            category_item = self.tree.topLevelItem(i)

            visible_children = 0
            for j in range(category_item.childCount()):
                child_item = category_item.child(j)
                component_name = child_item.text(0)

                # Show if matches search
                matches = search_text in component_name.lower()
                child_item.setHidden(not matches)

                if matches:
                    visible_children += 1

            # Hide category if no visible children
            category_item.setHidden(visible_children == 0)

    def _on_component_selected(self) -> None:
        """Handle component selection."""
        current_item = self.tree.currentItem()

        if not current_item or not current_item.parent():
            # Category item selected
            self.configure_btn.setEnabled(False)
            self.run_btn.setEnabled(False)
            self.details_text.clear()
            return

        # Component item selected
        category, comp_name = current_item.data(0, Qt.ItemDataRole.UserRole)

        try:
            # Get component info
            comp_class = self.registry.get_component(category, comp_name)
            component = comp_class(None)

            # Display component details
            details = f"""
<b>Component:</b> {comp_name}<br>
<b>Category:</b> {category}<br>
<b>Version:</b> {component.version}<br>
<br>
<b>Description:</b><br>
{component.__class__.__doc__ or "No description available"}
            """.strip()

            self.details_text.setHtml(details)

            # Enable buttons
            self.configure_btn.setEnabled(True)
            self.run_btn.setEnabled(True)

            self.component_selected.emit(category, comp_name)

        except Exception as e:
            logger.error(f"Failed to load component details: {e}")
            self.details_text.setText(f"Error loading component: {e}")

    def _configure_component(self) -> None:
        """Open component configuration dialog."""
        current_item = self.tree.currentItem()

        if not current_item or not current_item.parent():
            return

        category, comp_name = current_item.data(0, Qt.ItemDataRole.UserRole)
        logger.info(f"Configuring component: {category}/{comp_name}")

        try:
            # Get component info
            comp_class = self.registry.get_component(category, comp_name)
            component = comp_class(None)

            # Get component metadata
            component_info = {
                "name": comp_name,
                "category": category,
                "version": component.version,
                "description": component.__class__.__doc__ or "",
            }

            # Show configuration dialog
            config = show_config_dialog(
                comp_name,
                category,
                component_info,
                parent=self,
            )

            if config:
                logger.info(f"Component configured: {comp_name}")
                logger.debug(f"Configuration: {config}")
                # Store config for later execution
                self._component_config = config
                self._selected_component = (category, comp_name)
                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    f"Component '{comp_name}' configured successfully.",
                )

        except Exception as e:
            logger.error(f"Failed to configure component: {e}")
            QMessageBox.critical(
                self,
                "Configuration Error",
                f"Failed to configure component: {e}",
            )

    def _run_component(self) -> None:
        """Run selected component."""
        current_item = self.tree.currentItem()

        if not current_item or not current_item.parent():
            return

        category, comp_name = current_item.data(0, Qt.ItemDataRole.UserRole)
        logger.info(f"Running component: {category}/{comp_name}")

        self.component_executed.emit(category, comp_name)

        # TODO: Execute component

    def get_selected_component(self) -> Optional[tuple]:
        """Get currently selected component.

        Returns:
            Tuple of (category, component_name) or None
        """
        current_item = self.tree.currentItem()

        if not current_item or not current_item.parent():
            return None

        return current_item.data(0, Qt.ItemDataRole.UserRole)

    def get_component_config(self) -> Optional[Dict]:
        """Get configuration for currently selected component.

        Returns:
            Configuration dictionary or None if not configured
        """
        return self._component_config
