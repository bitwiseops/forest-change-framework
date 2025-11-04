"""Sample Extractor Component - Main orchestrator for extracting TIFF patches from Hansen data."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from forest_change_framework.interfaces import BaseComponent
from forest_change_framework.core import register_component

from .sampling import (
    balance_samples_across_years,
    create_sample_manifest,
    group_aois_by_year_and_bin,
    select_stratified_samples,
)
from .metadata import (
    validate_metadata,
    write_metadata_csv,
    write_metadata_json,
    write_samples_geojson,
    print_validation_report,
)
from .extraction import (
    extract_patch_from_vrt,
    save_geotiff,
)
from .visualization import create_sample_summary_map

logger = logging.getLogger(__name__)


@register_component(category="export", name="sample_extractor", version="1.0.0")
class SampleExtractorComponent(BaseComponent):
    """
    Extract TIFF patches from Hansen forest change data based on stratified AOI samples.

    This component reads GeoJSON output from the AOI Sampler, performs stratified sampling
    to select balanced samples across years and loss categories, and extracts lossyear band
    patches as georeferenced GeoTIFFs with metadata.

    Configuration:
        - aoi_geojson: Path to GeoJSON file from AOI sampler (required)
        - hansen_vrt: Path to Hansen VRT file or tiles directory (required)
        - output_dir: Directory for output patches and metadata (optional, uses data/sample_extractor/ if not provided)
        - samples_per_bin: Number of samples per loss bin (default: 10)
        - metadata_format: "csv", "json", or "both" (default: "both")
        - patch_crs: Output CRS for patches (default: "EPSG:4326")
        - include_metadata_in_tiff: Store metadata in TIFF tags (default: true)
        - validate: Whether to validate metadata after extraction (default: true)
        - band: Hansen band to extract (default: 2 for lossyear)
    """

    @property
    def name(self) -> str:
        """Component name."""
        return "sample_extractor"

    @property
    def version(self) -> str:
        """Component version."""
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize component with configuration.

        Args:
            config: Configuration dict with component parameters

        Raises:
            ValueError: If required config parameters are missing or invalid
        """
        self._config = config
        self._validate_config()

        # Set defaults for optional parameters
        self._samples_per_bin = config.get("samples_per_bin", 10)
        self._metadata_format = config.get("metadata_format", "both").lower()
        self._patch_crs = config.get("patch_crs", "EPSG:4326")
        self._include_metadata_in_tiff = config.get("include_metadata_in_tiff", True)
        self._validate_output = config.get("validate", True)
        self._band = config.get("band", 2)  # Default to lossyear band

        logger.info(f"Initialized {self.name} v{self.version}")

    def _validate_config(self) -> None:
        """Validate component configuration."""
        required = ["aoi_geojson", "hansen_vrt"]
        for key in required:
            if key not in self._config:
                raise ValueError(f"Required config parameter missing: {key}")

        # Validate file paths
        aoi_path = Path(self._config["aoi_geojson"])
        if not aoi_path.exists():
            raise ValueError(f"AOI GeoJSON file not found: {aoi_path}")

        hansen_path = Path(self._config["hansen_vrt"])
        if not hansen_path.exists():
            raise ValueError(f"Hansen VRT/tiles not found: {hansen_path}")

        # Validate metadata format
        valid_formats = {"csv", "json", "both"}
        fmt = self._config.get("metadata_format", "both").lower()
        if fmt not in valid_formats:
            raise ValueError(f"metadata_format must be one of {valid_formats}, got {fmt}")

        # Validate samples_per_bin
        spb = self._config.get("samples_per_bin", 10)
        if not isinstance(spb, int) or spb < 1:
            raise ValueError(f"samples_per_bin must be positive integer, got {spb}")

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute sample extraction workflow.

        Workflow:
        1. Load and parse AOI GeoJSON
        2. Group AOIs by year and loss bin
        3. Perform stratified sampling (N/bins per bin)
        4. Balance samples across years
        5. Create sample manifest with unique IDs
        6. Extract TIFF patches for each sample from Hansen VRT
        7. Generate metadata (CSV/JSON/both)
        8. Validate metadata and patches
        9. Publish progress events

        Returns:
            Dict with execution results including:
            - sample_count: Total samples extracted
            - output_dir: Path to output directory
            - patches_dir: Path to patches subdirectory
            - metadata_files: Paths to generated metadata files
            - validation_report: Metadata validation report (if validate=true)
            - status: "success" or error message
        """
        logger.info(f"Starting {self.name} execution")
        self.publish_event(f"{self.name}.start", {
            "aoi_geojson": self._config["aoi_geojson"],
            "samples_per_bin": self._samples_per_bin,
        })

        try:
            # Use standardized output directory: data/sample_extractor/
            # Allow override via config if provided
            output_dir_from_config = self._config.get("output_dir")
            if output_dir_from_config:
                output_dir = Path(output_dir_from_config)
            else:
                output_dir = self.get_output_dir()

            patches_dir = output_dir / "patches"
            patches_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: Load GeoJSON
            logger.info("Loading AOI GeoJSON...")
            self.publish_event(f"{self.name}.progress", {"step": 1, "message": "Loading GeoJSON"})
            geojson_data = self._load_geojson(self._config["aoi_geojson"])
            total_aois = len(geojson_data.get("features", []))
            logger.info(f"Loaded {total_aois} AOI features")

            # Step 2: Group by year and bin
            logger.info("Grouping AOIs by year and loss bin...")
            self.publish_event(f"{self.name}.progress", {"step": 2, "message": "Grouping AOIs"})
            grouped = group_aois_by_year_and_bin(geojson_data)
            logger.info(f"Grouped into {len(grouped)} years")

            # Step 3: Stratified sampling
            logger.info(f"Selecting stratified samples ({self._samples_per_bin} per bin)...")
            self.publish_event(f"{self.name}.progress", {
                "step": 3,
                "message": f"Stratified sampling ({self._samples_per_bin} per bin)"
            })
            selected = select_stratified_samples(grouped, self._samples_per_bin)
            selected_count = sum(len(f) for y in selected.values() for f in y.values())
            logger.info(f"Selected {selected_count} samples")

            # Step 4: Balance across years
            logger.info("Balancing samples across years...")
            self.publish_event(f"{self.name}.progress", {"step": 4, "message": "Balancing across years"})
            balanced = balance_samples_across_years(selected, self._samples_per_bin)
            balanced_count = sum(len(f) for y in balanced.values() for f in y.values())
            logger.info(f"Balanced to {balanced_count} samples across years")

            # Step 5: Create manifest
            logger.info("Creating sample manifest...")
            self.publish_event(f"{self.name}.progress", {"step": 5, "message": "Creating manifest"})
            manifest = create_sample_manifest(balanced)
            logger.info(f"Created manifest with {len(manifest)} samples")

            # Step 6: Extract TIFF patches
            logger.info("Extracting TIFF patches from Hansen VRT...")
            self.publish_event(f"{self.name}.progress", {
                "step": 6,
                "message": f"Extracting patches (0/{len(manifest)})"
            })
            hansen_path = Path(self._config["hansen_vrt"])
            self._extract_patches(manifest, patches_dir, hansen_path)
            logger.info(f"Extracted {len(manifest)} patches")

            # Step 7: Write metadata
            logger.info(f"Writing metadata ({self._metadata_format})...")
            self.publish_event(f"{self.name}.progress", {"step": 7, "message": "Writing metadata"})
            metadata_files = self._write_metadata(manifest, output_dir)
            logger.info(f"Wrote metadata files: {metadata_files}")

            # Step 8: Generate visualization map
            logger.info("Generating sample location map...")
            self.publish_event(f"{self.name}.progress", {"step": 8, "message": "Generating map visualization"})
            map_path = output_dir / "samples_map.png"
            try:
                create_sample_summary_map(manifest, str(map_path))
                logger.info(f"Generated sample location map: {map_path}")
            except Exception as e:
                logger.warning(f"Failed to generate map visualization: {e}")

            # Step 9: Validate (optional)
            validation_report = None
            if self._validate_output:
                logger.info("Validating metadata and patches...")
                self.publish_event(f"{self.name}.progress", {"step": 9, "message": "Validating metadata"})
                validation_report = validate_metadata(manifest, str(patches_dir))
                logger.info(f"Validation: valid={validation_report['valid']}")
                if not validation_report["valid"]:
                    print_validation_report(validation_report)

            # Return results
            result = {
                "status": "success",
                "sample_count": len(manifest),
                "output_dir": str(output_dir),
                "patches_dir": str(patches_dir),
                "metadata_files": metadata_files,
                "map_path": str(map_path),
                "validation_report": validation_report,
            }

            logger.info(f"Sample extraction complete: {len(manifest)} samples")
            self.publish_event(f"{self.name}.complete", result)
            return result

        except Exception as e:
            error_msg = f"Error in {self.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.publish_event(f"{self.name}.error", {"error": str(e)})
            raise

    def _load_geojson(self, geojson_path: str) -> Dict[str, Any]:
        """
        Load GeoJSON file.

        Args:
            geojson_path: Path to GeoJSON file

        Returns:
            Parsed GeoJSON dict

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON parsing fails
        """
        path = Path(geojson_path)
        if not path.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {geojson_path}")

        try:
            with open(path) as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("GeoJSON must be a dict")

            if "features" not in data:
                data["features"] = []

            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse GeoJSON: {e}")

    def _extract_patches(
        self,
        manifest: List[Dict[str, Any]],
        patches_dir: Path,
        hansen_path: Path,
    ) -> None:
        """
        Extract TIFF patches for all samples from Hansen VRT.

        Args:
            manifest: List of sample dicts from create_sample_manifest()
            patches_dir: Directory to save patch TIFFs
            hansen_path: Path to Hansen VRT file

        Raises:
            Exception: If extraction fails for any sample
        """
        skipped_samples = []

        for idx, sample in enumerate(manifest):
            sample_id = sample["sample_id"]
            bbox = {
                "minx": sample["minx"],
                "miny": sample["miny"],
                "maxx": sample["maxx"],
                "maxy": sample["maxy"],
            }

            try:
                # Extract patch from VRT
                patch_data = extract_patch_from_vrt(str(hansen_path), bbox, band=self._band)

                # Skip empty patches (outside VRT extent)
                if patch_data.shape[0] == 0 or patch_data.shape[1] == 0:
                    logger.warning(f"Skipping sample {sample_id}: empty patch (outside VRT extent)")
                    skipped_samples.append(sample_id)
                    continue

                # Prepare metadata for TIFF tags (include all input properties)
                tiff_metadata = None
                if self._include_metadata_in_tiff:
                    tiff_metadata = {
                        "sample_id": sample_id,
                        "aoi_id": sample["aoi_id"],
                        "year": sample["year"],
                        "loss_bin": sample["loss_bin"],
                        "loss_percentage": sample["loss_percentage"],
                    }
                    # Add all input properties (TIFF tags have size limits, so we compress)
                    if "input_properties" in sample:
                        input_props = sample["input_properties"]
                        for key, value in input_props.items():
                            # Convert to string and limit to reasonable length
                            if value is not None:
                                str_val = str(value)
                                if len(str_val) < 254:  # TIFF tag character limit
                                    tiff_metadata[f"prop_{key}"] = str_val

                # Save as GeoTIFF
                output_path = patches_dir / f"{sample_id}.tif"
                save_geotiff(
                    str(output_path),
                    patch_data,
                    bbox,
                    crs=self._patch_crs,
                    metadata=tiff_metadata,
                )

                # Publish progress
                if (idx + 1) % max(1, len(manifest) // 10) == 0:
                    self.publish_event(f"{self.name}.progress", {
                        "step": 6,
                        "message": f"Extracting patches ({idx + 1}/{len(manifest)})"
                    })

            except Exception as e:
                logger.error(f"Failed to extract patch {sample_id}: {e}")
                raise ValueError(f"Extraction failed for sample {sample_id}: {e}")

        if skipped_samples:
            logger.warning(f"Skipped {len(skipped_samples)} samples outside VRT extent: {skipped_samples}")

    def _write_metadata(
        self,
        manifest: List[Dict[str, Any]],
        output_dir: Path,
    ) -> List[str]:
        """
        Write metadata files in configured format(s).

        Args:
            manifest: List of sample dicts
            output_dir: Directory for metadata files

        Returns:
            List of written metadata file paths

        Raises:
            Exception: If writing fails
        """
        metadata_files = []

        if self._metadata_format in ("csv", "both"):
            csv_path = output_dir / "samples_metadata.csv"
            write_metadata_csv(manifest, str(csv_path))
            metadata_files.append(str(csv_path))
            logger.info(f"Wrote CSV metadata: {csv_path}")

        if self._metadata_format in ("json", "both"):
            json_path = output_dir / "samples_metadata.json"
            write_metadata_json(manifest, str(json_path), patches_dir="patches")
            metadata_files.append(str(json_path))
            logger.info(f"Wrote JSON metadata: {json_path}")

        # Always write GeoJSON with complete metadata for downstream components
        geojson_path = output_dir / "samples.geojson"
        write_samples_geojson(manifest, str(geojson_path))
        metadata_files.append(str(geojson_path))
        logger.info(f"Wrote GeoJSON with complete metadata: {geojson_path}")

        return metadata_files

    def cleanup(self) -> None:
        """Cleanup component resources."""
        logger.info(f"Cleaned up {self.name}")
