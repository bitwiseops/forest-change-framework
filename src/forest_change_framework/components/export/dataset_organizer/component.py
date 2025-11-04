"""Dataset Organizer Component - Organize ML training datasets with spatial splits."""

import logging
import csv
import json
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

logger = logging.getLogger(__name__)


@register_component(
    category="export",
    name="dataset_organizer",
    version="1.0.0",
    description="Organize satellite imagery into ML training datasets with spatial train/val/test splits",
    metadata={
        "author": "Forest Change Framework",
        "tags": ["ml-dataset", "train-val-test", "spatial-split", "triplet"],
        "input_type": "imagery_and_patches",
        "output_type": "organized_ml_dataset",
    },
)
class DatasetOrganizerComponent(BaseComponent):
    """
    Organize ML training datasets from imagery and sample patches.

    Takes downloaded Sentinel-2 imagery and sample patches, creates spatial
    train/val/test splits, and organizes into (pre, post, label) triplets
    for machine learning training.

    Uses spatial tile-based splitting to prevent data leakage:
    - Divides geographic space into tiles
    - Assigns all samples in a tile to same split (train/val/test)
    - Ensures spatially adjacent samples don't appear in different splits

    Configuration:
        imagery_directory (str): Path to imagery_downloader output
        sample_patches_directory (str): Path to sample_extractor output
        train_percentage (float): Train split %, default 70.0
        val_percentage (float): Validation split %, default 15.0
        test_percentage (float): Test split %, default 15.0
        spatial_tile_size_deg (float): Tile size in degrees, default 1.0
        image_format (str): Output format (png/geotiff/both), default png
        create_metadata_csv (bool): Generate metadata CSV, default True
    """

    def __init__(
        self,
        event_bus: Any,
        config: Optional[Dict[str, Any]] = None,
        output_base_dir: str = "./data",
    ) -> None:
        """Initialize the dataset organizer component."""
        super().__init__(event_bus, config, output_base_dir)

        # Configuration parameters
        self._imagery_directory: Optional[Path] = None
        self._sample_patches_directory: Optional[Path] = None
        self._train_percentage: float = 70.0
        self._val_percentage: float = 15.0
        self._test_percentage: float = 15.0
        self._spatial_tile_size_deg: float = 1.0
        self._image_format: str = "png"
        self._create_metadata_csv: bool = True

        # Runtime state
        self._output_dir: Optional[Path] = None
        self._samples: List[Dict[str, Any]] = []

        logger.debug("DatasetOrganizerComponent initialized")

    @property
    def name(self) -> str:
        """Get component name."""
        return "dataset_organizer"

    @property
    def version(self) -> str:
        """Get component version."""
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize component with configuration.

        Args:
            config: Configuration dict with keys:
                - imagery_directory: Path to imagery_downloader output (required)
                - sample_patches_directory: Path to sample_extractor output (required)
                - train_percentage: Train % (default 70.0)
                - val_percentage: Val % (default 15.0)
                - test_percentage: Test % (default 15.0)
                - spatial_tile_size_deg: Tile size in degrees (default 1.0)
                - image_format: "png"/"geotiff"/"both" (default "png")
                - create_metadata_csv: Boolean (default True)

        Raises:
            ValueError: If configuration is invalid
        """
        self._config = config
        self._validate_config()

        # Get configuration values
        self._imagery_directory = Path(config.get("imagery_directory"))
        self._sample_patches_directory = Path(config.get("sample_patches_directory"))
        self._train_percentage = float(config.get("train_percentage", 70.0))
        self._val_percentage = float(config.get("val_percentage", 15.0))
        self._test_percentage = float(config.get("test_percentage", 15.0))
        self._spatial_tile_size_deg = float(config.get("spatial_tile_size_deg", 1.0))
        self._image_format = config.get("image_format", "png")
        self._create_metadata_csv = config.get("create_metadata_csv", True)

        # Create output directory
        self._output_dir = self.get_output_dir() / "dataset_organizer"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"DatasetOrganizerComponent initialized: "
            f"train={self._train_percentage}%, "
            f"val={self._val_percentage}%, "
            f"test={self._test_percentage}%"
        )

    def _validate_config(self) -> None:
        """Validate configuration."""
        # Check required paths
        if "imagery_directory" not in self._config:
            raise ValueError("Required config parameter missing: imagery_directory")
        if "sample_patches_directory" not in self._config:
            raise ValueError("Required config parameter missing: sample_patches_directory")

        imagery_path = Path(self._config["imagery_directory"])
        patches_path = Path(self._config["sample_patches_directory"])

        if not imagery_path.exists():
            raise ValueError(f"Imagery directory not found: {imagery_path}")
        if not patches_path.exists():
            raise ValueError(f"Sample patches directory not found: {patches_path}")

        # Validate percentages
        train = float(self._config.get("train_percentage", 70.0))
        val = float(self._config.get("val_percentage", 15.0))
        test = float(self._config.get("test_percentage", 15.0))

        total = train + val + test
        if abs(total - 100.0) > 0.1:  # Allow small floating point error
            raise ValueError(
                f"Train/val/test percentages must sum to 100 "
                f"(got {total})"
            )

        if train < 1 or val < 0 or test < 0:
            raise ValueError("Percentages must be non-negative")

        # Validate tile size
        tile_size = float(self._config.get("spatial_tile_size_deg", 1.0))
        if tile_size <= 0:
            raise ValueError("spatial_tile_size_deg must be positive")

        # Validate image format
        valid_formats = {"png", "geotiff", "both"}
        image_format = self._config.get("image_format", "png")
        if image_format not in valid_formats:
            raise ValueError(f"image_format must be one of {valid_formats}")

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the dataset organizer.

        Returns:
            Dictionary with execution results
        """
        try:
            self.publish_event(f"{self.name}.start", {})

            # Step 1: Discover samples
            self.publish_event(
                f"{self.name}.progress",
                {"message": "Discovering samples..."},
            )

            # TODO: Discover samples from imagery_directory
            self._samples = self._discover_samples()

            self.publish_event(
                f"{self.name}.progress",
                {
                    "message": f"Found {len(self._samples)} samples",
                    "progress": 15,
                },
            )

            # Step 2: Apply spatial split
            self.publish_event(
                f"{self.name}.progress",
                {"message": "Applying spatial tile-based split..."},
            )

            # TODO: Implement spatial splitting
            sample_splits = self._apply_spatial_split()

            self.publish_event(
                f"{self.name}.progress",
                {
                    "message": f"Created triplets...",
                    "progress": 40,
                },
            )

            # Step 3: Create directory structure and triplets
            # TODO: Create train/val/test directories
            # TODO: Copy/organize imagery and patches
            triplet_count = self._create_triplets(sample_splits)

            self.publish_event(
                f"{self.name}.progress",
                {
                    "message": f"Created {triplet_count} triplets",
                    "progress": 70,
                },
            )

            # Step 4: Generate metadata CSV
            if self._create_metadata_csv:
                self.publish_event(
                    f"{self.name}.progress",
                    {"message": "Generating metadata CSV..."},
                )
                # TODO: Generate metadata CSV
                self._generate_metadata_csv(sample_splits)

            # Step 5: Validation
            self.publish_event(
                f"{self.name}.progress",
                {"message": "Validating dataset..."},
            )
            # TODO: Validate output
            validation_report = self._validate_dataset()

            self.publish_event(
                f"{self.name}.progress",
                {
                    "message": "Dataset organization complete",
                    "progress": 100,
                },
            )

            result = {
                "component": self.name,
                "status": "success",
                "samples_organized": triplet_count,
                "output_directory": str(self._output_dir),
                "validation": validation_report,
            }

            self.publish_event(f"{self.name}.complete", result)
            return result

        except Exception as e:
            logger.error(f"Error in dataset organizer: {e}", exc_info=True)
            self.publish_event(
                f"{self.name}.error",
                {"error": str(e), "traceback": "See logs"},
            )
            raise

    def _discover_samples(self) -> List[Dict[str, Any]]:
        """
        Discover samples from imagery_downloader output directory.

        Returns:
            List of sample dicts with {sample_id, bbox, year, ...}
        """
        from . import splitter as splitter_module

        samples = {}
        imagery_dir = Path(self._imagery_directory)

        if not imagery_dir.exists():
            logger.warning(f"Imagery directory not found: {imagery_dir}")
            return {}

        logger.info(f"Discovering samples from {imagery_dir}")

        # Each subdirectory in imagery_downloader output is a sample
        for sample_dir in imagery_dir.iterdir():
            if not sample_dir.is_dir():
                continue

            sample_id = sample_dir.name
            metadata_file = sample_dir / "metadata.json"

            if metadata_file.exists():
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

                    samples[sample_id] = {
                        "sample_id": sample_id,
                        "bbox": metadata.get("bbox"),
                        "year": metadata.get("year"),
                        "imagery_dir": str(sample_dir),
                        "metadata": metadata,
                    }
                except Exception as e:
                    logger.warning(
                        f"Failed to read metadata for {sample_id}: {e}"
                    )
                    continue
            else:
                logger.warning(f"No metadata.json for {sample_id}, skipping")

        logger.info(f"Discovered {len(samples)} samples")
        return samples

    def _apply_spatial_split(self) -> Dict[str, str]:
        """
        Apply spatial tile-based split to samples.

        Returns:
            Dict mapping sample_id to split ("train", "val", "test")
        """
        from .splitter import SpatialTileGrid, SplitValidator

        logger.info("Applying spatial tile-based split")

        # Create tile grid
        tile_grid = SpatialTileGrid(self._spatial_tile_size_deg)

        # Generate splits
        splits = tile_grid.generate_splits(
            self._samples,
            self._train_percentage,
            self._val_percentage,
            self._test_percentage,
        )

        # Validate splits
        validation = SplitValidator.validate_splits(
            splits,
            self._samples,
            self._train_percentage,
            self._val_percentage,
            self._test_percentage,
        )

        if not validation["valid"]:
            logger.warning(f"Split validation warning: {validation.get('warning')}")
        else:
            logger.info("Split validation passed")

        logger.info(
            f"Split distribution: "
            f"train={validation['actual_percentages']['train']}%, "
            f"val={validation['actual_percentages']['val']}%, "
            f"test={validation['actual_percentages']['test']}%"
        )

        return splits

    def _create_triplets(self, splits: Dict[str, str]) -> int:
        """
        Create (pre, post, label) triplets in output directory.

        Args:
            splits: Dict mapping sample_id to split

        Returns:
            Total count of triplets created
        """
        from .organizer import DatasetOrganizer

        logger.info("Creating triplets in output directories")

        organizer = DatasetOrganizer(
            self._output_dir, image_format=self._image_format
        )
        organizer.create_split_directories()

        triplet_count = 0
        patches_dir = Path(self._sample_patches_directory)

        for sample_id, sample_data in self._samples.items():
            split = splits.get(sample_id, "test")  # Default to test if not assigned

            try:
                # Get imagery files
                imagery_dir = Path(sample_data["imagery_dir"])

                # Find pre/post imagery files
                pre_files = {}
                post_files = {}

                if self._image_format in {"png", "both"}:
                    pre_png = imagery_dir / "pre.png"
                    post_png = imagery_dir / "post.png"
                    if pre_png.exists():
                        pre_files["png"] = str(pre_png)
                    if post_png.exists():
                        post_files["png"] = str(post_png)

                if self._image_format in {"geotiff", "both"}:
                    pre_tif = imagery_dir / "pre.tif"
                    post_tif = imagery_dir / "post.tif"
                    if pre_tif.exists():
                        pre_files["geotiff"] = str(pre_tif)
                    if post_tif.exists():
                        post_files["geotiff"] = str(post_tif)

                # Find label file (GeoTIFF from sample_extractor)
                label_path = patches_dir / f"{sample_id}.tif"
                if not label_path.exists():
                    # Try alternative name patterns
                    label_matches = list(
                        patches_dir.glob(f"*{sample_id}*.tif")
                    )
                    if label_matches:
                        label_path = label_matches[0]
                    else:
                        logger.warning(f"Label not found for {sample_id}")
                        label_path = None

                # Create triplet
                if label_path and (pre_files or post_files):
                    organizer.create_sample_triplet(
                        sample_id,
                        split,
                        pre_files,
                        post_files,
                        str(label_path) if label_path else "",
                    )
                    triplet_count += 1
                else:
                    logger.warning(
                        f"Cannot create triplet for {sample_id}: "
                        f"missing imagery or label"
                    )

            except Exception as e:
                logger.error(f"Error creating triplet for {sample_id}: {e}")

        # Store organizer reference for later validation
        self._organizer = organizer

        logger.info(f"Created {triplet_count} triplets")
        return triplet_count

    def _generate_metadata_csv(self, splits: Dict[str, str]) -> None:
        """
        Generate metadata CSV and reports.

        Args:
            splits: Dict mapping sample_id to split
        """
        from .metadata_generator import MetadataGenerator

        logger.info("Generating metadata CSV and reports")

        generator = MetadataGenerator(self._output_dir)

        # Add metadata for each sample
        for sample_id, sample_data in self._samples.items():
            split = splits.get(sample_id, "test")
            year = sample_data.get("year")
            bbox = sample_data.get("bbox")
            metadata = sample_data.get("metadata", {})

            # Find actual file paths in output
            sample_split_dir = self._output_dir / split / sample_id

            pre_path = ""
            post_path = ""
            label_path = ""

            if sample_split_dir.exists():
                for f in sample_split_dir.iterdir():
                    if f.name.startswith("pre"):
                        pre_path = str(f)
                    elif f.name.startswith("post"):
                        post_path = str(f)
                    elif f.name == "label.tif":
                        label_path = str(f)

            generator.add_sample_metadata(
                sample_id=sample_id,
                split=split,
                pre_path=pre_path,
                post_path=post_path,
                label_path=label_path,
                year=year,
                bbox=bbox,
                properties=metadata.get("properties", {}),
            )

        # Generate all metadata files
        generator.generate_metadata_csv()
        generator.generate_split_report(
            split_counts=self._get_split_counts(splits),
            target_percentages={
                "train": self._train_percentage,
                "val": self._val_percentage,
                "test": self._test_percentage,
            },
        )

        stats = generator.generate_statistics()
        logger.info(f"Dataset statistics: {stats}")

        logger.info("Metadata generation complete")

    def _validate_dataset(self) -> Dict[str, Any]:
        """
        Validate the organized dataset.

        Returns:
            Validation report dict
        """
        from .metadata_generator import MetadataGenerator

        logger.info("Validating organized dataset")

        if not hasattr(self, "_organizer"):
            return {
                "status": "error",
                "message": "Organizer not available",
            }

        # Get validation from organizer
        validation = self._organizer.validate_triplets()

        # Get statistics
        generator = MetadataGenerator(self._output_dir)
        stats = generator.generate_statistics()

        # Generate comprehensive report
        try:
            generator.generate_integrity_check(validation)
            generator.generate_summary_report(validation, stats)
        except Exception as e:
            logger.error(f"Error generating reports: {e}")

        report = {
            "status": "valid" if validation.get("valid") else "invalid",
            "total_triplets": validation.get("total_triplets", 0),
            "complete_triplets": validation.get("complete_triplets", 0),
            "split_counts": validation.get("split_counts", {}),
            "statistics": stats,
        }

        if not validation.get("valid"):
            report["incomplete_triplets"] = validation.get("incomplete_triplets", [])

        logger.info(
            f"Validation complete: {report['complete_triplets']}/{report['total_triplets']} "
            f"triplets complete"
        )

        return report

    def _get_split_counts(self, splits: Dict[str, str]) -> Dict[str, int]:
        """
        Count samples per split.

        Args:
            splits: Dict mapping sample_id to split

        Returns:
            Dict with counts per split
        """
        counts = {"train": 0, "val": 0, "test": 0}
        for split in splits.values():
            if split in counts:
                counts[split] += 1
        return counts

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.debug("Dataset organizer cleanup")
