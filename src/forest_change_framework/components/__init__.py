"""
Framework components.

This package contains component categories for different stages of the
forest change detection pipeline. Components are self-contained, pluggable
units that can be composed together to create analysis workflows.
"""

# Import and register sample component
from .data_ingestion.sample_component import SampleComponent

__all__ = ["SampleComponent"]
