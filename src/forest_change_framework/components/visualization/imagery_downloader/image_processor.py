"""Image processing utilities for downloading and saving Sentinel-2 imagery."""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import ee
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    import numpy as np
    import requests
except ImportError:
    pass

logger = logging.getLogger(__name__)


def save_imagery(
    image: "ee.Image",
    output_dir: Path,
    imagery_type: str,
    output_formats: List[str],
    target_crs: str = "EPSG:4326",
    scale: int = 10,
) -> Dict[str, str]:
    """
    Download image from Google Earth Engine and save to disk.

    Handles downloading a Sentinel-2 image from GEE and saving as both
    GeoTIFF (preserves metadata) and PNG (for visualization/ML).

    Args:
        image: ee.Image to download
        output_dir: Output directory for saved files
        imagery_type: Type of imagery ("pre" or "post") for naming
        output_formats: List of output formats ["geotiff", "png"]
        target_crs: Target CRS for output (default EPSG:4326)
        scale: Resolution in meters (default 10 for Sentinel-2)

    Returns:
        Dictionary mapping format to file path {geotiff: str, png: str, ...}

    Raises:
        ImportError: If required dependencies not available
        RuntimeError: If download fails
        IOError: If file writing fails
    """
    try:
        from io import BytesIO
        from PIL import Image
    except ImportError:
        raise ImportError("PIL required for imagery saving. Install with: pip install Pillow")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {}

    try:
        # Get geometry from image
        geometry = image.geometry()

        # Prepare download URL
        download_params = {
            "scale": scale,
            "crs": target_crs,
            "fileFormat": "GeoTIFF",
            "region": geometry,
        }

        url = image.getDownloadURL(download_params)
        logger.info(f"Downloading {imagery_type} imagery: {url[:80]}...")

        # Download the GeoTIFF with timeout
        response = requests.get(url, timeout=300)
        if response.status_code != 200:
            raise RuntimeError(
                f"Download failed with status {response.status_code}: {response.text[:200]}"
            )

        geotiff_data = BytesIO(response.content)
        geotiff_bytes = geotiff_data.getvalue()

        # Save GeoTIFF if requested
        if "geotiff" in output_formats:
            geotiff_path = output_dir / f"{imagery_type}.tif"
            with open(geotiff_path, "wb") as f:
                f.write(geotiff_bytes)
            logger.info(f"Saved GeoTIFF: {geotiff_path}")
            result["geotiff"] = str(geotiff_path)

        # Save PNG if requested
        if "png" in output_formats:
            png_path = output_dir / f"{imagery_type}.png"

            try:
                # Read GeoTIFF from memory and create PNG
                with MemoryFile(geotiff_bytes) as memfile:
                    with memfile.open() as src:
                        # Read first 3 bands for RGB
                        try:
                            if src.count >= 3:
                                # Read as float for normalization
                                r = src.read(1).astype(np.float32)
                                g = src.read(2).astype(np.float32)
                                b = src.read(3).astype(np.float32)
                            else:
                                # Fallback: repeat first band
                                band = src.read(1).astype(np.float32)
                                r = g = b = band

                            # Normalize each band to 0-255
                            def normalize_band(band_data):
                                band_min = np.nanmin(band_data)
                                band_max = np.nanmax(band_data)
                                if band_max == band_min:
                                    return np.zeros_like(band_data, dtype=np.uint8)
                                normalized = (band_data - band_min) / (band_max - band_min)
                                return (normalized * 255).astype(np.uint8)

                            r_norm = normalize_band(r)
                            g_norm = normalize_band(g)
                            b_norm = normalize_band(b)

                            # Stack into RGB
                            rgb = np.dstack([r_norm, g_norm, b_norm])

                            # Save with PIL
                            img = Image.fromarray(rgb, mode="RGB")
                            img.save(png_path)

                            logger.info(f"Saved PNG: {png_path}")
                            result["png"] = str(png_path)

                        except Exception as e:
                            logger.warning(f"Failed to create PNG from bands: {e}")
                            # Try to save grayscale from first band as fallback
                            try:
                                band1 = src.read(1).astype(np.uint8)
                                img = Image.fromarray(band1, mode="L")
                                img.save(png_path)
                                logger.info(f"Saved grayscale PNG: {png_path}")
                                result["png"] = str(png_path)
                            except Exception as e2:
                                logger.warning(f"Failed to create grayscale PNG: {e2}")

            except Exception as e:
                logger.warning(f"Failed to create PNG: {e}")

        return result

    except Exception as e:
        logger.error(f"Error saving imagery: {e}", exc_info=True)
        raise


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


def save_metadata(metadata: Dict, output_path) -> bool:
    """
    Save metadata as JSON file.

    Args:
        metadata: Metadata dictionary
        output_path: Path to output JSON file

    Returns:
        True if successful
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"Saved metadata to {output_path}")
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
