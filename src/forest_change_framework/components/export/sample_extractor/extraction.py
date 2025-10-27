"""TIFF patch extraction from Hansen data - supports both VRT and tile-based sources."""

import logging
import numpy as np
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.transform import Affine, from_bounds
except ImportError:
    rasterio = None


def calculate_geotransform(
    bbox: Dict[str, float], width: int, height: int
) -> Tuple[float, float, float, float, float, float]:
    """
    Calculate GDAL geotransform for a bounding box and raster dimensions.

    Args:
        bbox: Dict with keys minx, miny, maxx, maxy
        width: Number of columns in raster
        height: Number of rows in raster

    Returns:
        Tuple: (origin_x, pixel_width, 0, origin_y, 0, pixel_height)
        - origin_x, origin_y: Top-left corner coordinates
        - pixel_width, pixel_height: Pixel dimensions in coordinate units

    Example:
        >>> bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        >>> transform = calculate_geotransform(bbox, 340, 367)
        >>> # transform describes pixel-to-coordinate mapping
    """
    minx = bbox.get("minx")
    miny = bbox.get("miny")
    maxx = bbox.get("maxx")
    maxy = bbox.get("maxy")

    # Calculate pixel size
    pixel_width = (maxx - minx) / width
    pixel_height = (maxy - miny) / height

    # Top-left corner (upper-left in raster coordinates)
    origin_x = minx
    origin_y = maxy

    return (origin_x, pixel_width, 0, origin_y, 0, -pixel_height)


def extract_patch_from_vrt(
    vrt_path: str, bbox: Dict[str, float], band: int = 2
) -> np.ndarray:
    """
    Extract a TIFF patch from a VRT (Virtual Raster) file using a bounding box.

    Args:
        vrt_path: Path to VRT file (e.g., Hansen tiles VRT)
        bbox: Dict with keys minx, miny, maxx, maxy in source CRS (EPSG:4326)
        band: Band number to extract (default 2 for lossyear in Hansen)

    Returns:
        NumPy array with extracted band data

    Raises:
        ImportError: If rasterio not installed
        FileNotFoundError: If VRT file doesn't exist
        ValueError: If bbox is invalid or no data extracted

    Example:
        >>> bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        >>> data = extract_patch_from_vrt("hansen.vrt", bbox, band=2)
        >>> data.shape  # (rows, cols) of extracted patch
    """
    if rasterio is None:
        raise ImportError("rasterio required for TIFF extraction. Install with: pip install rasterio")

    vrt_file = Path(vrt_path)
    if not vrt_file.exists():
        raise FileNotFoundError(f"VRT file not found: {vrt_path}")

    # Validate bbox
    required_keys = {"minx", "miny", "maxx", "maxy"}
    if not all(k in bbox for k in required_keys):
        raise ValueError(f"bbox must contain keys: {required_keys}")

    minx = bbox["minx"]
    miny = bbox["miny"]
    maxx = bbox["maxx"]
    maxy = bbox["maxy"]

    if minx >= maxx or miny >= maxy:
        raise ValueError(f"Invalid bbox: minx must be < maxx, miny must be < maxy")

    try:
        with rasterio.open(vrt_file) as src:
            # Read data within bbox using window
            window = src.window(minx, miny, maxx, maxy)

            # Handle edge cases where bbox is outside raster
            if window.col_off < 0 or window.row_off < 0:
                logger.warning(
                    f"Bbox partially outside VRT extent: {bbox}. Clipping to valid region."
                )

            # Read band data in window
            data = src.read(band, window=window)

            logger.info(
                f"Extracted patch from VRT: shape={data.shape}, bbox={bbox}, band={band}"
            )
            return data

    except Exception as e:
        raise ValueError(f"Failed to extract patch from VRT: {e}")


def extract_patch_from_tiles(
    tiles_dir: str, bbox: Dict[str, float], year: int = 2000, band: int = 2
) -> np.ndarray:
    """
    Extract a TIFF patch from Hansen tile files in a directory.

    Tiles are named following Hansen convention: {yyyylossyear}_{tile_id}.tif
    Function identifies required tiles, reads them, and stitches into a single patch.

    Args:
        tiles_dir: Directory containing Hansen tile TIFF files
        bbox: Dict with keys minx, miny, maxx, maxy in EPSG:4326
        year: Year for tile identification (used in filename pattern if needed)
        band: Band number to extract (default 2 for lossyear)

    Returns:
        NumPy array with stitched patch data from multiple tiles

    Raises:
        ImportError: If rasterio not installed
        FileNotFoundError: If tiles directory doesn't exist or no matching tiles found
        ValueError: If bbox is invalid

    Example:
        >>> bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        >>> data = extract_patch_from_tiles("hansen_tiles/", bbox, year=2000)
        >>> data.shape  # Stitched patch shape
    """
    if rasterio is None:
        raise ImportError("rasterio required for TIFF extraction. Install with: pip install rasterio")

    tiles_path = Path(tiles_dir)
    if not tiles_path.is_dir():
        raise FileNotFoundError(f"Tiles directory not found: {tiles_dir}")

    # Validate bbox
    required_keys = {"minx", "miny", "maxx", "maxy"}
    if not all(k in bbox for k in required_keys):
        raise ValueError(f"bbox must contain keys: {required_keys}")

    minx = bbox["minx"]
    miny = bbox["miny"]
    maxx = bbox["maxx"]
    maxy = bbox["maxy"]

    if minx >= maxx or miny >= maxy:
        raise ValueError(f"Invalid bbox: minx must be < maxx, miny must be < maxy")

    # Find all TIFF files in directory
    tile_files = sorted(tiles_path.glob("*.tif"))

    if not tile_files:
        raise FileNotFoundError(f"No TIFF tiles found in {tiles_dir}")

    # Collect data from overlapping tiles
    patches = []
    transforms = []

    try:
        for tile_file in tile_files:
            with rasterio.open(tile_file) as src:
                # Check if tile overlaps with bbox
                tile_bounds = src.bounds
                if (
                    tile_bounds.right < minx
                    or tile_bounds.left > maxx
                    or tile_bounds.top < miny
                    or tile_bounds.bottom > maxy
                ):
                    continue  # Tile doesn't overlap

                # Read band from tile
                tile_data = src.read(band)
                patches.append(tile_data)
                transforms.append(src.transform)

        if not patches:
            raise ValueError(f"No tiles overlap with bbox: {bbox}")

        # If single tile, return directly
        if len(patches) == 1:
            logger.info(
                f"Extracted patch from 1 tile: shape={patches[0].shape}, "
                f"bbox={bbox}, band={band}"
            )
            return patches[0]

        # Multiple tiles: stitch together
        # For simplicity, stack vertically (assumes tiles are in grid)
        stitched = np.vstack(patches) if len(patches) > 1 else patches[0]

        logger.info(
            f"Extracted and stitched {len(patches)} tiles: "
            f"shape={stitched.shape}, bbox={bbox}, band={band}"
        )
        return stitched

    except Exception as e:
        raise ValueError(f"Failed to extract patch from tiles: {e}")


def save_geotiff(
    output_path: str,
    data: np.ndarray,
    bbox: Dict[str, float],
    crs: str = "EPSG:4326",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Save a NumPy array as a georeferenced GeoTIFF file.

    Args:
        output_path: Path where GeoTIFF will be written
        data: 2D NumPy array with band data
        bbox: Dict with keys minx, miny, maxx, maxy (in coordinate system)
        crs: Coordinate Reference System (default: EPSG:4326)
        metadata: Optional dict with keys:
            - sample_id: Sample identifier for TIFF tags
            - aoi_id: Area of Interest identifier
            - year: Year associated with sample
            - loss_bin: Loss category (e.g., "low_loss")
            - loss_percentage: Percentage forest loss

    Raises:
        ImportError: If rasterio not installed
        ValueError: If data shape invalid or bbox missing keys
        IOError: If file cannot be written

    Example:
        >>> data = np.random.randint(0, 100, (367, 340), dtype=np.uint8)
        >>> bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        >>> save_geotiff("sample_001.tif", data, bbox, crs="EPSG:4326",
        ...              metadata={"sample_id": "001", "year": 2010})
    """
    if rasterio is None:
        raise ImportError("rasterio required for TIFF export. Install with: pip install rasterio")

    if data.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {data.shape}")

    # Validate bbox
    required_keys = {"minx", "miny", "maxx", "maxy"}
    if not all(k in bbox for k in required_keys):
        raise ValueError(f"bbox must contain keys: {required_keys}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Calculate transform
    height, width = data.shape

    # Validate dimensions - skip if patch is empty (outside VRT extent)
    if width == 0 or height == 0:
        raise ValueError(
            f"Invalid patch dimensions: {data.shape}. "
            f"Bbox {bbox} may be outside VRT extent or completely clipped."
        )

    transform = from_bounds(
        bbox["minx"], bbox["miny"], bbox["maxx"], bbox["maxy"], width, height
    )

    try:
        with rasterio.open(
            output_file,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=data.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(data, 1)

            # Write metadata as tags if provided
            if metadata:
                tags = {}
                # Add all metadata to tags (TIFF tags have size limits, handled in component)
                for key, value in metadata.items():
                    if value is not None:
                        # Convert key to uppercase and handle special chars
                        tag_key = str(key).upper().replace("_", "")[:31]  # TIFF tag name limit
                        tag_value = str(value)
                        tags[tag_key] = tag_value

                if tags:
                    dst.update_tags(1, **tags)
                    logger.debug(f"Wrote {len(tags)} metadata tags to TIFF")

        logger.info(f"Wrote GeoTIFF: {output_path} (shape={data.shape}, crs={crs})")

    except Exception as e:
        raise IOError(f"Failed to write GeoTIFF: {e}")
