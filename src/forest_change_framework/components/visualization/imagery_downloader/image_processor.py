"""Image processing utilities for downloading and saving Sentinel-2 imagery."""

import logging
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

try:
    import ee
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    import numpy as np
except ImportError:
    pass

logger = logging.getLogger(__name__)


def download_image(
    image: "ee.Image",
    geometry: "ee.Geometry",
    bands: list,
    scale: int = 10,
) -> Optional[Tuple[np.ndarray, Dict]]:
    """
    Download image data from Google Earth Engine.

    Args:
        image: ee.Image to download
        geometry: ee.Geometry defining region
        bands: List of band names to download
        scale: Resolution in meters

    Returns:
        Tuple of (data_array, metadata_dict) or None if failed
    """
    try:
        # Select bands
        image_subset = image.select(bands)

        # Get region bounds
        bbox = geometry.bounds().getInfo()

        # Prepare URL
        url = image_subset.getDownloadURL({
            "scale": scale,
            "crs": "EPSG:4326",
            "fileFormat": "GeoTIFF",
            "region": geometry,
        })

        logger.info(f"Download URL generated: {url[:50]}...")

        # Extract metadata
        metadata = {
            "bands": bands,
            "scale": scale,
            "crs": "EPSG:4326",
            "geometry": bbox,
            "timestamp": datetime.now().isoformat(),
        }

        # Note: Actual download would use requests or urllib
        # This is a placeholder for the architectural structure

        return None, metadata

    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


def reproject_image(
    input_path: Path,
    output_path: Path,
    target_crs: str = "EPSG:4326",
) -> bool:
    """
    Reproject a GeoTIFF to target CRS.

    Args:
        input_path: Path to input GeoTIFF
        output_path: Path to output GeoTIFF
        target_crs: Target coordinate reference system

    Returns:
        True if successful, False otherwise
    """
    try:
        with rasterio.open(input_path) as src:
            # Calculate transform
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )

            # Prepare output metadata
            kwargs = src.meta.copy()
            kwargs.update({
                "crs": target_crs,
                "transform": transform,
                "width": width,
                "height": height,
            })

            # Reproject
            with rasterio.open(output_path, "w", **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        rasterio.band(src, i),
                        rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.nearest,
                    )

        logger.info(f"Reprojected {input_path} to {target_crs}")
        return True

    except Exception as e:
        logger.error(f"Error reprojecting image: {e}")
        return False


def clip_to_bbox(
    input_path: Path,
    output_path: Path,
    bbox: Dict[str, float],
) -> bool:
    """
    Clip image to bounding box.

    Args:
        input_path: Path to input GeoTIFF
        output_path: Path to output GeoTIFF
        bbox: Bounding box {'minx': float, 'miny': float, 'maxx': float, 'maxy': float}

    Returns:
        True if successful, False otherwise
    """
    try:
        from rasterio.mask import mask

        with rasterio.open(input_path) as src:
            # Create geometry from bbox
            geom = {
                "type": "Polygon",
                "coordinates": [[
                    [bbox["minx"], bbox["miny"]],
                    [bbox["maxx"], bbox["miny"]],
                    [bbox["maxx"], bbox["maxy"]],
                    [bbox["minx"], bbox["maxy"]],
                    [bbox["minx"], bbox["miny"]],
                ]],
            }

            # Mask (clip) to geometry
            out_image, out_transform = mask(src, [geom], crop=True)

            # Prepare metadata
            out_meta = src.meta.copy()
            out_meta.update({
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
            })

            # Write clipped image
            with rasterio.open(output_path, "w", **out_meta) as dst:
                dst.write(out_image)

        logger.info(f"Clipped {input_path} to bbox")
        return True

    except Exception as e:
        logger.error(f"Error clipping image: {e}")
        return False


def save_metadata(output_dir: Path, metadata: Dict) -> bool:
    """
    Save metadata as JSON file.

    Args:
        output_dir: Output directory
        metadata: Metadata dictionary

    Returns:
        True if successful
    """
    try:
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"Saved metadata to {metadata_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")
        return False


def generate_thumbnail(
    input_path: Path,
    output_path: Path,
    rgb_bands: Tuple[int, int, int] = (3, 2, 1),  # R, G, B band indices
    size: Tuple[int, int] = (256, 256),
) -> bool:
    """
    Generate PNG thumbnail from GeoTIFF.

    Args:
        input_path: Path to input GeoTIFF
        output_path: Path to output PNG
        rgb_bands: Tuple of band indices for RGB
        size: Output size in pixels

    Returns:
        True if successful, False otherwise
    """
    try:
        import matplotlib.pyplot as plt
        from PIL import Image

        with rasterio.open(input_path) as src:
            # Read bands
            r = src.read(rgb_bands[0])
            g = src.read(rgb_bands[1])
            b = src.read(rgb_bands[2])

            # Normalize to 0-1
            r = (r - r.min()) / (r.max() - r.min() + 1e-8)
            g = (g - g.min()) / (g.max() - g.min() + 1e-8)
            b = (b - b.min()) / (b.max() - b.min() + 1e-8)

            # Stack into RGB image
            rgb = np.dstack([r, g, b])

            # Convert to 8-bit
            rgb_8bit = (rgb * 255).astype(np.uint8)

            # Save with PIL
            img = Image.fromarray(rgb_8bit, mode="RGB")
            img = img.resize(size, Image.Resampling.LANCZOS)
            img.save(output_path)

        logger.info(f"Generated thumbnail: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return False


def validate_tiff(file_path: Path) -> Tuple[bool, str]:
    """
    Validate a GeoTIFF file.

    Args:
        file_path: Path to GeoTIFF

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with rasterio.open(file_path) as src:
            if src.count == 0:
                return False, "No bands in GeoTIFF"
            if src.width < 10 or src.height < 10:
                return False, "Image too small"
            if src.crs is None:
                return False, "No CRS defined"
        return True, ""
    except Exception as e:
        return False, str(e)
