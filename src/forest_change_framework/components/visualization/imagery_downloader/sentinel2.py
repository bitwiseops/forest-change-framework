"""Sentinel-2 specific utilities and processing."""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Sentinel-2 band information
SENTINEL2_BANDS = {
    "B1": {"name": "Coastal Aerosol", "resolution": 60},
    "B2": {"name": "Blue", "resolution": 10},
    "B3": {"name": "Green", "resolution": 10},
    "B4": {"name": "Red", "resolution": 10},
    "B5": {"name": "Vegetation Red Edge", "resolution": 20},
    "B6": {"name": "Vegetation Red Edge", "resolution": 20},
    "B7": {"name": "Vegetation Red Edge", "resolution": 20},
    "B8": {"name": "NIR", "resolution": 10},
    "B8A": {"name": "Vegetation Red Edge", "resolution": 20},
    "B9": {"name": "Water Vapour", "resolution": 60},
    "B11": {"name": "SWIR", "resolution": 20},
    "B12": {"name": "SWIR", "resolution": 20},
}

# Common band combinations for different purposes
BAND_COMBINATIONS = {
    "rgb": ["B4", "B3", "B2"],  # True color
    "ndvi": ["B8", "B4"],  # Normalized Difference Vegetation Index
    "ndbi": ["B11", "B8"],  # Normalized Difference Built-up Index
    "ndmi": ["B8", "B11"],  # Normalized Difference Moisture Index
    "custom": None,  # User-defined
}


def get_band_info(band_name: str) -> Dict[str, object]:
    """
    Get information about a Sentinel-2 band.

    Args:
        band_name: Band name (e.g., "B4")

    Returns:
        Dictionary with band information
    """
    return SENTINEL2_BANDS.get(band_name, {})


def validate_bands(band_names: List[str]) -> Tuple[bool, str]:
    """
    Validate Sentinel-2 band names.

    Args:
        band_names: List of band names to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not band_names:
        return False, "Band list is empty"

    invalid_bands = [b for b in band_names if b not in SENTINEL2_BANDS]
    if invalid_bands:
        return False, f"Invalid bands: {', '.join(invalid_bands)}"

    return True, ""


def get_common_combination(combination_name: str) -> List[str]:
    """
    Get common band combination.

    Args:
        combination_name: Name of combination (rgb, ndvi, etc.)

    Returns:
        List of band names
    """
    return BAND_COMBINATIONS.get(combination_name, [])


def recommend_resolution(band_names: List[str]) -> int:
    """
    Recommend output resolution based on selected bands.

    Sentinel-2 has multiple resolutions: 10m (B2,B3,B4,B8), 20m (B5,B6,B7,B8A,B11,B12), 60m (B1,B9)
    Best to resample to 10m if mixing bands.

    Args:
        band_names: List of selected bands

    Returns:
        Recommended resolution in meters
    """
    resolutions = set()
    for band in band_names:
        info = SENTINEL2_BANDS.get(band, {})
        if "resolution" in info:
            resolutions.add(info["resolution"])

    if not resolutions:
        return 10  # Default to 10m

    # Return highest resolution (smallest number)
    return min(resolutions)


def get_band_dtype() -> str:
    """
    Get data type for Sentinel-2 bands.

    Sentinel-2 L2A (surface reflectance) is typically uint16.

    Returns:
        NumPy dtype string
    """
    return "uint16"


def get_scale_factor() -> float:
    """
    Get scale factor for Sentinel-2 reflectance values.

    Sentinel-2 reflectance is stored as 0-10000, not 0-1.

    Returns:
        Scale factor
    """
    return 10000.0
