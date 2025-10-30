"""Dataset organizer for creating directory structure and triplets."""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DatasetOrganizer:
    """Organize imagery into train/val/test directories with (pre, post, label) triplets."""

    def __init__(self, output_dir: Path, image_format: str = "png"):
        """
        Initialize dataset organizer.

        Args:
            output_dir: Base output directory
            image_format: "png", "geotiff", or "both"
        """
        if image_format not in {"png", "geotiff", "both"}:
            raise ValueError(f"Invalid image_format: {image_format}")

        self.output_dir = Path(output_dir)
        self.image_format = image_format
        self.split_dirs = {}

    def create_split_directories(self) -> None:
        """Create train/val/test subdirectories."""
        for split in ["train", "val", "test"]:
            split_dir = self.output_dir / split
            split_dir.mkdir(parents=True, exist_ok=True)
            self.split_dirs[split] = split_dir
            logger.debug(f"Created {split} directory: {split_dir}")

    def create_sample_triplet(
        self,
        sample_id: str,
        split: str,
        pre_files: Dict[str, str],
        post_files: Dict[str, str],
        label_path: str,
    ) -> Dict[str, str]:
        """
        Create triplet directory structure for a sample.

        Creates: {split}/{sample_id}/pre.*, post.*, label.tif

        Args:
            sample_id: Sample identifier
            split: "train", "val", or "test"
            pre_files: Dict of pre-imagery files {format: path}
            post_files: Dict of post-imagery files {format: path}
            label_path: Path to label GeoTIFF

        Returns:
            Dict with paths to created files

        Raises:
            ValueError: If split is invalid or files not found
        """
        if split not in self.split_dirs:
            raise ValueError(f"Invalid split: {split}")

        # Create sample directory
        sample_dir = self.split_dirs[split] / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        output_files = {}

        try:
            # Copy pre-imagery
            pre_path = self._copy_imagery_file(
                pre_files, sample_dir, "pre"
            )
            if pre_path:
                output_files["pre"] = str(pre_path)

            # Copy post-imagery
            post_path = self._copy_imagery_file(
                post_files, sample_dir, "post"
            )
            if post_path:
                output_files["post"] = str(post_path)

            # Copy label
            if label_path and Path(label_path).exists():
                label_dest = sample_dir / "label.tif"
                shutil.copy2(label_path, label_dest)
                output_files["label"] = str(label_dest)
                logger.debug(f"Copied label to {label_dest}")
            else:
                logger.warning(f"Label file not found: {label_path}")

        except Exception as e:
            logger.error(f"Error creating triplet for {sample_id}: {e}")
            raise

        return output_files

    def _copy_imagery_file(
        self,
        files_dict: Dict[str, str],
        dest_dir: Path,
        prefix: str,
    ) -> Optional[Path]:
        """
        Copy imagery file (PNG or GeoTIFF based on format preference).

        Args:
            files_dict: Dict of format to file path
            dest_dir: Destination directory
            prefix: "pre" or "post"

        Returns:
            Path to copied file or None

        Raises:
            ValueError: If no suitable file format found
        """
        source_path = None
        dest_ext = None

        if self.image_format == "png" and "png" in files_dict:
            source_path = Path(files_dict["png"])
            dest_ext = ".png"
        elif self.image_format == "geotiff" and "geotiff" in files_dict:
            source_path = Path(files_dict["geotiff"])
            dest_ext = ".tif"
        elif self.image_format == "both":
            # Use PNG as primary, but keep both if available
            if "png" in files_dict:
                source_path = Path(files_dict["png"])
                dest_ext = ".png"
            elif "geotiff" in files_dict:
                source_path = Path(files_dict["geotiff"])
                dest_ext = ".tif"

        if not source_path or not source_path.exists():
            logger.warning(
                f"Imagery file not found for {prefix}. "
                f"Available formats: {list(files_dict.keys())}"
            )
            return None

        dest_path = dest_dir / f"{prefix}{dest_ext}"

        try:
            shutil.copy2(source_path, dest_path)
            logger.debug(f"Copied {prefix} imagery to {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to copy {prefix} imagery: {e}")
            raise

    def get_triplet_structure(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get structure of created triplets.

        Returns:
            Dict mapping split to list of triplet dicts
        """
        structure = {}

        for split, split_dir in self.split_dirs.items():
            structure[split] = []

            if split_dir.exists():
                for sample_dir in sorted(split_dir.iterdir()):
                    if sample_dir.is_dir():
                        files = {
                            f.name: str(f)
                            for f in sample_dir.iterdir()
                        }

                        triplet = {
                            "sample_id": sample_dir.name,
                            "files": files,
                            "complete": all(
                                k in files for k in ["pre", "post", "label"]
                            ),
                        }
                        structure[split].append(triplet)

        return structure

    def validate_triplets(self) -> Dict[str, Any]:
        """
        Validate all created triplets.

        Returns:
            Validation report dict
        """
        report = {
            "valid": True,
            "total_triplets": 0,
            "complete_triplets": 0,
            "incomplete_triplets": [],
            "split_counts": {"train": 0, "val": 0, "test": 0},
        }

        for split, split_dir in self.split_dirs.items():
            if not split_dir.exists():
                continue

            for sample_dir in split_dir.iterdir():
                if not sample_dir.is_dir():
                    continue

                report["total_triplets"] += 1
                report["split_counts"][split] += 1

                files = list(sample_dir.iterdir())
                file_names = {f.name for f in files}

                # Check for required files
                required_files = {"label.tif"}
                # At least one of pre or post should exist
                imagery_exists = any(
                    fn.startswith("pre") or fn.startswith("post")
                    for fn in file_names
                )

                if required_files.issubset(file_names) and imagery_exists:
                    report["complete_triplets"] += 1
                else:
                    report["valid"] = False
                    report["incomplete_triplets"].append({
                        "sample_id": sample_dir.name,
                        "split": split,
                        "missing_files": list(
                            required_files - file_names
                        ),
                    })

        return report
