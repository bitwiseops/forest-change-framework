"""Real-world integration test using actual sample extractor output."""

import json
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

# Import components to trigger registration
from forest_change_framework.components.export.dataset_organizer import (
    DatasetOrganizerComponent,
)


# Path to real sample extractor output
SAMPLE_EXTRACTOR_OUTPUT = Path(
    "/home/bitwise/Projects/forest-change-framework/data/sample_extractor_output"
)


@pytest.fixture
def real_sample_metadata() -> Dict[str, Any]:
    """Load real sample metadata from sample extractor output."""
    metadata_file = SAMPLE_EXTRACTOR_OUTPUT / "samples_metadata.json"

    if not metadata_file.exists():
        pytest.skip(f"Sample extractor output not found: {SAMPLE_EXTRACTOR_OUTPUT}")

    with open(metadata_file, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_imagery_from_real_samples(tmp_path, real_sample_metadata) -> str:
    """
    Create mock imagery directory that matches real sample metadata.

    For each sample in the real metadata, create:
    - metadata.json with actual bbox and year
    - pre.png and post.png (dummy files)
    """
    imagery_dir = tmp_path / "imagery_from_sampler"
    imagery_dir.mkdir(parents=True, exist_ok=True)

    samples_data = real_sample_metadata.get("samples", [])

    for sample in samples_data[:20]:  # Use first 20 samples for testing
        sample_id = sample.get("sample_id")
        if not sample_id:
            continue

        sample_dir = imagery_dir / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata.json with actual bbox and year
        metadata = {
            "sample_id": sample_id,
            "bbox": [
                sample["bbox"]["minx"],
                sample["bbox"]["miny"],
                sample["bbox"]["maxx"],
                sample["bbox"]["maxy"],
            ],
            "year": sample.get("year", 2016),
            "loss_percentage": sample.get("loss_percentage", 0),
            "source": "sentinel-2",
        }

        with open(sample_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Create dummy PNG imagery files
        if Image:
            img_array = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(sample_dir / "pre.png")
            img.save(sample_dir / "post.png")
        else:
            # Fallback: create minimal PNG files
            (sample_dir / "pre.png").write_bytes(b"PNG_DATA")
            (sample_dir / "post.png").write_bytes(b"PNG_DATA")

    return str(imagery_dir)


class TestDatasetOrganizerWithRealSamples:
    """Integration tests using real sample extractor output."""

    def test_organize_real_samples_end_to_end(
        self,
        framework,
        mock_imagery_from_real_samples,
        tmp_path,
    ):
        """
        End-to-end test: organize real sampler output into ML dataset.

        This test demonstrates the full workflow:
        1. Take output from sample_extractor (patches + metadata)
        2. Create mock imagery to match sample locations
        3. Run dataset organizer to create train/val/test splits
        4. Verify output structure and validation
        """
        from forest_change_framework.core import get_registry

        # Get the dataset organizer component
        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        # Configure with real paths
        config = {
            "imagery_directory": mock_imagery_from_real_samples,
            "sample_patches_directory": str(
                SAMPLE_EXTRACTOR_OUTPUT / "patches"
            ),
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "spatial_tile_size_deg": 5.0,
            "image_format": "png",
            "create_metadata_csv": True,
            "output_base_dir": str(tmp_path),
        }

        # Create and initialize component
        component = component_class(framework.event_bus, config)
        component.initialize(config)

        # Execute
        result = component.execute()

        # Verify success
        assert result["status"] == "success"
        assert result["samples_organized"] > 0

        # Verify output directory structure
        output_dir = Path(result["output_directory"])
        assert output_dir.exists()
        assert (output_dir / "train").exists()
        assert (output_dir / "val").exists()
        assert (output_dir / "test").exists()

        # Verify metadata CSV was created
        assert (output_dir / "metadata.csv").exists()

        print(f"\n✓ Successfully organized {result['samples_organized']} samples")
        print(f"✓ Output directory: {output_dir}")

    def test_real_samples_split_distribution(
        self,
        framework,
        mock_imagery_from_real_samples,
        tmp_path,
    ):
        """Test that real samples are properly distributed across splits."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = {
            "imagery_directory": mock_imagery_from_real_samples,
            "sample_patches_directory": str(
                SAMPLE_EXTRACTOR_OUTPUT / "patches"
            ),
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "spatial_tile_size_deg": 5.0,
            "output_base_dir": str(tmp_path),
        }

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        # Check split distribution
        validation = result["validation"]
        split_counts = validation.get("split_counts", {})

        print(f"\n✓ Split distribution:")
        print(f"  Train: {split_counts.get('train', 0)}")
        print(f"  Val:   {split_counts.get('val', 0)}")
        print(f"  Test:  {split_counts.get('test', 0)}")
        print(f"  Total: {validation.get('total_triplets', 0)}")

        total = sum(split_counts.values())
        if total > 0:
            # Calculate actual percentages
            train_pct = (split_counts.get("train", 0) / total) * 100
            val_pct = (split_counts.get("val", 0) / total) * 100
            test_pct = (split_counts.get("test", 0) / total) * 100

            print(f"\n✓ Actual percentages:")
            print(f"  Train: {train_pct:.1f}%")
            print(f"  Val:   {val_pct:.1f}%")
            print(f"  Test:  {test_pct:.1f}%")

    def test_real_samples_metadata_csv(
        self,
        framework,
        mock_imagery_from_real_samples,
        tmp_path,
    ):
        """Test that metadata CSV contains correct sample information."""
        from forest_change_framework.core import get_registry
        import csv

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = {
            "imagery_directory": mock_imagery_from_real_samples,
            "sample_patches_directory": str(
                SAMPLE_EXTRACTOR_OUTPUT / "patches"
            ),
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "create_metadata_csv": True,
            "output_base_dir": str(tmp_path),
        }

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        # Read metadata CSV
        output_dir = Path(result["output_directory"])
        metadata_csv = output_dir / "metadata.csv"

        assert metadata_csv.exists()

        # Verify CSV contents
        with open(metadata_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"\n✓ Metadata CSV contains {len(rows)} samples")

        # Verify required columns
        if rows:
            first_row = rows[0]
            expected_columns = {"sample_id", "split", "pre_path", "post_path"}
            actual_columns = set(first_row.keys())
            assert expected_columns.issubset(actual_columns)

            print(f"✓ CSV columns: {list(first_row.keys())}")
            print(f"\nFirst sample:")
            for key in ["sample_id", "split", "pre_path", "post_path"]:
                print(f"  {key}: {first_row.get(key, 'N/A')}")

    def test_real_samples_triplet_validation(
        self,
        framework,
        mock_imagery_from_real_samples,
        tmp_path,
    ):
        """Test that all created triplets pass validation."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = {
            "imagery_directory": mock_imagery_from_real_samples,
            "sample_patches_directory": str(
                SAMPLE_EXTRACTOR_OUTPUT / "patches"
            ),
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "output_base_dir": str(tmp_path),
        }

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        # Check validation
        validation = result["validation"]

        print(f"\n✓ Validation Report:")
        print(f"  Status: {validation.get('status')}")
        print(f"  Total triplets: {validation.get('total_triplets')}")
        print(f"  Complete triplets: {validation.get('complete_triplets')}")

        # All triplets should be complete
        assert validation["complete_triplets"] == validation["total_triplets"]

    def test_real_samples_directory_structure(
        self,
        framework,
        mock_imagery_from_real_samples,
        tmp_path,
    ):
        """Test that output directory structure is correct."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = {
            "imagery_directory": mock_imagery_from_real_samples,
            "sample_patches_directory": str(
                SAMPLE_EXTRACTOR_OUTPUT / "patches"
            ),
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "output_base_dir": str(tmp_path),
        }

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        output_dir = Path(result["output_directory"])

        # Check directory structure
        print(f"\n✓ Output directory structure:")

        for split in ["train", "val", "test"]:
            split_dir = output_dir / split
            assert split_dir.exists()

            # Count samples in each split
            sample_dirs = [d for d in split_dir.iterdir() if d.is_dir()]
            print(f"  {split}/: {len(sample_dirs)} samples")

            # Check a sample triplet
            if sample_dirs:
                first_sample = sample_dirs[0]
                files = list(first_sample.iterdir())
                file_names = {f.name for f in files}

                print(f"    Sample: {first_sample.name}")
                print(f"    Files: {file_names}")

    def test_real_samples_with_events(
        self,
        framework,
        mock_imagery_from_real_samples,
        tmp_path,
        event_collector,
    ):
        """Test that component publishes events during processing."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        # Subscribe to events
        framework.subscribe_event(
            "dataset_organizer.start", event_collector.collect
        )
        framework.subscribe_event(
            "dataset_organizer.progress", event_collector.collect
        )
        framework.subscribe_event(
            "dataset_organizer.complete", event_collector.collect
        )

        config = {
            "imagery_directory": mock_imagery_from_real_samples,
            "sample_patches_directory": str(
                SAMPLE_EXTRACTOR_OUTPUT / "patches"
            ),
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "output_base_dir": str(tmp_path),
        }

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        # Verify events
        events = event_collector.get_events()

        print(f"\n✓ Events published: {len(events)}")

        start_events = event_collector.get_events("dataset_organizer.start")
        progress_events = event_collector.get_events(
            "dataset_organizer.progress"
        )
        complete_events = event_collector.get_events(
            "dataset_organizer.complete"
        )

        print(f"  Start: {len(start_events)}")
        print(f"  Progress: {len(progress_events)}")
        print(f"  Complete: {len(complete_events)}")

        assert len(start_events) > 0
        assert len(progress_events) > 0
        assert len(complete_events) > 0


class TestDatasetOrganizerWithAllSamples:
    """Optional stress test with all available samples."""

    @pytest.mark.slow
    def test_organize_all_available_samples(
        self,
        framework,
        tmp_path,
    ):
        """Test organizing all samples from sample extractor output."""
        from forest_change_framework.core import get_registry

        if not SAMPLE_EXTRACTOR_OUTPUT.exists():
            pytest.skip("Sample extractor output not available")

        # Load metadata
        metadata_file = SAMPLE_EXTRACTOR_OUTPUT / "samples_metadata.json"
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        samples = metadata.get("samples", [])
        print(f"\n✓ Found {len(samples)} samples in real data")

        # Create imagery directory with all samples
        imagery_dir = tmp_path / "imagery_all"
        imagery_dir.mkdir(parents=True, exist_ok=True)

        for sample in samples:
            sample_id = sample.get("sample_id")
            if not sample_id:
                continue

            sample_dir = imagery_dir / sample_id
            sample_dir.mkdir(parents=True, exist_ok=True)

            metadata_out = {
                "sample_id": sample_id,
                "bbox": [
                    sample["bbox"]["minx"],
                    sample["bbox"]["miny"],
                    sample["bbox"]["maxx"],
                    sample["bbox"]["maxy"],
                ],
                "year": sample.get("year", 2016),
            }

            with open(sample_dir / "metadata.json", "w") as f:
                json.dump(metadata_out, f)

            # Create dummy files
            (sample_dir / "pre.png").write_bytes(b"PNG")
            (sample_dir / "post.png").write_bytes(b"PNG")

        # Run organizer
        registry = get_registry()
        component_class = registry.get("export", "dataset_organizer")

        config = {
            "imagery_directory": str(imagery_dir),
            "sample_patches_directory": str(
                SAMPLE_EXTRACTOR_OUTPUT / "patches"
            ),
            "train_percentage": 70.0,
            "val_percentage": 15.0,
            "test_percentage": 15.0,
            "spatial_tile_size_deg": 5.0,
            "output_base_dir": str(tmp_path / "output_all"),
        }

        component = component_class(framework.event_bus, config)
        component.initialize(config)
        result = component.execute()

        print(f"\n✓ Organized {result['samples_organized']} samples")
        print(f"✓ Validation: {result['validation']['status']}")

        assert result["status"] == "success"
