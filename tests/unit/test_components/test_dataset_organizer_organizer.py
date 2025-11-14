"""Unit tests for dataset organizer module."""

import tempfile
from pathlib import Path
from typing import Dict
import json

import pytest

from forest_change_framework.components.export.dataset_organizer.organizer import (
    DatasetOrganizer,
)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def dummy_image_file(tmp_path):
    """Create a dummy image file for testing."""
    image_path = tmp_path / "dummy.png"
    image_path.write_bytes(b"PNG_DATA")
    return str(image_path)


@pytest.fixture
def dummy_label_file(tmp_path):
    """Create a dummy label file for testing."""
    label_path = tmp_path / "label.tif"
    label_path.write_bytes(b"TIFF_DATA")
    return str(label_path)


class TestDatasetOrganizer:
    """Tests for DatasetOrganizer class."""

    def test_initialization_valid(self, temp_output_dir):
        """Test DatasetOrganizer initialization with valid parameters."""
        organizer = DatasetOrganizer(temp_output_dir, image_format="png")

        assert organizer.output_dir == temp_output_dir
        assert organizer.image_format == "png"
        assert len(organizer.split_dirs) == 0

    def test_initialization_invalid_format(self, temp_output_dir):
        """Test initialization with invalid image format."""
        with pytest.raises(ValueError, match="Invalid image_format"):
            DatasetOrganizer(temp_output_dir, image_format="invalid")

    def test_create_split_directories(self, temp_output_dir):
        """Test split directory creation."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        assert (temp_output_dir / "train").exists()
        assert (temp_output_dir / "val").exists()
        assert (temp_output_dir / "test").exists()

        assert len(organizer.split_dirs) == 3
        assert organizer.split_dirs["train"] == temp_output_dir / "train"
        assert organizer.split_dirs["val"] == temp_output_dir / "val"
        assert organizer.split_dirs["test"] == temp_output_dir / "test"

    def test_create_sample_triplet_png(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test creating a sample triplet with PNG format."""
        organizer = DatasetOrganizer(temp_output_dir, image_format="png")
        organizer.create_split_directories()

        pre_files = {"png": dummy_image_file}
        post_files = {"png": dummy_image_file}

        result = organizer.create_sample_triplet(
            "sample_001",
            "train",
            pre_files,
            post_files,
            dummy_label_file,
        )

        assert "pre" in result
        assert "post" in result
        assert "label" in result

        sample_dir = temp_output_dir / "train" / "sample_001"
        assert sample_dir.exists()
        assert (sample_dir / "pre.png").exists()
        assert (sample_dir / "post.png").exists()
        assert (sample_dir / "label.tif").exists()

    def test_create_sample_triplet_geotiff(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test creating a sample triplet with GeoTIFF format."""
        organizer = DatasetOrganizer(temp_output_dir, image_format="geotiff")
        organizer.create_split_directories()

        pre_files = {"geotiff": dummy_image_file}
        post_files = {"geotiff": dummy_image_file}

        result = organizer.create_sample_triplet(
            "sample_001",
            "val",
            pre_files,
            post_files,
            dummy_label_file,
        )

        sample_dir = temp_output_dir / "val" / "sample_001"
        assert sample_dir.exists()
        assert (sample_dir / "pre.tif").exists()
        assert (sample_dir / "post.tif").exists()

    def test_create_sample_triplet_both_formats(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test creating a sample triplet with both PNG and GeoTIFF."""
        organizer = DatasetOrganizer(temp_output_dir, image_format="both")
        organizer.create_split_directories()

        pre_files = {"png": dummy_image_file}
        post_files = {"png": dummy_image_file}

        result = organizer.create_sample_triplet(
            "sample_001",
            "test",
            pre_files,
            post_files,
            dummy_label_file,
        )

        sample_dir = temp_output_dir / "test" / "sample_001"
        assert sample_dir.exists()

    def test_create_sample_triplet_invalid_split(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test creating a triplet with invalid split."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        with pytest.raises(ValueError, match="Invalid split"):
            organizer.create_sample_triplet(
                "sample_001",
                "invalid_split",
                {"png": dummy_image_file},
                {"png": dummy_image_file},
                dummy_label_file,
            )

    def test_create_sample_triplet_missing_imagery(self, temp_output_dir, dummy_label_file):
        """Test creating a triplet with missing imagery files."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        result = organizer.create_sample_triplet(
            "sample_001",
            "train",
            {},  # No imagery files
            {},  # No imagery files
            dummy_label_file,
        )

        # Should still create directory with label
        sample_dir = temp_output_dir / "train" / "sample_001"
        assert sample_dir.exists()

    def test_create_sample_triplet_missing_label(self, temp_output_dir, dummy_image_file):
        """Test creating a triplet with missing label."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        result = organizer.create_sample_triplet(
            "sample_001",
            "train",
            {"png": dummy_image_file},
            {"png": dummy_image_file},
            "",  # No label
        )

        sample_dir = temp_output_dir / "train" / "sample_001"
        assert sample_dir.exists()
        assert (sample_dir / "pre.png").exists()
        assert (sample_dir / "post.png").exists()

    def test_get_triplet_structure(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test get_triplet_structure method."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        # Create a few triplets
        for i in range(3):
            organizer.create_sample_triplet(
                f"sample_{i:03d}",
                "train" if i < 2 else "test",
                {"png": dummy_image_file},
                {"png": dummy_image_file},
                dummy_label_file,
            )

        structure = organizer.get_triplet_structure()

        assert "train" in structure
        assert "val" in structure
        assert "test" in structure
        assert len(structure["train"]) == 2
        assert len(structure["test"]) == 1

    def test_validate_triplets_complete(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test validate_triplets with complete triplets."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        # Create complete triplets
        for i in range(2):
            organizer.create_sample_triplet(
                f"sample_{i:03d}",
                "train",
                {"png": dummy_image_file},
                {"png": dummy_image_file},
                dummy_label_file,
            )

        report = organizer.validate_triplets()

        assert report["valid"] is True
        assert report["total_triplets"] == 2
        assert report["complete_triplets"] == 2
        assert report["split_counts"]["train"] == 2

    def test_validate_triplets_incomplete(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test validate_triplets with incomplete triplets."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        # Create incomplete triplet (missing label)
        sample_dir = temp_output_dir / "train" / "sample_001"
        sample_dir.mkdir(parents=True)
        import shutil
        shutil.copy(dummy_image_file, sample_dir / "pre.png")

        report = organizer.validate_triplets()

        assert report["valid"] is False
        assert report["total_triplets"] == 1
        assert report["complete_triplets"] == 0
        assert len(report["incomplete_triplets"]) == 1

    def test_validate_triplets_empty(self, temp_output_dir):
        """Test validate_triplets with empty output directory."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        report = organizer.validate_triplets()

        assert report["total_triplets"] == 0
        assert report["complete_triplets"] == 0
        assert report["valid"] is True

    def test_multiple_splits(self, temp_output_dir, dummy_image_file, dummy_label_file):
        """Test creating triplets in multiple splits."""
        organizer = DatasetOrganizer(temp_output_dir)
        organizer.create_split_directories()

        splits = ["train", "val", "test"]

        for split_name in splits:
            organizer.create_sample_triplet(
                f"sample_{split_name}",
                split_name,
                {"png": dummy_image_file},
                {"png": dummy_image_file},
                dummy_label_file,
            )

        report = organizer.validate_triplets()

        assert report["total_triplets"] == 3
        assert report["complete_triplets"] == 3
        assert report["split_counts"]["train"] == 1
        assert report["split_counts"]["val"] == 1
        assert report["split_counts"]["test"] == 1
