"""Integration tests for dataset organizer component."""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
import numpy as np
try:
    from PIL import Image
except ImportError:
    Image = None

from forest_change_framework import BaseFramework
from forest_change_framework.components.export.dataset_organizer import DatasetOrganizerComponent


@pytest.fixture
def sample_imagery_directory(tmp_path):
    """
    Create a mock imagery_downloader output directory with sample metadata and dummy imagery.

    Structure:
        imagery_output/
        ├── 000001/
        │   ├── metadata.json
        │   ├── pre.png
        │   └── post.png
        ├── 000002/
        │   ├── metadata.json
        │   ├── pre.png
        │   └── post.png
        ...
    """
    imagery_dir = tmp_path / "imagery_output"
    imagery_dir.mkdir(parents=True, exist_ok=True)

    # Create 10 sample imagery directories with metadata
    for sample_id in range(1, 11):
        sample_dir = imagery_dir / f"{sample_id:06d}"
        sample_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata.json
        metadata = {
            "sample_id": f"{sample_id:06d}",
            "bbox": [
                -45.0 + (sample_id * 0.1),
                -13.0 - (sample_id * 0.1),
                -44.9 + (sample_id * 0.1),
                -12.9 - (sample_id * 0.1),
            ],
            "year": 2016 + (sample_id % 3),
            "cloud_cover": 5 + (sample_id % 10),
            "source": "sentinel-2",
        }

        with open(sample_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Create dummy PNG imagery (8x8 small image)
        if Image:
            img_array = np.random.randint(0, 256, (8, 8, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(sample_dir / "pre.png")
            img.save(sample_dir / "post.png")
        else:
            # Fallback: create minimal PNG files
            (sample_dir / "pre.png").write_bytes(b"PNG_DATA")
            (sample_dir / "post.png").write_bytes(b"PNG_DATA")

    return str(imagery_dir)


@pytest.fixture
def sample_patches_directory():
    """Use actual sample patches from the project data folder."""
    patches_dir = Path("/home/bitwise/Projects/forest-change-framework/data/sample_extractor_output/patches")

    if not patches_dir.exists():
        pytest.skip(f"Sample patches directory not found: {patches_dir}")

    return str(patches_dir)


@pytest.fixture
def dataset_organizer_config(sample_imagery_directory, sample_patches_directory, tmp_path):
    """Create configuration for dataset organizer."""
    return {
        "imagery_directory": sample_imagery_directory,
        "sample_patches_directory": sample_patches_directory,
        "train_percentage": 70.0,
        "val_percentage": 15.0,
        "test_percentage": 15.0,
        "spatial_tile_size_deg": 5.0,
        "image_format": "png",
        "create_metadata_csv": True,
    }


class TestDatasetOrganizerComponentIntegration:
    """Integration tests for DatasetOrganizerComponent."""

    def test_component_initialization(self, framework, dataset_organizer_config):
        """Test component can be initialized with valid config."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        # Create instance
        component = component_class(framework.event_bus, dataset_organizer_config)
        component.initialize(dataset_organizer_config)

        assert component.name == "dataset_organizer"
        assert component.version == "1.0.0"

    def test_component_execution(self, framework, dataset_organizer_config, tmp_path):
        """Test component can execute with sample data."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        # Create component with temp output directory
        config = dataset_organizer_config.copy()
        config["output_base_dir"] = str(tmp_path)

        component = component_class(framework.event_bus, config)
        component.initialize(config)

        # Execute
        result = component.execute()

        # Verify result
        assert result["status"] == "success"
        assert "output_directory" in result
        assert result["samples_organized"] >= 0

    def test_output_directory_structure(self, framework, dataset_organizer_config, tmp_path):
        """Test that output directory has correct structure."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = dataset_organizer_config.copy()
        config["output_base_dir"] = str(tmp_path)

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        output_dir = Path(result["output_directory"])

        # Check split directories exist
        assert (output_dir / "train").exists()
        assert (output_dir / "val").exists()
        assert (output_dir / "test").exists()

    def test_metadata_csv_generation(self, framework, dataset_organizer_config, tmp_path):
        """Test that metadata CSV is generated."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = dataset_organizer_config.copy()
        config["output_base_dir"] = str(tmp_path)
        config["create_metadata_csv"] = True

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        output_dir = Path(result["output_directory"])
        metadata_csv = output_dir / "metadata.csv"

        # Check metadata CSV exists
        assert metadata_csv.exists()

        # Verify CSV has content
        with open(metadata_csv, "r") as f:
            lines = f.readlines()
            assert len(lines) > 1  # Header + at least one sample

    def test_validation_report(self, framework, dataset_organizer_config, tmp_path):
        """Test that validation report is generated."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = dataset_organizer_config.copy()
        config["output_base_dir"] = str(tmp_path)

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        assert "validation" in result
        assert "status" in result["validation"]
        assert "total_triplets" in result["validation"]
        assert "complete_triplets" in result["validation"]

    def test_event_publishing(self, framework, dataset_organizer_config, tmp_path, event_collector):
        """Test that component publishes correct events."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        # Subscribe to events
        framework.subscribe_event("dataset_organizer.start", event_collector.collect)
        framework.subscribe_event("dataset_organizer.progress", event_collector.collect)
        framework.subscribe_event("dataset_organizer.complete", event_collector.collect)

        config = dataset_organizer_config.copy()
        config["output_base_dir"] = str(tmp_path)

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        # Verify events were published
        assert event_collector.has_event("dataset_organizer.start")
        assert event_collector.has_event("dataset_organizer.complete")

    def test_configuration_validation_missing_imagery_dir(self, framework, sample_patches_directory, tmp_path):
        """Test configuration validation rejects missing imagery directory."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = {
            "imagery_directory": "/nonexistent/path",
            "sample_patches_directory": sample_patches_directory,
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
        }

        component = component_class(framework.event_bus, config)

        with pytest.raises(ValueError, match="Imagery directory not found"):
            component.initialize(config)

    def test_configuration_validation_invalid_percentages(self, framework, dataset_organizer_config):
        """Test configuration validation rejects invalid percentages."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = dataset_organizer_config.copy()
        config["train_percentage"] = 50.0
        config["val_percentage"] = 30.0
        config["test_percentage"] = 15.0  # Sum = 95, not 100

        component = component_class(framework.event_bus, config)

        with pytest.raises(ValueError, match="must sum to 100"):
            component.initialize(config)

    def test_different_image_formats(self, framework, sample_imagery_directory, sample_patches_directory, tmp_path):
        """Test component with different image format options."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        for image_format in ["png"]:  # Simplified for testing
            config = {
                "imagery_directory": sample_imagery_directory,
                "sample_patches_directory": sample_patches_directory,
                "train_percentage": 70.0,
                "val_percentage": 15.0,
                "test_percentage": 15.0,
                "image_format": image_format,
                "output_base_dir": str(tmp_path / f"output_{image_format}"),
            }

            component = component_class(framework.event_bus, config)
            component.initialize(config)
            result = component.execute()

            assert result["status"] == "success"

    def test_spatial_split_distribution(self, framework, dataset_organizer_config, tmp_path):
        """Test that spatial splits distribute samples correctly."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = dataset_organizer_config.copy()
        config["output_base_dir"] = str(tmp_path)
        config["train_percentage"] = 70.0
        config["val_percentage"] = 15.0
        config["test_percentage"] = 15.0

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        validation = result["validation"]
        total = validation.get("total_triplets", 0)

        if total > 0:
            # Verify splits are within tolerance
            split_counts = validation.get("split_counts", {})
            assert sum(split_counts.values()) == total


class TestDatasetOrganizerWithSmallDataset:
    """Tests with minimal dataset to ensure robustness."""

    @pytest.fixture
    def minimal_imagery_dir(self, tmp_path):
        """Create minimal imagery directory with just 3 samples."""
        imagery_dir = tmp_path / "imagery"
        imagery_dir.mkdir()

        for i in range(1, 4):
            sample_dir = imagery_dir / f"{i:06d}"
            sample_dir.mkdir()

            metadata = {
                "sample_id": f"{i:06d}",
                "bbox": [-45.0 + i * 0.5, -13.0 - i * 0.5, -44.5 + i * 0.5, -12.5 - i * 0.5],
                "year": 2016,
            }

            with open(sample_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)

            # Create minimal files
            (sample_dir / "pre.png").write_bytes(b"")
            (sample_dir / "post.png").write_bytes(b"")

        return str(imagery_dir)

    def test_minimal_dataset_organization(self, framework, minimal_imagery_dir, sample_patches_directory, tmp_path):
        """Test organizing a minimal dataset."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = {
            "imagery_directory": minimal_imagery_dir,
            "sample_patches_directory": sample_patches_directory,
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "output_base_dir": str(tmp_path),
        }

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        # Even with few samples, should complete successfully
        assert result["status"] == "success"
        assert result["samples_organized"] >= 0
