"""
Data ingestion components.

Components in this category handle loading forest change data from various sources
(files, databases, APIs, remote services). Each component is responsible for
connecting to a data source and producing standardized output data.
"""

from .sample_component import SampleComponent

__all__ = ["SampleComponent"]


# TODO: Auto-discovery mechanism for components in subdirectories
# Future: Implement dynamic component loading from subdirectories
