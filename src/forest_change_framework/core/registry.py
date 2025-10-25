"""
Component registry and auto-discovery system.

This module provides the component registry that maintains a catalog of all
registered components, organized by category. Components self-register using
the @register_component decorator.
"""

from typing import Any, Dict, List, Optional, Type
import logging

from .exceptions import RegistryError

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    Registry for managing component discovery and lifecycle.

    The ComponentRegistry maintains a catalog of all registered components,
    organized by category. It supports auto-discovery of components and
    provides access to component metadata and class references.

    Attributes:
        _components: Dictionary mapping categories to component registrations.
    """

    def __init__(self) -> None:
        """Initialize an empty component registry."""
        self._components: Dict[str, Dict[str, Dict[str, Any]]] = {}
        logger.debug("ComponentRegistry initialized")

    def register(
        self,
        component_class: Type,
        name: str,
        category: str,
        version: str = "1.0.0",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a component in the registry.

        Args:
            component_class: The component class to register.
            name: The component name (unique within its category).
            category: The category the component belongs to.
            version: Version string for the component (default: "1.0.0").
            description: Human-readable component description.
            metadata: Additional metadata dictionary for the component.

        Raises:
            RegistryError: If a component with the same name already exists in the category.

        Example:
            >>> registry = ComponentRegistry()
            >>> class MyComponent: pass
            >>> registry.register(MyComponent, "my_component", "data_ingestion")
        """
        if metadata is None:
            metadata = {}

        # Ensure category exists
        if category not in self._components:
            self._components[category] = {}

        # Check for duplicate registration
        if name in self._components[category]:
            raise RegistryError(
                f"Component '{name}' already registered in category '{category}'"
            )

        # Store component information
        self._components[category][name] = {
            "class": component_class,
            "name": name,
            "category": category,
            "version": version,
            "description": description,
            "metadata": metadata,
        }

        logger.info(f"Component registered: {category}/{name} (v{version})")

    def get(self, category: str, name: str) -> Type:
        """
        Get a component class from the registry.

        Args:
            category: The category containing the component.
            name: The component name.

        Returns:
            The component class.

        Raises:
            RegistryError: If the component is not found.

        Example:
            >>> registry = ComponentRegistry()
            >>> class MyComponent: pass
            >>> registry.register(MyComponent, "my_component", "analysis")
            >>> ComponentClass = registry.get("analysis", "my_component")
        """
        if category not in self._components:
            raise RegistryError(f"Category '{category}' not found in registry")

        if name not in self._components[category]:
            raise RegistryError(
                f"Component '{name}' not found in category '{category}'"
            )

        return self._components[category][name]["class"]

    def get_info(self, category: str, name: str) -> Dict[str, Any]:
        """
        Get metadata for a registered component.

        Args:
            category: The category containing the component.
            name: The component name.

        Returns:
            Dictionary containing component information.

        Raises:
            RegistryError: If the component is not found.
        """
        if category not in self._components:
            raise RegistryError(f"Category '{category}' not found in registry")

        if name not in self._components[category]:
            raise RegistryError(
                f"Component '{name}' not found in category '{category}'"
            )

        return self._components[category][name]

    def list_components(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List all registered components, optionally filtered by category.

        Args:
            category: Optional category to filter by. If None, returns all components.

        Returns:
            Dictionary mapping categories to lists of component names.
            If category is specified, returns only that category.

        Example:
            >>> registry = ComponentRegistry()
            >>> class C1: pass
            >>> class C2: pass
            >>> registry.register(C1, "comp1", "data_ingestion")
            >>> registry.register(C2, "comp2", "analysis")
            >>> all_comps = registry.list_components()
            >>> data_comps = registry.list_components("data_ingestion")
        """
        if category:
            if category not in self._components:
                return {category: []}
            return {category: list(self._components[category].keys())}

        return {
            cat: list(comps.keys()) for cat, comps in self._components.items()
        }

    def list_categories(self) -> List[str]:
        """
        List all registered component categories.

        Returns:
            List of category names.

        Example:
            >>> registry = ComponentRegistry()
            >>> registry.register(MyComponent, "comp1", "analysis")
            >>> registry.list_categories()
            ['analysis']
        """
        return list(self._components.keys())

    def unregister(self, category: str, name: str) -> None:
        """
        Unregister a component from the registry.

        Args:
            category: The component's category.
            name: The component name.

        Raises:
            RegistryError: If the component is not found.
        """
        if category not in self._components:
            raise RegistryError(f"Category '{category}' not found in registry")

        if name not in self._components[category]:
            raise RegistryError(
                f"Component '{name}' not found in category '{category}'"
            )

        del self._components[category][name]

        # Clean up empty categories
        if not self._components[category]:
            del self._components[category]

        logger.info(f"Component unregistered: {category}/{name}")

    def clear(self) -> None:
        """Clear all registered components. Useful for testing."""
        self._components.clear()
        logger.debug("ComponentRegistry cleared")


# Global registry instance
_global_registry = ComponentRegistry()


def get_registry() -> ComponentRegistry:
    """
    Get the global component registry.

    Returns:
        The global ComponentRegistry instance.

    Example:
        >>> registry = get_registry()
        >>> components = registry.list_components()
    """
    return _global_registry


def register_component(
    category: str,
    name: Optional[str] = None,
    version: str = "1.0.0",
    description: str = "",
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Decorator for registering a component.

    This decorator automatically registers a component class with the global
    registry. The component name defaults to the class name (in snake_case) if
    not provided.

    Args:
        category: The category for this component.
        name: Optional component name. Defaults to class name in snake_case.
        version: Version string for the component.
        description: Human-readable description of the component.
        metadata: Optional metadata dictionary.

    Returns:
        Decorator function.

    Example:
        >>> @register_component("data_ingestion", description="Loads CSV files")
        ... class CSVLoader:
        ...     pass
    """

    def decorator(cls: Type) -> Type:
        component_name = name or _to_snake_case(cls.__name__)
        registry = get_registry()
        registry.register(
            cls,
            component_name,
            category,
            version=version,
            description=description,
            metadata=metadata or {},
        )
        return cls

    return decorator


def _to_snake_case(name: str) -> str:
    """
    Convert a class name to snake_case.

    Args:
        name: The class name (typically in PascalCase).

    Returns:
        The name converted to snake_case.

    Example:
        >>> _to_snake_case("MyComponent")
        'my_component'
        >>> _to_snake_case("CSV")
        'csv'
    """
    # TODO: Handle consecutive capital letters better (e.g., "CSV" -> "csv")
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
