"""Google Earth Engine utilities for imagery downloading."""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

try:
    import ee
except ImportError:
    ee = None

logger = logging.getLogger(__name__)


def expand_date_range(
    target_date: datetime,
    initial_range_days: int,
    max_range_days: int,
) -> List[Tuple[datetime, datetime]]:
    """
    Generate expanding date ranges for searching imagery.

    If initial range doesn't find suitable imagery, automatically expands.

    Args:
        target_date: Central date to search around (e.g., Jan 1st)
        initial_range_days: Initial ±days around target
        max_range_days: Maximum ±days to expand to

    Returns:
        List of (start_date, end_date) tuples in order of preference
    """
    ranges = []

    # Generate expanding ranges: 30, 60, 90
    for range_days in range(initial_range_days, max_range_days + 1, 30):
        if range_days > max_range_days:
            break
        start = target_date - timedelta(days=range_days)
        end = target_date + timedelta(days=range_days)
        ranges.append((start, end))

    return ranges


def calculate_pre_post_dates(
    loss_year: int,
) -> Tuple[datetime, datetime]:
    """
    Calculate pre and post event dates.

    Pre: Jan 1st of loss year
    Post: Jan 1st of year+1

    Args:
        loss_year: Year when forest loss was detected

    Returns:
        (pre_date, post_date) tuples
    """
    pre_date = datetime(loss_year, 1, 1)
    post_date = datetime(loss_year + 1, 1, 1)

    return pre_date, post_date


def query_sentinel2_scenes(
    bbox: Dict[str, float],
    start_date: datetime,
    end_date: datetime,
    cloud_cover_threshold: int = 30,
) -> Optional[ee.Image]:
    """
    Query Google Earth Engine for Sentinel-2 scenes.

    Args:
        bbox: Bounding box {'minx': float, 'miny': float, 'maxx': float, 'maxy': float}
        start_date: Start date for search
        end_date: End date for search
        cloud_cover_threshold: Maximum cloud cover percentage (0-100)

    Returns:
        Best ee.Image match or None if nothing found
    """
    if not ee:
        raise ImportError("earthengine-api not available")

    try:
        # Create geometry from bbox
        geometry = ee.Geometry.Rectangle([
            bbox["minx"], bbox["miny"],
            bbox["maxx"], bbox["maxy"]
        ])

        # Query Sentinel-2 collection
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(geometry)
            .filterDate(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_threshold))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )

        # Get best image (lowest cloud cover)
        image = collection.first()

        # Check if image exists
        if image.getInfo() is None:
            return None

        return image

    except Exception as e:
        logger.error(f"Error querying Sentinel-2: {e}")
        return None


def get_sentinel2_bands(band_names: List[str]) -> Dict[str, str]:
    """
    Map band names to Sentinel-2 band IDs.

    Args:
        band_names: List of band names (e.g., ["B4", "B3", "B2"])

    Returns:
        Dictionary mapping band name to band ID
    """
    band_mapping = {
        "B1": "B1",      # Coastal aerosol
        "B2": "B2",      # Blue
        "B3": "B3",      # Green
        "B4": "B4",      # Red
        "B5": "B5",      # Vegetation Red Edge
        "B6": "B6",      # Vegetation Red Edge
        "B7": "B7",      # Vegetation Red Edge
        "B8": "B8",      # NIR
        "B8A": "B8A",    # Vegetation Red Edge
        "B11": "B11",    # SWIR
        "B12": "B12",    # SWIR
    }

    result = {}
    for band in band_names:
        if band in band_mapping:
            result[band] = band_mapping[band]
        else:
            logger.warning(f"Unknown band: {band}")

    return result


def estimate_cloud_cover(image: ee.Image) -> float:
    """
    Estimate cloud cover percentage for an image.

    Args:
        image: Google Earth Engine image

    Returns:
        Cloud cover percentage (0-100)
    """
    try:
        cloud_cover = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
        return float(cloud_cover) if cloud_cover else 100.0
    except Exception as e:
        logger.warning(f"Could not determine cloud cover: {e}")
        return 100.0
