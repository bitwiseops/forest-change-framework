"""
Hansen forest change data ingestion component.

This component downloads and processes Hansen's Global Forest Change dataset
for a specified bounding box, including automatic tile discovery, download,
and rasterio-based stacking for further analysis.
"""

from .component import HansenForestChangeComponent

__all__ = ["HansenForestChangeComponent"]
