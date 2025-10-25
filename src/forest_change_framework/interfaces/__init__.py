"""
Interface definitions for framework extensibility.

This package contains abstract base classes that define the contracts for
different types of framework extensions.
"""

from .component import BaseComponent
from .plugin import BasePlugin
from .middleware import BaseMiddleware

__all__ = [
    "BaseComponent",
    "BasePlugin",
    "BaseMiddleware",
]
