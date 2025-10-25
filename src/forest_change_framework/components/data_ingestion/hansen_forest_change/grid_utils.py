"""
Utility functions for parsing and working with Hansen's lat/lon tile grid system.

Hansen's forest change dataset uses a lat/lon tiling scheme where each tile
represents a 10°×10° area. Tiles are named using latitude and longitude notation:
- Latitude: 00N, 10N, 20N, ..., 80N (north) and 10S, 20S, ..., 80S (south)
- Longitude: 000E, 010E, 020E, ..., 180E (east) and 010W, 020W, ..., 180W (west)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_tile_list(lines: List[str]) -> Dict[str, str]:
    """
    Parse Hansen tile reference file.

    The tile list files from Google Storage contain filenames with tile references,
    typically extracted from: Hansen_GFC-2024-v1.12_{layer}_{lat}_{lon}.tif

    This function extracts the lat/lon part from each filename.

    Args:
        lines: List of lines from a tile reference file (can be filenames or paths).

    Returns:
        Dictionary mapping tile IDs (e.g., "00N_000E") to their geographic bounds.

    Example:
        >>> lines = ["Hansen_GFC-2024-v1.12_lossyear_00N_000E.tif",
        ...          "Hansen_GFC-2024-v1.12_lossyear_10N_010E.tif"]
        >>> tiles = parse_tile_list(lines)
        >>> "00N_000E" in tiles
        True
    """
    tiles = {}

    for line in lines:
        # Clean up line: strip whitespace
        line = line.strip()
        if not line:
            continue

        # Extract lat/lon coordinates from filename
        # Pattern: {layer}_{XXYY}_{XXXEE} where XX is degrees, Y/E is direction
        match = re.search(r'([0-8]\d[NS])_(\d{3}[EW])', line)

        if not match:
            logger.debug(f"Skipping line with no valid lat/lon: {line}")
            continue

        latitude = match.group(1)  # e.g., "00N", "10S"
        longitude = match.group(2)  # e.g., "000E", "010W"
        tile_id = f"{latitude}_{longitude}"

        # Validate tile_id
        if not _is_valid_tile_id(tile_id):
            logger.warning(f"Skipping invalid tile ID: {tile_id}")
            continue

        # Calculate bounds for this tile
        bounds = get_tile_bounds(tile_id)
        tiles[tile_id] = bounds

    logger.info(f"Parsed {len(tiles)} valid tiles from tile list")
    return tiles


def bbox_to_tiles(
    bbox: Dict[str, float], tiles: Dict[str, Any]
) -> List[str]:
    """
    Find all tiles that overlap with the given bounding box.

    Args:
        bbox: Dictionary with keys 'minx', 'miny', 'maxx', 'maxy' in WGS84.
        tiles: Dictionary of available tiles (output from parse_tile_list).

    Returns:
        List of tile IDs that overlap with the bounding box.

    Raises:
        ValueError: If bbox has invalid coordinates or missing keys.

    Example:
        >>> bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}
        >>> tiles = {"00N_000E": {...}, "10N_000E": {...}}
        >>> overlapping = bbox_to_tiles(bbox, tiles)
        >>> "00N_000E" in overlapping
        True
    """
    # Validate bbox
    required_keys = {"minx", "miny", "maxx", "maxy"}
    if not required_keys.issubset(bbox.keys()):
        raise ValueError(f"Bbox must contain keys: {required_keys}")

    minx, miny, maxx, maxy = bbox["minx"], bbox["miny"], bbox["maxx"], bbox["maxy"]

    # Validate bbox coordinates
    if minx >= maxx or miny >= maxy:
        raise ValueError(
            f"Invalid bbox: minx={minx}, maxx={maxx}, miny={miny}, maxy={maxy}"
        )

    if not _is_valid_wgs84_bbox(minx, miny, maxx, maxy):
        raise ValueError(
            f"Bbox coordinates outside WGS84 bounds: {minx}, {miny}, {maxx}, {maxy}"
        )

    overlapping_tiles = []

    for tile_id, tile_bounds in tiles.items():
        if _bboxes_overlap(bbox, tile_bounds):
            overlapping_tiles.append(tile_id)

    logger.debug(
        f"Found {len(overlapping_tiles)} tiles overlapping bbox: "
        f"[{minx}, {miny}, {maxx}, {maxy}]"
    )
    return sorted(overlapping_tiles)


def get_tile_bounds(tile_id: str) -> Dict[str, float]:
    """
    Calculate the geographic bounds of a Hansen lat/lon tile.

    Tiles are 10°×10° in size. Tile naming: XXYY_XXXZZ where:
    - XX: degrees latitude (00-80)
    - YY: direction (N=North, S=South)
    - XXX: degrees longitude (000-180)
    - ZZ: direction (E=East, W=West)

    Args:
        tile_id: Tile ID in format "##N_###E" (e.g., "00N_000E", "10S_120W").

    Returns:
        Dictionary with keys: minx, miny, maxx, maxy (WGS84 coordinates).

    Raises:
        ValueError: If tile_id is not in valid format.

    Example:
        >>> bounds = get_tile_bounds("00N_000E")
        >>> bounds["minx"]
        0.0
        >>> bounds["maxy"]
        10.0
    """
    tile_id = tile_id.strip().upper()

    if not _is_valid_tile_id(tile_id):
        raise ValueError(f"Invalid tile ID format: {tile_id}")

    # Parse latitude (e.g., "00N" or "10S")
    lat_match = re.match(r'(\d{2})([NS])', tile_id)
    lat_deg = int(lat_match.group(1))
    lat_dir = lat_match.group(2)

    # Parse longitude (e.g., "000E" or "010W")
    lon_match = re.search(r'(\d{3})([EW])', tile_id)
    lon_deg = int(lon_match.group(1))
    lon_dir = lon_match.group(2)

    # Calculate bounds
    # Latitude: North is positive, South is negative
    if lat_dir == 'N':
        maxy = lat_deg + 10.0
        miny = lat_deg
    else:  # 'S'
        maxy = -lat_deg
        miny = -lat_deg - 10.0

    # Longitude: East is positive, West is negative
    if lon_dir == 'E':
        minx = lon_deg
        maxx = lon_deg + 10.0
    else:  # 'W'
        minx = -lon_deg - 10.0
        maxx = -lon_deg

    return {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}


# ============================================================================
# Private Helper Functions
# ============================================================================


def _is_valid_tile_id(tile_id: str) -> bool:
    """
    Check if a string is a valid Hansen tile ID (##N_###E format).

    Args:
        tile_id: String to validate.

    Returns:
        True if valid format and within valid ranges.
    """
    tile_id = tile_id.strip().upper()

    # Check format: ##N_###E or ##S_###W, etc.
    # Pattern: 2 digits, direction (N/S), underscore, 3 digits, direction (E/W)
    pattern = r'^(\d{2}[NS])_(\d{3}[EW])$'
    if not re.match(pattern, tile_id):
        return False

    # Parse and validate ranges
    try:
        lat_match = re.match(r'(\d{2})([NS])', tile_id)
        lat_deg = int(lat_match.group(1))

        lon_match = re.search(r'(\d{3})([EW])', tile_id)
        lon_deg = int(lon_match.group(1))

        # Latitude: 00-80
        if lat_deg > 80:
            return False

        # Longitude: 000-180
        if lon_deg > 180:
            return False

        return True
    except (ValueError, AttributeError):
        return False


def _is_valid_wgs84_bbox(
    minx: float, miny: float, maxx: float, maxy: float
) -> bool:
    """
    Check if bounding box coordinates are within WGS84 limits.

    Args:
        minx, miny, maxx, maxy: Bounding box coordinates.

    Returns:
        True if all coordinates are within [-180, 180] for x and [-90, 90] for y.
    """
    return (
        -180 <= minx <= 180
        and -180 <= maxx <= 180
        and -90 <= miny <= 90
        and -90 <= maxy <= 90
    )


def _bboxes_overlap(bbox1: Dict[str, float], bbox2: Dict[str, float]) -> bool:
    """
    Check if two bounding boxes overlap.

    Args:
        bbox1, bbox2: Dictionaries with minx, miny, maxx, maxy keys.

    Returns:
        True if bboxes overlap, False otherwise.
    """
    return not (
        bbox1["maxx"] < bbox2["minx"]
        or bbox1["minx"] > bbox2["maxx"]
        or bbox1["maxy"] < bbox2["miny"]
        or bbox1["miny"] > bbox2["maxy"]
    )
