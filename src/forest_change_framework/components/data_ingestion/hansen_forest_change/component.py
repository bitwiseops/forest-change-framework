"""
Hansen forest change data ingestion component.

This component downloads and processes Hansen's Global Forest Change dataset
for a specified bounding box. It:

1. Downloads tile reference lists from Google Cloud Storage
2. Parses the lat/lon grid system to find tiles covering the bbox (tiles like "00N_000E")
3. Downloads required GeoTIFF files (lossyear, treecover2000, datamask layers)
4. Stacks the 3 layers for each tile (3-band GeoTIFF)
5. Creates a VRT (Virtual Raster) mosaic that references stacked tiles without materializing data

Memory efficiency: Zero materialization. Creates only lightweight VRT metadata file (~5KB).
Stacked tiles are stored on disk (~500MB for 16 tiles). The VRT describes how to combine
them without loading into memory. Rasterio and QGIS read the VRT and access tile data on-demand.

Each tile in Hansen's system is 10°×10° in the lat/lon grid system.

Configuration:
    - data_folder (str): Path to store downloaded tiles (default: "./data/hansen_tiles")
    - output_folder (str): Path to write VRT output files (default: "./data/hansen_output")
    - version (str): Hansen dataset version (default: "GFC-2024-v1.12")
    - timeout (int): Download timeout in seconds (default: 30)

Raises:
    ValueError: If bbox is invalid or no tiles found for area
    IOError: If downloads fail or VRT creation fails
    Exception: If rasterio operations fail

Example:
    >>> from forest_change_framework.core import BaseFramework
    >>> framework = BaseFramework()
    >>> component = framework.instantiate_component("data_ingestion", "hansen_forest_change")
    >>> bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}  # WGS84 coordinates
    >>> vrt_path, metadata = component.execute(bbox=bbox)
    >>> print(vrt_path)  # Path to VRT mosaic file
    /path/to/hansen_output/hansen_mosaic_20241025_120530.vrt
    >>> # Open in QGIS or read with rasterio
    >>> import rasterio
    >>> with rasterio.open(vrt_path) as src:
    ...     data = src.read()  # Reads from referenced tiles on-the-fly
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

try:
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.vrt import WarpedVRT
except ImportError:
    rasterio = None

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

from .grid_utils import bbox_to_tiles, parse_tile_list

logger = logging.getLogger(__name__)

# Google Cloud Storage base URL for Hansen data
GCS_BASE_URL = "https://storage.googleapis.com/earthenginepartners-hansen"

# Layer names in the dataset
LAYERS = ["treecover2000", "lossyear", "datamask"]


@register_component(
    category="data_ingestion",
    name="hansen_forest_change",
    version="1.0.0",
    description="Download and stack Hansen forest change geotiffs for a bounding box",
    metadata={
        "author": "Forest Change Framework",
        "tags": ["hansen", "forest-change", "geospatial"],
        "data_source": "earthenginepartners-hansen",
    },
)
class HansenForestChangeComponent(BaseComponent):
    """
    Hansen forest change data ingestion component.

    Downloads satellite-derived forest change data from Hansen's Global Forest Change
    dataset, organized by the MODIS tiling scheme.
    """

    def __init__(
        self,
        event_bus: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the Hansen component.

        Args:
            event_bus: Reference to the central event bus.
            config: Component configuration dictionary.
        """
        super().__init__(event_bus, config)
        self._data_folder: Optional[Path] = None
        self._output_folder: Optional[Path] = None
        self._version: str = "GFC-2024-v1.12"
        self._timeout: int = 30
        self._tiles_available: Dict[str, Any] = {}
        self._downloaded_tiles: Dict[str, Any] = {}
        logger.debug("HansenForestChangeComponent initialized")

    @property
    def name(self) -> str:
        """Get the component name."""
        return "hansen_forest_change"

    @property
    def version(self) -> str:
        """Get the component version."""
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the component with configuration.

        Args:
            config: Configuration dictionary with optional keys:
                - data_folder: Path to store downloaded tiles (default: "./data/hansen_tiles")
                - output_folder: Path to write mosaic GeoTIFF files (default: "./data/hansen_output")
                - version: Hansen dataset version (default: "GFC-2024-v1.12")
                - timeout: Download timeout in seconds (default: 30)

        Raises:
            ValueError: If configuration is invalid.
        """
        self._config = config

        # Get configuration values with defaults
        data_folder = self.get_config("data_folder", "./data/hansen_tiles")
        output_folder = self.get_config("output_folder", "./data/hansen_output")
        self._version = self.get_config("version", "GFC-2024-v1.12")
        self._timeout = self.get_config("timeout", 30)

        # Create data folder if it doesn't exist
        self._data_folder = Path(data_folder)
        try:
            self._data_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Data folder prepared: {self._data_folder}")
        except OSError as e:
            raise ValueError(f"Cannot create data folder {data_folder}: {str(e)}")

        # Create output folder if it doesn't exist
        self._output_folder = Path(output_folder)
        try:
            self._output_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output folder prepared: {self._output_folder}")
        except OSError as e:
            raise ValueError(f"Cannot create output folder {output_folder}: {str(e)}")

        logger.info(
            f"Component initialized with version={self._version}, "
            f"data_folder={self._data_folder}, output_folder={self._output_folder}, "
            f"timeout={self._timeout}"
        )

    def execute(
        self, bbox: Optional[Dict[str, float]] = None, biomes: Optional[list] = None, *args: Any, **kwargs: Any
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Execute the component's core functionality.

        Downloads Hansen forest change data for the specified bounding box,
        stacks the 3 layers (treecover2000, lossyear, datamask) for each tile,
        mosaics them together, and writes the mosaic to a GeoTIFF file.

        Args:
            bbox: Bounding box dict with keys minx, miny, maxx, maxy (WGS84).
            *args: Additional positional arguments (unused).
            **kwargs: Additional keyword arguments (bbox can also be here).

        Returns:
            Tuple of (vrt_file_path, metadata_dict) where:
            - vrt_file_path: Path to the VRT (Virtual Raster) XML file describing mosaic of 3 bands:
              * Band 1: treecover2000 (0-100%)
              * Band 2: lossyear (0=no loss, 1-21=loss year)
              * Band 3: datamask (0=invalid, 1=valid)
              The VRT references stacked tile files on disk without materializing data.
              Can be opened directly in QGIS or read with rasterio.
            - metadata_dict: Contains bbox, tiles, band info, CRS, bounds, output_path

        Raises:
            ValueError: If bbox is invalid or no tiles found.
            IOError: If downloads fail or VRT creation fails.

        Example:
            >>> bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}
            >>> vrt_path, metadata = component.execute(bbox=bbox)
            >>> print(vrt_path)
            /path/to/hansen_output/hansen_mosaic_20241025_120530.vrt
            >>> print(metadata["tiles_downloaded"])
            ['00N_000E', '10N_000E', '00N_010E', '10N_010E']
            >>> # Open in QGIS or read with rasterio
            >>> import rasterio
            >>> with rasterio.open(vrt_path) as src:
            ...     data = src.read()
        """
        try:
            # Get biomes or bbox from kwargs
            if biomes is None:
                biomes = kwargs.get("biomes")
            if bbox is None:
                bbox = kwargs.get("bbox")

            # Route to appropriate processing method
            if biomes:
                logger.info("Processing multiple regions via biomes config")
                return self._process_biomes(biomes)

            # Single bbox processing (original behavior)
            if bbox is None:
                raise ValueError("Either 'bbox' or 'biomes' is required")

            return self._execute_single_region(bbox)

        except Exception as e:
            logger.error(f"Component execution failed: {str(e)}", exc_info=True)

            # Publish error event
            self.publish_event(
                "hansen.error",
                {
                    "component": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def _execute_single_region(self, bbox: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
        """
        Execute Hansen data processing for a single bounding box region.

        This method encapsulates the core logic for downloading, stacking, and creating
        a VRT mosaic for a single bbox. It's used both by direct execute() calls and
        by _process_biomes() for multi-region processing.

        Args:
            bbox: Bounding box dict with keys minx, miny, maxx, maxy (WGS84).

        Returns:
            Tuple of (vrt_file_path, metadata_dict) where:
            - vrt_file_path: Path to the VRT file (as string)
            - metadata_dict: Contains bbox, tiles, band info, CRS, bounds, output_path

        Raises:
            ValueError: If bbox is invalid or no tiles found.
            IOError: If downloads fail or VRT creation fails.
        """
        try:
            logger.info(f"Starting Hansen data download for bbox: {bbox}")

            # Publish start event
            self.publish_event(
                "hansen.start",
                {
                    "component": self.name,
                    "bbox": bbox,
                    "version": self._version,
                },
            )

            # Step 1: Download and parse tile lists (reuse if already downloaded)
            if not self._tiles_available:
                logger.debug("Step 1: Downloading tile lists from Google Storage")
                self._tiles_available = self._download_and_parse_tile_lists()

                self.publish_event(
                    "hansen.tile_list_downloaded",
                    {
                        "component": self.name,
                        "available_tiles": len(self._tiles_available),
                    },
                )
            else:
                logger.debug("Step 1: Using cached tile lists")

            # Step 2: Find tiles covering the bbox
            logger.debug(f"Step 2: Finding tiles for bbox: {bbox}")
            required_tiles = bbox_to_tiles(bbox, self._tiles_available)

            if not required_tiles:
                raise ValueError(f"No tiles found for bbox: {bbox}")

            logger.info(f"Found {len(required_tiles)} tiles covering bbox")

            # Step 3: Download tiles
            logger.debug(f"Step 3: Downloading {len(required_tiles)} tiles")
            self._downloaded_tiles = self._download_tiles(required_tiles)

            if not self._downloaded_tiles:
                raise IOError("Failed to download any tiles")

            # Step 4: Create VRT mosaic from stacked tiles
            logger.debug("Step 4: Creating VRT mosaic from stacked tiles")
            vrt_path, mosaic_info = self._create_vrt_mosaic()

            if vrt_path is None:
                raise IOError("Failed to create VRT mosaic")

            # Prepare metadata
            metadata = self._prepare_metadata(bbox, required_tiles, vrt_path, mosaic_info)

            # Publish success event
            self.publish_event(
                "hansen.complete",
                {
                    "component": self.name,
                    "bbox": bbox,
                    "tiles_stacked": len(self._downloaded_tiles),
                    "output_path": str(vrt_path),
                    "shape": mosaic_info["shape"],
                    "crs": mosaic_info["crs"],
                    "vrt_mosaic": True,
                },
            )

            logger.info(
                f"Component executed successfully. Created VRT mosaic for {len(self._downloaded_tiles)} "
                f"stacked tiles with shape {mosaic_info['shape']} and 3 bands. "
                f"Output: {vrt_path}"
            )

            return str(vrt_path), metadata

        except Exception as e:
            logger.error(f"Single region processing failed for bbox {bbox}: {str(e)}", exc_info=True)

            # Publish error event
            self.publish_event(
                "hansen.error",
                {
                    "component": self.name,
                    "bbox": bbox,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def _process_biomes(self, biomes: list) -> Tuple[str, Dict[str, Any]]:
        """
        Process multiple regions organized by biomes.

        For each biome and region, downloads tiles, stacks bands, and creates a VRT.
        Outputs are organized as: output/biome_name/region_name.vrt

        Args:
            biomes: List of biome configs, each with regions and their bboxes.

        Returns:
            Tuple of (output_folder_path, metadata_dict) where:
            - output_folder_path: Path to biomes output folder
            - metadata_dict: Summary of all processed regions

        Raises:
            ValueError: If biomes config is invalid
            IOError: If processing fails
        """
        from datetime import datetime

        try:
            if not biomes or not isinstance(biomes, list):
                raise ValueError("'biomes' must be a list of biome configs")

            # Create biomes output folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            biomes_folder = self._output_folder / f"hansen_biomes_{timestamp}"
            biomes_folder.mkdir(parents=True, exist_ok=True)

            logger.info(f"Processing {len(biomes)} biomes into {biomes_folder}")

            # Track results
            results = {
                "timestamp": timestamp,
                "output_folder": str(biomes_folder),
                "biomes_processed": 0,
                "regions_processed": 0,
                "regions_failed": 0,
                "biome_details": [],
            }

            # Process each biome
            for biome_idx, biome_config in enumerate(biomes, 1):
                biome_name = biome_config.get("name", f"biome_{biome_idx}")
                regions = biome_config.get("regions", [])

                logger.info(f"Processing biome {biome_idx}/{len(biomes)}: {biome_name}")

                biome_folder = biomes_folder / biome_name
                biome_folder.mkdir(parents=True, exist_ok=True)

                biome_result = {
                    "name": biome_name,
                    "regions": [],
                }

                # Process each region in the biome
                for region_idx, region_config in enumerate(regions, 1):
                    region_name = region_config.get("name", f"region_{region_idx}")
                    bbox = region_config.get("bbox")

                    if not bbox or len(bbox) != 4:
                        logger.warning(f"Skipping region {region_name}: invalid bbox {bbox}")
                        biome_result["regions"].append({
                            "name": region_name,
                            "status": "failed",
                            "error": "Invalid bbox"
                        })
                        results["regions_failed"] += 1
                        continue

                    try:
                        logger.info(f"  Processing region: {region_name} bbox={bbox}")

                        # Convert bbox list to dict
                        bbox_dict = {
                            "minx": bbox[0],
                            "miny": bbox[1],
                            "maxx": bbox[2],
                            "maxy": bbox[3],
                        }

                        # Execute single-bbox processing for this region
                        vrt_path, region_metadata = self._execute_single_region(bbox_dict)

                        if vrt_path:
                            # Move VRT to biome folder with region name
                            region_vrt_path = biome_folder / f"{region_name}.vrt"
                            import shutil
                            # Copy VRT file
                            shutil.copy(vrt_path, region_vrt_path)
                            logger.debug(f"Saved region VRT: {region_vrt_path}")

                            biome_result["regions"].append({
                                "name": region_name,
                                "status": "success",
                                "vrt_path": str(region_vrt_path),
                                "bbox": bbox_dict,
                                "shape": region_metadata.get("output_shape"),
                                "crs": region_metadata.get("output_crs"),
                            })
                            results["regions_processed"] += 1

                        else:
                            raise IOError(f"Failed to create VRT for {region_name}")

                    except Exception as e:
                        logger.error(f"Failed to process region {region_name}: {str(e)}")
                        biome_result["regions"].append({
                            "name": region_name,
                            "status": "failed",
                            "error": str(e),
                        })
                        results["regions_failed"] += 1
                        continue

                results["biome_details"].append(biome_result)
                results["biomes_processed"] += 1

            # Publish completion event
            self.publish_event(
                "hansen.complete",
                {
                    "component": self.name,
                    "mode": "biomes",
                    "biomes_processed": results["biomes_processed"],
                    "regions_processed": results["regions_processed"],
                    "regions_failed": results["regions_failed"],
                    "output_path": str(biomes_folder),
                },
            )

            logger.info(
                f"Biome processing complete: {results['biomes_processed']} biomes, "
                f"{results['regions_processed']} regions processed, "
                f"{results['regions_failed']} failed"
            )

            return str(biomes_folder), results

        except Exception as e:
            logger.error(f"Biome processing failed: {str(e)}", exc_info=True)
            self.publish_event(
                "hansen.error",
                {
                    "component": self.name,
                    "mode": "biomes",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def cleanup(self) -> None:
        """
        Clean up component resources.

        Clears internal tile caches. Mosaic files are written to disk and
        not held in memory, so no special cleanup is needed.
        """
        self._tiles_available.clear()
        self._downloaded_tiles.clear()
        logger.debug("Component cleaned up")

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _download_and_parse_tile_lists(self) -> Dict[str, Any]:
        """
        Download tile reference lists from Google Storage.

        Downloads the tile list files for each layer (treecover2000, lossyear, datamask)
        and parses them to build a complete inventory of available tiles.

        Returns:
            Dictionary mapping tile IDs to their bounds.

        Raises:
            IOError: If tile lists cannot be downloaded.
        """
        if requests is None:
            raise ImportError(
                "The 'requests' library is required for hansen_forest_change component. "
                "Install it with: pip install requests"
            )

        all_tiles = {}

        for layer in LAYERS:
            url = (
                f"{GCS_BASE_URL}/{self._version}/{layer}.txt"
            )

            try:
                logger.debug(f"Downloading tile list: {url}")

                response = requests.get(url, timeout=self._timeout)
                response.raise_for_status()

                # Parse the tile list
                lines = response.text.strip().split("\n")
                tiles = parse_tile_list(lines)

                # Merge with all_tiles (use union of all available tiles)
                all_tiles.update(tiles)

                logger.info(f"Downloaded tile list for {layer}: {len(tiles)} tiles")

            except Exception as e:
                logger.error(f"Failed to download tile list from {url}: {str(e)}")
                raise IOError(f"Failed to download tile list for {layer}") from e

        logger.info(f"Total unique tiles available: {len(all_tiles)}")
        return all_tiles

    def _download_tiles(self, tile_ids: list) -> Dict[str, Dict[str, str]]:
        """
        Download GeoTIFF files for required tiles.

        For each tile, downloads all 3 layers (treecover2000, lossyear, datamask).
        Skips download if file already exists locally.

        Args:
            tile_ids: List of tile IDs to download (e.g., ["h18v07", "h18v08"]).

        Returns:
            Dictionary mapping tile_id -> {layer: filepath} for successfully processed tiles.

        Raises:
            IOError: If critical downloads fail.
        """
        downloaded = {}
        failed_tiles = []

        for idx, tile_id in enumerate(tile_ids):
            try:
                # Publish progress
                progress = ((idx + 1) / len(tile_ids)) * 100
                self.publish_event(
                    "hansen.tile_downloading",
                    {
                        "component": self.name,
                        "tile_id": tile_id,
                        "progress": progress,
                        "current": idx + 1,
                        "total": len(tile_ids),
                    },
                )

                tile_data = {}

                # Download each layer for this tile
                for layer in LAYERS:
                    filepath = self._download_single_file(tile_id, layer)
                    if filepath:
                        tile_data[layer] = filepath
                    else:
                        logger.warning(f"Failed to get {layer} for tile {tile_id}")

                if tile_data:
                    downloaded[tile_id] = tile_data
                else:
                    failed_tiles.append(tile_id)

            except Exception as e:
                logger.warning(f"Error processing tile {tile_id}: {str(e)}")
                failed_tiles.append(tile_id)

        if failed_tiles:
            logger.warning(f"Failed to process {len(failed_tiles)} tiles: {failed_tiles}")

        return downloaded

    def _download_single_file(self, tile_id: str, layer: str) -> Optional[str]:
        """
        Download a single GeoTIFF file.

        Constructs the download URL, checks if file exists locally, and downloads
        if necessary.

        Args:
            tile_id: Tile ID (e.g., "00N_000E").
            layer: Layer name (e.g., "treecover2000").

        Returns:
            Path to the downloaded file, or None if download failed.
        """
        # Construct file path
        tile_folder = self._data_folder / tile_id
        filename = f"Hansen_GFC-2024-v1.12_{layer}_{tile_id}.tif"
        filepath = tile_folder / filename

        # Check if file already exists
        if filepath.exists():
            logger.debug(f"File already exists, skipping: {filepath}")
            return str(filepath)

        # Construct download URL
        # Format: Hansen_GFC-2024-v1.12_{layer}_{lat}_{lon}.tif
        url = f"{GCS_BASE_URL}/{self._version}/{filename}"

        try:
            # Create tile folder
            tile_folder.mkdir(parents=True, exist_ok=True)

            # Download file
            logger.debug(f"Downloading: {url}")
            response = requests.get(url, timeout=self._timeout, stream=True)
            response.raise_for_status()

            # Write file
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.warning(f"Failed to download {layer} for {tile_id}: {str(e)}")
            # Clean up partial file if it exists
            if filepath.exists():
                filepath.unlink()
            return None

    def _create_vrt_mosaic(self) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
        """
        Create a VRT (Virtual Raster) mosaic from stacked tiles.

        Creates an XML-based virtual raster description that references stacked
        tile files without materializing the data. The VRT can be read by rasterio
        and QGIS to access the mosaic on-the-fly.

        Returns:
            Tuple of (vrt_file_path, mosaic_info) where:
            - vrt_file_path: Path to .vrt XML file (lightweight metadata), or None if creation failed
            - mosaic_info: Dict with 'shape' and 'crs' info about the mosaic
                - Band 1: treecover2000 (0-100%)
                - Band 2: lossyear (0=no loss, 1-21=year of loss)
                - Band 3: datamask (0=invalid, 1=valid)

        Note: The VRT references stacked tile files on disk. The actual data
        is read lazily when accessed via rasterio or QGIS.

        Raises:
            IOError: If stacked tiles cannot be read or VRT cannot be created.
        """
        if rasterio is None:
            raise ImportError(
                "The 'rasterio' library is required for hansen_forest_change component. "
                "Install it with: pip install rasterio"
            )

        try:
            from datetime import datetime
            from xml.etree.ElementTree import Element, SubElement, ElementTree

            if not self._downloaded_tiles:
                logger.error("No downloaded tiles to stack")
                return None, None

            logger.debug(f"Creating stacks for {len(self._downloaded_tiles)} tiles")

            # Create temporary stacked tile files on disk
            temp_stacked_tiles = []
            stacked_tile_metadata = {}  # Store metadata for VRT creation

            for tile_id, layers in self._downloaded_tiles.items():
                try:
                    # Get paths for each layer
                    layer_files = {}
                    for layer in LAYERS:
                        if layer in layers and Path(layers[layer]).exists():
                            layer_files[layer] = layers[layer]

                    # Skip if not all layers available
                    if len(layer_files) < 3:
                        logger.warning(f"Tile {tile_id} missing some layers, skipping")
                        continue

                    # Read all 3 layers (band by band, not all at once)
                    band_data = {}
                    metadata = None

                    for layer in LAYERS:
                        with rasterio.open(layer_files[layer]) as src:
                            # Only read the band data (avoid loading entire array into memory at once)
                            band_data[layer] = src.read(1)
                            if metadata is None:
                                metadata = src.profile.copy()
                                logger.debug(
                                    f"Tile {tile_id}: {src.height}x{src.width}, "
                                    f"CRS={src.crs}, bounds={src.bounds}"
                                )

                    # Stack bands: [treecover2000, lossyear, datamask]
                    import numpy as np
                    stacked_array = np.array([band_data[layer] for layer in LAYERS])

                    # Write stacked tile to file on disk
                    temp_tile_path = self._data_folder / f"stacked_{tile_id}.tif"

                    # Update metadata for 3 bands
                    metadata["count"] = 3
                    metadata["dtype"] = stacked_array.dtype

                    with rasterio.open(temp_tile_path, "w", **metadata) as dst:
                        dst.write(stacked_array)

                    logger.debug(f"Wrote stacked tile to disk: {temp_tile_path}")
                    temp_stacked_tiles.append(temp_tile_path)

                    # Store metadata for VRT creation (no need to keep dataset open)
                    stacked_tile_metadata[tile_id] = {
                        "path": str(temp_tile_path),
                        "transform": metadata["transform"],
                        "crs": metadata["crs"],
                        "width": metadata["width"],
                        "height": metadata["height"],
                        "bounds": rasterio.transform.array_bounds(
                            metadata["height"], metadata["width"], metadata["transform"]
                        )
                    }

                except Exception as e:
                    logger.warning(f"Failed to stack tile {tile_id}: {str(e)}")
                    continue

            if not stacked_tile_metadata:
                logger.error("No stacked tiles created")
                return None, None

            logger.info(f"Creating VRT mosaic for {len(stacked_tile_metadata)} stacked tiles")

            try:
                # Create VRT (Virtual Raster) that references stacked tiles
                # No data materialization, just XML metadata describing the mosaic

                # Calculate overall bounds
                all_bounds = [meta["bounds"] for meta in stacked_tile_metadata.values()]
                overall_minx = min(b[0] for b in all_bounds)
                overall_miny = min(b[1] for b in all_bounds)
                overall_maxx = max(b[2] for b in all_bounds)
                overall_maxy = max(b[3] for b in all_bounds)

                # Get reference metadata from first tile
                first_meta = next(iter(stacked_tile_metadata.values()))
                crs = first_meta["crs"]
                pixel_width = first_meta["transform"].a
                pixel_height = first_meta["transform"].e

                # Calculate VRT size
                vrt_width = int((overall_maxx - overall_minx) / pixel_width)
                vrt_height = int((overall_maxy - overall_miny) / (-pixel_height))

                logger.debug(f"VRT bounds: ({overall_minx}, {overall_miny}) to ({overall_maxx}, {overall_maxy})")
                logger.debug(f"VRT size: {vrt_width}x{vrt_height}")

                # Create VRT XML
                vrt = Element("VRTDataset")
                vrt.set("rasterXSize", str(vrt_width))
                vrt.set("rasterYSize", str(vrt_height))

                # Add geotransform
                geo_transform = SubElement(vrt, "GeoTransform")
                geo_transform.text = f"{overall_minx}, {pixel_width}, 0, {overall_maxy}, 0, {pixel_height}"

                # Add projection
                srs = SubElement(vrt, "SRS")
                srs.text = str(crs)

                # Add bands (3 bands for 3-band stacked tiles)
                for band_num in range(1, 4):
                    band = SubElement(vrt, "VRTRasterBand")
                    band.set("dataType", "Byte")  # GDAL uses "Byte" for uint8
                    band.set("band", str(band_num))

                    # Add each stacked tile as a source for this band
                    for tile_id, tile_meta in sorted(stacked_tile_metadata.items()):
                        source = SubElement(band, "SimpleSource")

                        file_ref = SubElement(source, "SourceFilename")
                        file_ref.set("relativeToVRT", "0")
                        file_ref.text = tile_meta["path"]

                        source_band = SubElement(source, "SourceBand")
                        source_band.text = str(band_num)

                        # Calculate source window in VRT coordinates
                        bounds = tile_meta["bounds"]
                        src_minx, src_miny, src_maxx, src_maxy = bounds

                        # VRT pixel coordinates for this tile
                        dst_xoff = int((src_minx - overall_minx) / pixel_width)
                        dst_yoff = int((overall_maxy - src_maxy) / (-pixel_height))

                        src_rect = SubElement(source, "SrcRect")
                        src_rect.set("xOff", "0")
                        src_rect.set("yOff", "0")
                        src_rect.set("xSize", str(tile_meta["width"]))
                        src_rect.set("ySize", str(tile_meta["height"]))

                        dst_rect = SubElement(source, "DstRect")
                        dst_rect.set("xOff", str(dst_xoff))
                        dst_rect.set("yOff", str(dst_yoff))
                        dst_rect.set("xSize", str(tile_meta["width"]))
                        dst_rect.set("ySize", str(tile_meta["height"]))

                # Generate VRT filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                vrt_filename = f"hansen_mosaic_{timestamp}.vrt"
                vrt_path = self._output_folder / vrt_filename

                # Write VRT file
                vrt_tree = ElementTree(vrt)
                vrt_tree.write(vrt_path, encoding="utf-8", xml_declaration=True)

                logger.info(
                    f"Created VRT mosaic: {vrt_path} "
                    f"(size: {vrt_width}x{vrt_height}, crs: {crs})"
                )

                # Prepare mosaic info
                mosaic_info = {
                    "shape": (vrt_height, vrt_width),
                    "crs": str(crs),
                    "tiles_referenced": len(stacked_tile_metadata),
                }

                return vrt_path, mosaic_info

            finally:
                # No datasets to close (VRT doesn't keep files open)
                # Stacked tile files are left on disk as they're referenced by VRT
                logger.debug(f"VRT creation complete. Stacked tiles preserved at {self._data_folder}")

        except Exception as e:
            logger.error(f"Failed to create mosaic stack: {str(e)}", exc_info=True)
            return None, None

    def _prepare_metadata(
        self, bbox: Dict[str, float], tile_ids: list, output_path: Path, mosaic_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare metadata dictionary about the download operation and output mosaic.

        Args:
            bbox: Input bounding box.
            tile_ids: List of tiles that were requested.
            output_path: Path to the output mosaic GeoTIFF file.
            mosaic_info: Dictionary with mosaic shape and CRS info.

        Returns:
            Dictionary with metadata about the operation and mosaic bands.
        """
        return {
            "bbox": bbox,
            "version": self._version,
            "tiles_requested": tile_ids,
            "tiles_downloaded": list(self._downloaded_tiles.keys()),
            "tiles_failed": [t for t in tile_ids if t not in self._downloaded_tiles],
            "output_path": str(output_path),
            "output_shape": mosaic_info["shape"],
            "output_crs": mosaic_info["crs"],
            "data_folder": str(self._data_folder),
            "output_folder": str(self._output_folder),
            "layers": LAYERS,
            "band_info": {
                "band_1": {"name": "treecover2000", "description": "Tree cover in year 2000 (0-100%)"},
                "band_2": {"name": "lossyear", "description": "Year of loss (0=no loss, 1-21=loss year)"},
                "band_3": {"name": "datamask", "description": "Data mask (0=invalid, 1=valid)"},
            },
        }
