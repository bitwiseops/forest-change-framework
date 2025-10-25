"""
Unit tests for ComponentRegistry.

Tests component registration, discovery, and lifecycle.
"""

import pytest
from forest_change_framework.core import (
    ComponentRegistry,
    get_registry,
    register_component,
    RegistryError,
)
from forest_change_framework.interfaces import BaseComponent


@pytest.mark.unit
class TestComponentRegistry:
    """Test ComponentRegistry functionality."""

    def test_registry_singleton(self):
        """Test that get_registry returns the same instance."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_register_component(self, clean_registry, mock_component_class):
        """Test registering a component."""
        registry = clean_registry

        registry.register(
            mock_component_class,
            "test_comp",
            "analysis",
            version="1.0.0",
            description="Test component",
        )

        assert "analysis" in registry._components
        assert "test_comp" in registry._components["analysis"]

    def test_register_duplicate_raises_error(self, clean_registry, mock_component_class):
        """Test that registering duplicate component raises error."""
        registry = clean_registry

        registry.register(
            mock_component_class,
            "duplicate",
            "analysis",
        )

        with pytest.raises(RegistryError):
            registry.register(
                mock_component_class,
                "duplicate",
                "analysis",
            )

    def test_get_component_class(self, clean_registry, mock_component_class):
        """Test retrieving a component class."""
        registry = clean_registry

        registry.register(
            mock_component_class,
            "my_comp",
            "preprocessing",
        )

        retrieved = registry.get("preprocessing", "my_comp")
        assert retrieved is mock_component_class

    def test_get_nonexistent_component_raises_error(self, clean_registry):
        """Test that getting nonexistent component raises error."""
        registry = clean_registry

        with pytest.raises(RegistryError):
            registry.get("nonexistent", "component")

    def test_get_info(self, clean_registry, mock_component_class):
        """Test retrieving component metadata."""
        registry = clean_registry

        registry.register(
            mock_component_class,
            "info_test",
            "analysis",
            version="2.0.0",
            description="A test component",
            metadata={"author": "test"},
        )

        info = registry.get_info("analysis", "info_test")

        assert info["name"] == "info_test"
        assert info["category"] == "analysis"
        assert info["version"] == "2.0.0"
        assert info["description"] == "A test component"
        assert info["metadata"]["author"] == "test"

    def test_list_components_all(self, clean_registry, mock_component_class):
        """Test listing all components."""
        registry = clean_registry

        class TestComp2(BaseComponent):
            @property
            def name(self):
                return "test2"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                pass

            def cleanup(self):
                pass

        registry.register(mock_component_class, "comp1", "analysis")
        registry.register(TestComp2, "comp2", "preprocessing")

        comps = registry.list_components()

        assert "analysis" in comps
        assert "preprocessing" in comps
        assert "comp1" in comps["analysis"]
        assert "comp2" in comps["preprocessing"]

    def test_list_components_by_category(self, clean_registry, mock_component_class):
        """Test listing components in specific category."""
        registry = clean_registry

        registry.register(mock_component_class, "comp1", "analysis")
        registry.register(mock_component_class, "comp2", "analysis")

        comps = registry.list_components("analysis")

        assert "analysis" in comps
        assert "comp1" in comps["analysis"]
        assert "comp2" in comps["analysis"]

    def test_list_categories(self, clean_registry, mock_component_class):
        """Test listing all categories."""
        registry = clean_registry

        class TestComp2(BaseComponent):
            @property
            def name(self):
                return "test2"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                pass

            def cleanup(self):
                pass

        registry.register(mock_component_class, "comp1", "analysis")
        registry.register(TestComp2, "comp2", "visualization")

        categories = registry.list_categories()

        assert "analysis" in categories
        assert "visualization" in categories

    def test_unregister_component(self, clean_registry, mock_component_class):
        """Test unregistering a component."""
        registry = clean_registry

        registry.register(mock_component_class, "to_remove", "analysis")
        assert "to_remove" in registry._components["analysis"]

        registry.unregister("analysis", "to_remove")
        assert "to_remove" not in registry._components.get("analysis", {})

    def test_unregister_nonexistent_raises_error(self, clean_registry):
        """Test unregistering nonexistent component raises error."""
        registry = clean_registry

        with pytest.raises(RegistryError):
            registry.unregister("analysis", "nonexistent")

    def test_clear_registry(self, clean_registry, mock_component_class):
        """Test clearing all components."""
        registry = clean_registry

        registry.register(mock_component_class, "comp", "analysis")
        assert len(registry._components) > 0

        registry.clear()
        assert len(registry._components) == 0


@pytest.mark.unit
class TestRegisterComponentDecorator:
    """Test @register_component decorator."""

    def test_decorator_registers_component(self, clean_registry):
        """Test that decorator registers component."""
        from forest_change_framework.core import get_registry

        @register_component(
            category="test",
            name="decorated_comp",
            version="1.0.0",
            description="Decorated component",
        )
        class DecoratedComponent(BaseComponent):
            @property
            def name(self):
                return "decorated_comp"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                pass

            def cleanup(self):
                pass

        registry = get_registry()
        retrieved = registry.get("test", "decorated_comp")
        assert retrieved is DecoratedComponent

    def test_decorator_with_default_name(self, clean_registry):
        """Test decorator with default component name."""
        from forest_change_framework.core import get_registry

        @register_component(category="analysis")
        class MyAnalyzer(BaseComponent):
            @property
            def name(self):
                return "my_analyzer"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, *args, **kwargs):
                pass

            def cleanup(self):
                pass

        registry = get_registry()
        # Name should be converted to snake_case
        retrieved = registry.get("analysis", "my_analyzer")
        assert retrieved is MyAnalyzer
