"""Imagery Downloader Component - Download Sentinel-2 imagery from Google Earth Engine."""

import logging
import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

logger = logging.getLogger(__name__)


@register_component(
    category="visualization",
    name="imagery_downloader",
    version="1.0.0",
    description=(
        "Download Sentinel-2 satellite imagery from Google Earth Engine "
        "for forest change samples"
    ),
    metadata={
        "author": "Forest Change Framework",
        "tags": ["sentinel-2", "google-earth-engine", "satellite-imagery", "forest-change"],
        "input_type": "geojson_with_metadata",
        "output_type": "geotiff_png_imagery",
        "requires_authentication": True,
    },
)
class ImageryDownloaderComponent(BaseComponent):
    """
    Download Sentinel-2 pre/post imagery from Google Earth Engine.

    Downloads cloud-free Sentinel-2 imagery matching the spatial extent of
    GeoTIFF samples from the sample_extractor component. For each sample:
    - Downloads pre-event imagery: ±30 days from Jan 1st of loss year
    - Downloads post-event imagery: ±30 days from Jan 1st of year+1
    - Automatically expands date range if no suitable imagery found (up to ±90 days)
    - Saves as GeoTIFF (preserves metadata) and PNG (for ML training)

    Configuration:
        aoi_geojson (str): Path to GeoJSON file from sample_extractor
        cloud_cover_threshold (int): Max cloud cover %, default 30
        initial_date_range (int): Initial ±days around target date, default 30
        max_date_range (int): Maximum ±days to expand search, default 90
        reproject_to_crs (str): Output CRS, default "EPSG:4326"
        bands (list): Sentinel-2 bands to download, default ["B4", "B3", "B2"]
        output_format (list): Output types, default ["geotiff", "png"]
    """

    def __init__(
        self,
        event_bus: Any,
        config: Optional[Dict[str, Any]] = None,
        output_base_dir: str = "./data",
    ) -> None:
        """Initialize the imagery downloader component."""
        super().__init__(event_bus, config, output_base_dir)

        # Configuration parameters
        self._aoi_geojson: Optional[str] = None
        self._cloud_cover_threshold: int = 30
        self._initial_date_range: int = 30
        self._max_date_range: int = 90
        self._reproject_to_crs: str = "EPSG:4326"
        self._bands: list = ["B4", "B3", "B2"]
        self._output_format: list = ["geotiff", "png"]

        # Runtime state
        self._gee_initialized: bool = False
        self._output_dir: Optional[Path] = None

        logger.debug("ImageryDownloaderComponent initialized")

    @property
    def name(self) -> str:
        """Get component name."""
        return "imagery_downloader"

    @property
    def version(self) -> str:
        """Get component version."""
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize component with configuration.

        Args:
            config: Configuration dict with keys:
                - aoi_geojson: Path to GeoJSON (required)
                - cloud_cover_threshold: Max cloud cover % (0-100, default 30)
                - initial_date_range: ±days around target (default 30)
                - max_date_range: Max ±days to expand (default 90)
                - reproject_to_crs: Output CRS (default EPSG:4326)
                - bands: List of Sentinel-2 bands (default ["B4", "B3", "B2"])
                - output_format: List of ["geotiff", "png"] (default both)

        Raises:
            ValueError: If configuration is invalid
        """
        self._config = config
        self._validate_config()

        # Get configuration values
        self._aoi_geojson = config.get("aoi_geojson")
        self._cloud_cover_threshold = config.get("cloud_cover_threshold", 30)
        self._initial_date_range = config.get("initial_date_range", 30)
        self._max_date_range = config.get("max_date_range", 90)
        self._reproject_to_crs = config.get("reproject_to_crs", "EPSG:4326")
        self._bands = config.get("bands", ["B4", "B3", "B2"])
        self._output_format = config.get("output_format", ["geotiff", "png"])

        # Create output directory
        self._output_dir = self.get_output_dir() / "imagery_downloader"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Google Earth Engine
        self._initialize_gee()

        logger.info(f"ImageryDownloaderComponent initialized with {len(self._bands)} bands")

    def _validate_config(self) -> None:
        """Validate configuration."""
        if "aoi_geojson" not in self._config:
            raise ValueError("Required config parameter missing: aoi_geojson")

        aoi_path = Path(self._config["aoi_geojson"])
        if not aoi_path.exists():
            raise ValueError(f"AOI GeoJSON file not found: {aoi_path}")

        # Validate numeric ranges
        threshold = self._config.get("cloud_cover_threshold", 30)
        if not (0 <= threshold <= 100):
            raise ValueError("cloud_cover_threshold must be 0-100")

        initial_range = self._config.get("initial_date_range", 30)
        if initial_range < 1:
            raise ValueError("initial_date_range must be >= 1")

        max_range = self._config.get("max_date_range", 90)
        if max_range < initial_range:
            raise ValueError("max_date_range must be >= initial_date_range")

        # Validate output format
        valid_formats = {"geotiff", "png"}
        output_fmt = self._config.get("output_format", ["geotiff", "png"])
        if not isinstance(output_fmt, list) or not output_fmt:
            raise ValueError("output_format must be non-empty list")
        if not set(output_fmt).issubset(valid_formats):
            raise ValueError(f"output_format values must be in {valid_formats}")

    def _initialize_gee(self) -> None:
        """Initialize Google Earth Engine."""
        if not EE_AVAILABLE:
            raise ImportError(
                "earthengine-api not installed. "
                "Install with: pip install earthengine-api"
            )

        try:
            ee.Initialize()
            self._gee_initialized = True
            logger.info("Google Earth Engine initialized")
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Google Earth Engine: {e}. "
                "Make sure you've authenticated: earthengine authenticate"
            )

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the imagery downloader.

        Returns:
            Dictionary with execution results
        """
        try:
            self.publish_event(f"{self.name}.start", {"source": self._aoi_geojson})

            # Step 1: Read GeoJSON and extract sample metadata
            self.publish_event(
                f"{self.name}.progress",
                {"message": "Reading GeoJSON metadata..."},
            )

            samples = self._read_geojson()
            if not samples:
                raise ValueError(f"No samples found in {self._aoi_geojson}")

            logger.info(f"Found {len(samples)} samples in GeoJSON")

            self.publish_event(
                f"{self.name}.progress",
                {
                    "message": f"Querying Google Earth Engine for {len(samples)} samples...",
                    "progress": 10,
                },
            )

            # Step 2: Query and download imagery for each sample
            download_log = []
            successful_downloads = 0

            for idx, (sample_id, sample_data) in enumerate(samples.items()):
                progress = 10 + int((idx / len(samples)) * 80)

                self.publish_event(
                    f"{self.name}.progress",
                    {
                        "message": f"Processing sample {sample_id} ({idx + 1}/{len(samples)})",
                        "progress": progress,
                    },
                )

                try:
                    result = self._download_sample_imagery(sample_id, sample_data)
                    download_log.append(result)
                    successful_downloads += 1
                except Exception as sample_error:
                    logger.warning(
                        f"Failed to download imagery for sample {sample_id}: {sample_error}"
                    )
                    download_log.append({
                        "sample_id": sample_id,
                        "status": "failed",
                        "error": str(sample_error),
                    })

            # Step 3: Write download log CSV
            self.publish_event(
                f"{self.name}.progress",
                {
                    "message": "Writing download log...",
                    "progress": 95,
                },
            )
            self._write_download_log(download_log)

            self.publish_event(
                f"{self.name}.progress",
                {
                    "message": "Imagery download complete",
                    "progress": 100,
                },
            )

            result = {
                "component": self.name,
                "status": "success",
                "samples_processed": len(samples),
                "successful_downloads": successful_downloads,
                "failed_downloads": len(samples) - successful_downloads,
                "output_directory": str(self._output_dir),
            }

            self.publish_event(f"{self.name}.complete", result)
            return result

        except Exception as e:
            logger.error(f"Error in imagery downloader: {e}", exc_info=True)
            self.publish_event(
                f"{self.name}.error",
                {"error": str(e), "traceback": "See logs"},
            )
            raise

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self._gee_initialized:
            try:
                # GEE doesn't need explicit cleanup, but we log it
                logger.debug("Google Earth Engine session closed")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

    def _read_geojson(self) -> Dict[str, Dict[str, Any]]:
        """
        Read GeoJSON file and extract sample metadata.

        Returns:
            Dictionary mapping sample_id to {bbox, year, ...}

        Raises:
            ValueError: If GeoJSON format is invalid
        """
        try:
            with open(self._aoi_geojson, "r") as f:
                geojson_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid GeoJSON format: {e}")

        samples = {}
        features = geojson_data.get("features", [])

        for feature in features:
            # Extract properties
            props = feature.get("properties", {})
            sample_id = props.get("sample_id")
            year = props.get("year")

            if not sample_id:
                logger.warning("Feature missing sample_id, skipping")
                continue
            if year is None:
                logger.warning(f"Feature {sample_id} missing year, skipping")
                continue

            # Extract bbox from geometry
            geometry = feature.get("geometry", {})
            if geometry.get("type") != "Polygon":
                logger.warning(f"Feature {sample_id} is not a Polygon, skipping")
                continue

            coords = geometry.get("coordinates", [[]])[0]
            if len(coords) < 4:
                logger.warning(f"Feature {sample_id} has invalid coordinates, skipping")
                continue

            # Calculate bbox [minx, miny, maxx, maxy]
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            bbox = [min(xs), min(ys), max(xs), max(ys)]

            samples[sample_id] = {
                "bbox": bbox,
                "year": int(year),
                "properties": props,
            }

        return samples

    def _download_sample_imagery(
        self, sample_id: str, sample_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Download pre/post imagery for a single sample.

        Args:
            sample_id: Sample identifier
            sample_data: Dict with bbox, year, properties

        Returns:
            Download result dict with status, metadata, paths

        Raises:
            Exception: On download or processing errors
        """
        from . import gee_utils, image_processor

        bbox = sample_data["bbox"]
        year = sample_data["year"]

        # Create sample output directory
        sample_dir = self._output_dir / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        # Calculate pre/post dates
        pre_date, post_date = gee_utils.calculate_pre_post_dates(year)

        result = {
            "sample_id": sample_id,
            "status": "success",
            "year": year,
            "bbox": bbox,
            "pre_date": pre_date.isoformat(),
            "post_date": post_date.isoformat(),
            "files": {},
        }

        try:
            # Download pre-event imagery
            logger.debug(f"Downloading pre-event imagery for {sample_id}")
            date_ranges = gee_utils.expand_date_range(
                pre_date, self._initial_date_range, self._max_date_range
            )

            pre_image = self._query_and_download_imagery(
                bbox, date_ranges, "pre", sample_id
            )
            if pre_image is not None:
                pre_files = image_processor.save_imagery(
                    pre_image, sample_dir, "pre", self._output_format,
                    self._reproject_to_crs
                )
                result["files"]["pre"] = pre_files

            # Download post-event imagery
            logger.debug(f"Downloading post-event imagery for {sample_id}")
            date_ranges = gee_utils.expand_date_range(
                post_date, self._initial_date_range, self._max_date_range
            )

            post_image = self._query_and_download_imagery(
                bbox, date_ranges, "post", sample_id
            )
            if post_image is not None:
                post_files = image_processor.save_imagery(
                    post_image, sample_dir, "post", self._output_format,
                    self._reproject_to_crs
                )
                result["files"]["post"] = post_files

            # Save metadata
            metadata = {
                "sample_id": sample_id,
                "year": year,
                "bbox": bbox,
                "pre_date": pre_date.isoformat(),
                "post_date": post_date.isoformat(),
                "cloud_cover_threshold": self._cloud_cover_threshold,
                "bands": self._bands,
                "output_format": self._output_format,
                "crs": self._reproject_to_crs,
            }
            image_processor.save_metadata(
                metadata, sample_dir / "metadata.json"
            )
            result["files"]["metadata"] = str(sample_dir / "metadata.json")

        except Exception as e:
            logger.error(f"Error downloading imagery for {sample_id}: {e}")
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    def _query_and_download_imagery(
        self,
        bbox: list,
        date_ranges: list,
        imagery_type: str,
        sample_id: str,
    ) -> Any:
        """
        Query Google Earth Engine for cloud-free imagery.

        Args:
            bbox: Bounding box [minx, miny, maxx, maxy]
            date_ranges: List of (start_date, end_date) tuples to try
            imagery_type: "pre" or "post" for logging
            sample_id: Sample ID for logging

        Returns:
            ee.Image object or None if not found
        """
        from . import gee_utils

        for start_date, end_date in date_ranges:
            try:
                logger.debug(
                    f"Querying {imagery_type} imagery for {sample_id} "
                    f"between {start_date.date()} and {end_date.date()}"
                )

                image = gee_utils.query_sentinel2_scenes(
                    bbox, start_date, end_date, self._cloud_cover_threshold, self._bands
                )

                if image is not None:
                    logger.info(
                        f"Found {imagery_type} imagery for {sample_id} "
                        f"on {start_date.date()}"
                    )
                    return image

            except Exception as e:
                logger.debug(
                    f"Error querying {imagery_type} imagery "
                    f"({start_date.date()} to {end_date.date()}): {e}"
                )
                continue

        logger.warning(
            f"No suitable {imagery_type} imagery found for {sample_id} "
            f"within {date_ranges[0][0].date()} to {date_ranges[-1][1].date()}"
        )
        return None

    def _write_download_log(self, download_log: list) -> None:
        """
        Write download log to CSV file.

        Args:
            download_log: List of download result dicts
        """
        import csv

        log_path = self._output_dir / "download_log.csv"

        try:
            with open(log_path, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "sample_id",
                        "status",
                        "year",
                        "bbox",
                        "pre_date",
                        "post_date",
                        "error",
                    ],
                )
                writer.writeheader()

                for entry in download_log:
                    row = {
                        "sample_id": entry.get("sample_id"),
                        "status": entry.get("status"),
                        "year": entry.get("year", ""),
                        "bbox": str(entry.get("bbox", "")) if entry.get("bbox") else "",
                        "pre_date": entry.get("pre_date", ""),
                        "post_date": entry.get("post_date", ""),
                        "error": entry.get("error", ""),
                    }
                    writer.writerow(row)

            logger.info(f"Download log written to {log_path}")

        except Exception as e:
            logger.error(f"Failed to write download log: {e}")
