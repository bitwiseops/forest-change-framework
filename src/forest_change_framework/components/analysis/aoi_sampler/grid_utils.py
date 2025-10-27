"""Grid utility functions for creating regular grid cells over a bounding box."""

import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)

# Earth's mean radius in km
EARTH_RADIUS_KM = 6371.0


def degrees_to_km(degrees: float, latitude: float) -> float:
    """
    Convert degrees longitude or latitude to kilometers.

    Args:
        degrees: Distance in degrees
        latitude: Latitude (for longitude conversion, use mean latitude of the area)

    Returns:
        Distance in kilometers
    """
    # 1 degree latitude = 111.32 km (constant)
    if latitude is None:
        # For latitude conversions
        return degrees * 111.32

    # For longitude, it varies with latitude
    import math
    km_per_degree_lon = 111.32 * math.cos(math.radians(latitude))
    return degrees * km_per_degree_lon


def km_to_degrees(km: float, latitude: float) -> float:
    """
    Convert kilometers to degrees.

    Args:
        km: Distance in kilometers
        latitude: Latitude (for longitude conversion, use mean latitude of the area)

    Returns:
        Distance in degrees
    """
    if latitude is None:
        # For latitude conversions
        return km / 111.32

    # For longitude, it varies with latitude
    import math
    km_per_degree_lon = 111.32 * math.cos(math.radians(latitude))
    return km / km_per_degree_lon


def create_grid_cells(
    bbox: Dict[str, float], cell_size_km: float = 1.0
) -> Tuple[List[Dict[str, float]], int]:
    """
    Create a regular grid of cells covering a bounding box.

    Args:
        bbox: Bounding box dict with keys: minx, miny, maxx, maxy (WGS84 degrees)
        cell_size_km: Size of each grid cell in kilometers (default: 1km)

    Returns:
        Tuple of:
        - List of grid cells, each with bounds: {minx, miny, maxx, maxy, cell_id}
        - Total number of cells created

    Raises:
        ValueError: If bbox is invalid or cell_size_km is invalid
    """
    # Validate bbox
    if not isinstance(bbox, dict) or not all(k in bbox for k in ["minx", "miny", "maxx", "maxy"]):
        raise ValueError("bbox must have keys: minx, miny, maxx, maxy")

    minx, miny, maxx, maxy = bbox["minx"], bbox["miny"], bbox["maxx"], bbox["maxy"]

    if minx >= maxx or miny >= maxy:
        raise ValueError(f"Invalid bbox: minx >= maxx or miny >= maxy")

    if cell_size_km <= 0:
        raise ValueError(f"cell_size_km must be positive, got {cell_size_km}")

    # Calculate grid cell size in degrees
    mean_lat = (miny + maxy) / 2

    # Cell size in degrees (latitude is straightforward, longitude varies with latitude)
    cell_size_lat = km_to_degrees(cell_size_km, latitude=None)  # None means use latitude formula
    cell_size_lon = km_to_degrees(cell_size_km, latitude=mean_lat)

    logger.debug(
        f"Grid parameters: bbox={bbox}, cell_size_km={cell_size_km}, "
        f"cell_size_lat={cell_size_lat:.6f}°, cell_size_lon={cell_size_lon:.6f}°"
    )

    # Create grid cells
    cells = []
    cell_id = 0

    # Iterate through latitude (rows)
    current_y = miny
    row = 0
    while current_y < maxy:
        cell_maxy = min(current_y + cell_size_lat, maxy)

        # Iterate through longitude (columns)
        current_x = minx
        col = 0
        while current_x < maxx:
            cell_maxx = min(current_x + cell_size_lon, maxx)

            cell = {
                "minx": current_x,
                "miny": current_y,
                "maxx": cell_maxx,
                "maxy": cell_maxy,
                "cell_id": cell_id,
                "row": row,
                "col": col,
            }
            cells.append(cell)
            cell_id += 1
            col += 1
            current_x = cell_maxx

        row += 1
        current_y = cell_maxy

    logger.info(
        f"Created grid with {len(cells)} cells covering bbox "
        f"({maxx - minx:.2f}° x {maxy - miny:.2f}°)"
    )

    return cells, len(cells)


def cell_to_polygon(cell: Dict[str, float]) -> Dict[str, Any]:
    """
    Convert a grid cell to a GeoJSON Polygon geometry.

    Args:
        cell: Cell dict with bounds: {minx, miny, maxx, maxy}

    Returns:
        GeoJSON geometry dict with type "Polygon"
    """
    minx, miny, maxx, maxy = cell["minx"], cell["miny"], cell["maxx"], cell["maxy"]

    # GeoJSON polygon coordinates: [[[lon, lat], ...]]
    # Coordinates must form a closed ring (first and last are same)
    coordinates = [
        [
            [minx, miny],  # bottom-left
            [maxx, miny],  # bottom-right
            [maxx, maxy],  # top-right
            [minx, maxy],  # top-left
            [minx, miny],  # close ring
        ]
    ]

    return {
        "type": "Polygon",
        "coordinates": coordinates,
    }


def cells_to_geojson_features(
    cells_with_stats: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert grid cells with statistics to GeoJSON Feature objects.

    Args:
        cells_with_stats: List of cells, each with bounds, statistics, and bin info

    Returns:
        List of GeoJSON Feature dicts
    """
    features = []

    for cell in cells_with_stats:
        # Extract bounds and statistics
        bounds = {k: v for k, v in cell.items() if k in ["minx", "miny", "maxx", "maxy"]}
        stats = {k: v for k, v in cell.items() if k not in ["minx", "miny", "maxx", "maxy"]}

        # Create geometry
        geometry = cell_to_polygon(bounds)

        # Create feature
        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": stats,
        }
        features.append(feature)

    return features


def create_geojson(
    cells_with_stats: List[Dict[str, Any]],
    crs: str = "EPSG:4326",
) -> Dict[str, Any]:
    """
    Create a complete GeoJSON FeatureCollection from cells with statistics.

    Args:
        cells_with_stats: List of cells with bounds and statistics
        crs: Coordinate reference system (default: EPSG:4326 for WGS84)

    Returns:
        GeoJSON FeatureCollection dict
    """
    features = cells_to_geojson_features(cells_with_stats)

    return {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": crs},
        },
        "features": features,
    }
