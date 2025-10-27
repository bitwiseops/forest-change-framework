"""AOI Sampler component for sampling and analyzing areas of interest."""

import logging
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import rasterio
    import numpy as np
except ImportError:
    rasterio = None
    np = None

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

from .grid_utils import create_grid_cells, cell_to_polygon, create_geojson
from .statistics import calculate_cell_statistics, aggregate_statistics
from .binning import apply_binning_and_filtering
from .visualization import create_yearly_maps, generate_map_summary

logger = logging.getLogger(__name__)


@register_component(
    category="analysis",
    name="aoi_sampler",
    version="1.0.0",
    description="Sample areas of interest from Hansen VRT data and calculate forest loss statistics",
    metadata={
        "author": "Forest Change Framework",
        "tags": ["aoi", "sampling", "hansen", "forest-loss"],
        "input_type": "raster_vrt",
        "output_type": "geojson",
    },
)
class AoiSamplerComponent(BaseComponent):
    """
    AOI Sampler component.

    Samples regular grid cells from a Hansen VRT mosaic, calculates forest loss
    and data validity statistics per cell, and bins AOIs by loss percentage ranges.

    Configuration:
        grid_cell_size_km (float): Size of each grid cell in kilometers (default: 1.0)
        min_validity_threshold (float): Minimum data validity % for inclusion (default: 80.0)
        loss_bins (list): List of bin dicts with name, min, max (required)
        include_loss_by_year (bool): Include loss breakdown by year (default: True)
        keep_invalid_aois (bool): Keep invalid AOIs but mark them (default: False)
        output_format (str): Output format - geojson or json (default: geojson)
    """

    def __init__(
        self,
        event_bus: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the AOI Sampler component."""
        super().__init__(event_bus, config)
        self._grid_cell_size_km: float = 1.0
        self._min_validity_threshold: float = 80.0
        self._loss_bins: list = []
        self._include_loss_by_year: bool = True
        self._keep_invalid_aois: bool = False
        self._output_format: str = "geojson"
        self._create_visualizations: bool = False
        self._visualization_dpi: int = 150
        logger.debug("AoiSamplerComponent initialized")

    @property
    def name(self) -> str:
        """Get the component name."""
        return "aoi_sampler"

    @property
    def version(self) -> str:
        """Get the component version."""
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the component with configuration.

        Args:
            config: Configuration dict with keys:
                - grid_cell_size_km: Grid cell size in km (default: 1.0)
                - min_validity_threshold: Min validity % (default: 80.0)
                - loss_bins: List of bin dicts with name, min, max
                - include_loss_by_year: Include loss by year (default: True)
                - keep_invalid_aois: Keep invalid AOIs (default: False)
                - output_format: Output format (default: geojson)
                - create_visualizations: Generate yearly maps (default: False)
                - visualization_dpi: Map resolution in DPI (default: 150)

        Raises:
            ValueError: If configuration is invalid
        """
        self._config = config

        # Get configuration values with defaults
        self._grid_cell_size_km = self.get_config("grid_cell_size_km", 1.0)
        self._min_validity_threshold = self.get_config("min_validity_threshold", 80.0)
        self._loss_bins = self.get_config("loss_bins", [])
        self._include_loss_by_year = self.get_config("include_loss_by_year", True)
        self._keep_invalid_aois = self.get_config("keep_invalid_aois", False)
        self._output_format = self.get_config("output_format", "geojson")
        self._create_visualizations = self.get_config("create_visualizations", False)
        self._visualization_dpi = self.get_config("visualization_dpi", 150)

        # Validate grid cell size
        if self._grid_cell_size_km <= 0:
            raise ValueError(
                f"grid_cell_size_km must be positive, got {self._grid_cell_size_km}"
            )

        # Validate validity threshold
        if not (0 <= self._min_validity_threshold <= 100):
            raise ValueError(
                f"min_validity_threshold must be 0-100, got {self._min_validity_threshold}"
            )

        # Validate loss bins
        if not self._loss_bins:
            raise ValueError("loss_bins configuration is required")

        if not isinstance(self._loss_bins, list):
            raise ValueError("loss_bins must be a list of dicts")

        logger.info(
            f"Component initialized: grid_cell_size_km={self._grid_cell_size_km}, "
            f"min_validity_threshold={self._min_validity_threshold}%, "
            f"loss_bins={len(self._loss_bins)}, "
            f"include_loss_by_year={self._include_loss_by_year}"
        )

    def execute(
        self, vrt_path: str, output_path: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Execute the AOI sampler component.

        Samples grid cells from Hansen VRT, calculates statistics, bins by loss,
        and outputs GeoJSON with sampled AOIs.

        Args:
            vrt_path: Path to Hansen VRT file
            output_path: Output file path (optional, auto-generated if not provided)
            **kwargs: Additional config overrides

        Returns:
            Tuple of (output_file_path, metadata_dict) where:
            - output_file_path: Path to generated GeoJSON file
            - metadata_dict: Contains summary statistics and processing info

        Raises:
            ValueError: If vrt_path is invalid or config is invalid
            IOError: If VRT cannot be opened or output cannot be written
        """
        if rasterio is None or np is None:
            raise ImportError(
                "rasterio and numpy are required for aoi_sampler. "
                "Install with: pip install rasterio numpy"
            )

        try:
            # Validate VRT path
            vrt_file = Path(vrt_path)
            if not vrt_file.exists():
                raise ValueError(f"VRT file not found: {vrt_path}")

            logger.info(f"Starting AOI sampling from VRT: {vrt_path}")

            # Publish start event
            self.publish_event(
                "aoi_sampler.start",
                {
                    "component": self.name,
                    "vrt_path": vrt_path,
                    "grid_cell_size_km": self._grid_cell_size_km,
                    "loss_bins": self._loss_bins,
                },
            )

            # Step 1: Open VRT and get bounds
            logger.debug("Step 1: Opening VRT and retrieving bounds")
            with rasterio.open(vrt_path) as src:
                bounds = src.bounds  # (left, bottom, right, top)
                crs = src.crs
                bbox = {
                    "minx": bounds.left,
                    "miny": bounds.bottom,
                    "maxx": bounds.right,
                    "maxy": bounds.top,
                }

                logger.info(f"VRT bounds: {bbox}, CRS: {crs}")

                # Step 2: Create grid cells
                logger.debug("Step 2: Creating grid cells")
                cells, cell_count = create_grid_cells(bbox, self._grid_cell_size_km)

                self.publish_event(
                    "aoi_sampler.grid_created",
                    {
                        "component": self.name,
                        "cell_count": cell_count,
                        "grid_cell_size_km": self._grid_cell_size_km,
                    },
                )

                # Step 3: Calculate statistics for each cell
                logger.debug(f"Step 3: Calculating statistics for {cell_count} cells")
                aois = self._process_cells(src, cells, bbox)

                self.publish_event(
                    "aoi_sampler.statistics_calculated",
                    {
                        "component": self.name,
                        "processed_cells": len(aois),
                    },
                )

                # Step 4: Bin and filter AOIs
                logger.debug("Step 4: Binning and filtering AOIs")
                binned_aois, bin_summary = apply_binning_and_filtering(
                    aois,
                    self._loss_bins,
                    validity_threshold=self._min_validity_threshold / 100.0,  # Convert % to 0-1
                    keep_invalid_aois=self._keep_invalid_aois,
                )

                self.publish_event(
                    "aoi_sampler.binned",
                    {
                        "component": self.name,
                        "valid_aois": bin_summary["valid_aois"],
                        "invalid_aois": bin_summary["invalid_aois"],
                        "bin_summary": bin_summary["bin_summary"],
                    },
                )

                # Step 5: Create GeoJSON output
                logger.debug("Step 5: Creating GeoJSON output")
                geojson_data = create_geojson(binned_aois, crs=str(crs))

                # Step 6: Write output file
                if output_path is None:
                    from datetime import datetime

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = (
                        Path.cwd()
                        / "aoi_samples"
                        / "aois"
                        / f"aoi_samples_{timestamp}.geojson"
                    )
                else:
                    output_file = Path(output_path)

                output_file.parent.mkdir(parents=True, exist_ok=True)

                logger.debug(f"Step 6: Writing GeoJSON to {output_file}")
                with open(output_file, "w") as f:
                    json.dump(geojson_data, f, indent=2)

                logger.info(f"Wrote {len(binned_aois)} AOIs to {output_file}")

                # Prepare metadata
                metadata = {
                    "output_path": str(output_file),
                    "vrt_path": vrt_path,
                    "bbox": bbox,
                    "crs": str(crs),
                    "grid_cell_size_km": self._grid_cell_size_km,
                    "total_cells": len(aois),
                    "valid_aois": bin_summary["valid_aois"],
                    "invalid_aois": bin_summary["invalid_aois"],
                    "excluded_aois": bin_summary["excluded_aois"],
                    "validity_threshold": self._min_validity_threshold,
                    "bin_summary": bin_summary["bin_summary"],
                    "geojson_features": len(binned_aois),
                    "yearly_maps": {},
                }

                # Step 7: Generate visualizations (optional)
                if self._create_visualizations:
                    logger.debug("Step 7: Generating yearly loss maps")

                    try:
                        # Create subfolder named after the GeoJSON file
                        vis_folder = output_file.parent.parent / "loss_maps" / output_file.stem
                        year_maps = create_yearly_maps(
                            geojson_data,
                            vis_folder,
                            bbox=bbox,
                            dpi=self._visualization_dpi,
                        )

                        if year_maps:
                            metadata["yearly_maps"] = year_maps

                            # Generate HTML index
                            html_index = generate_map_summary(year_maps, vis_folder)
                            metadata["map_index"] = str(html_index)

                            logger.info(f"Generated {len(year_maps)} yearly loss maps")

                            self.publish_event(
                                "aoi_sampler.visualizations_created",
                                {
                                    "component": self.name,
                                    "num_maps": len(year_maps),
                                    "maps_folder": str(vis_folder),
                                },
                            )
                    except Exception as e:
                        logger.warning(f"Failed to generate visualizations: {str(e)}")

                # Publish completion event
                self.publish_event(
                    "aoi_sampler.complete",
                    {
                        "component": self.name,
                        "output_path": str(output_file),
                        "total_aois": len(binned_aois),
                        "valid_aois": bin_summary["valid_aois"],
                        "maps_created": len(metadata.get("yearly_maps", {})),
                    },
                )

                logger.info(
                    f"AOI sampling complete: {len(binned_aois)} AOIs "
                    f"({bin_summary['valid_aois']} valid, {bin_summary['invalid_aois']} invalid)"
                )

                return str(output_file), metadata

        except Exception as e:
            logger.error(f"Component execution failed: {str(e)}", exc_info=True)

            # Publish error event
            self.publish_event(
                "aoi_sampler.error",
                {
                    "component": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def _process_cells(
        self, src: Any, cells: list, bbox: Dict[str, float]
    ) -> list:
        """
        Process grid cells and calculate statistics from VRT data.

        Args:
            src: Opened rasterio dataset
            cells: List of grid cell dicts
            bbox: Bounding box of the area

        Returns:
            List of AOI dicts with statistics
        """
        aois = []

        for cell in cells:
            try:
                # Get window from cell bounds
                cell_window = rasterio.windows.from_bounds(
                    cell["minx"],
                    cell["miny"],
                    cell["maxx"],
                    cell["maxy"],
                    src.transform,
                )

                # Read data for this cell (3 bands: treecover, lossyear, datamask)
                try:
                    treecover_data = src.read(1, window=cell_window)
                    lossyear_data = src.read(2, window=cell_window)
                    datamask_data = src.read(3, window=cell_window)
                except Exception as e:
                    logger.warning(f"Failed to read cell {cell['cell_id']}: {str(e)}")
                    continue

                # Calculate statistics
                stats = calculate_cell_statistics(
                    treecover_data,
                    lossyear_data,
                    datamask_data,
                    include_treecover_stats=False,
                    include_loss_by_year=self._include_loss_by_year,
                )

                # Create AOI dict with bounds + statistics
                aoi = {
                    "minx": cell["minx"],
                    "miny": cell["miny"],
                    "maxx": cell["maxx"],
                    "maxy": cell["maxy"],
                    "cell_id": cell["cell_id"],
                    "row": cell["row"],
                    "col": cell["col"],
                }
                aoi.update(stats)

                aois.append(aoi)

            except Exception as e:
                logger.debug(f"Error processing cell {cell['cell_id']}: {str(e)}")
                continue

        logger.info(f"Successfully processed {len(aois)}/{len(cells)} cells")

        return aois

    def cleanup(self) -> None:
        """Clean up component resources."""
        logger.debug("Component cleaned up")
