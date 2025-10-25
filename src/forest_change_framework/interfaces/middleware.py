"""
Abstract middleware interface.

This module defines the BaseMiddleware interface for components that provide
cross-cutting concerns like logging, monitoring, or validation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseMiddleware(ABC):
    """
    Abstract base class for middleware components.

    Middleware components provide cross-cutting functionality that applies to
    multiple other components. They use before() and after() hooks to wrap
    component execution.

    Attributes:
        name: The middleware name.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize the middleware.

        Args:
            name: The middleware name.
        """
        self.name = name
        logger.debug(f"Middleware {name} initialized")

    @abstractmethod
    def before(self, component_name: str, *args: Any, **kwargs: Any) -> None:
        """
        Hook called before component execution.

        This method is called before a component's execute() method is invoked.
        It can perform setup, validation, or logging operations.

        Args:
            component_name: Name of the component about to execute.
            *args: Arguments that will be passed to the component.
            **kwargs: Keyword arguments that will be passed to the component.

        Raises:
            Exception: Subclasses should raise to prevent component execution.

        Example:
            >>> def before(self, component_name, *args, **kwargs):
            ...     logger.info(f"Executing {component_name}")
            ...     logger.debug(f"Args: {args}, Kwargs: {kwargs}")
        """
        pass

    @abstractmethod
    def after(
        self,
        component_name: str,
        result: Any,
        error: Optional[Exception] = None,
    ) -> Any:
        """
        Hook called after component execution.

        This method is called after a component's execute() method completes,
        whether successfully or with an error. It can perform logging, result
        transformation, or cleanup operations.

        Args:
            component_name: Name of the component that executed.
            result: The result returned by the component (None if error occurred).
            error: Exception if the component raised one (None if successful).

        Returns:
            Transformed result, or the original result if no transformation needed.

        Example:
            >>> def after(self, component_name, result, error):
            ...     if error:
            ...         logger.error(f"{component_name} failed: {error}")
            ...     else:
            ...         logger.info(f"{component_name} completed successfully")
            ...     return result
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        Get middleware metadata.

        Returns:
            Dictionary containing middleware information.
        """
        return {
            "name": self.name,
            "description": self.__doc__ or "No description available",
        }
