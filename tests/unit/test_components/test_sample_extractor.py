"""Unit tests for Sample Extractor component modules."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from forest_change_framework.components.export.sample_extractor import (
    balance_samples_across_years,
    calculate_geotransform,
    create_metadata_dict,
    create_sample_manifest,
    extract_patch_from_vrt,
    extract_patch_from_tiles,
    group_aois_by_year_and_bin,
    save_geotiff,
    select_stratified_samples,
    validate_metadata,
    write_metadata_csv,
    write_metadata_json,
)


# ===== Sampling Tests =====


class TestGroupAoisByYearAndBin:
    """Tests for group_aois_by_year_and_bin function."""

    def test_groups_features_by_year_and_bin(self):
        """Test that features are correctly grouped by year and bin."""
        geojson = {
            "features": [
                {
                    "properties": {
                        "bin_category": "low_loss",
                        "loss_by_year": {"2010": 5.0, "2020": 10.0},
                    }
                },
                {
                    "properties": {
                        "bin_category": "high_loss",
                        "loss_by_year": {"2010": 50.0},
                    }
                },
            ]
        }

        result = group_aois_by_year_and_bin(geojson)

        assert 2010 in result
        assert 2020 in result
        assert "low_loss" in result[2010]
        assert "high_loss" in result[2010]
        assert "low_loss" in result[2020]
        assert len(result[2010]["low_loss"]) == 1
        assert len(result[2020]["low_loss"]) == 1

    def test_handles_empty_geojson(self):
        """Test that empty GeoJSON is handled gracefully."""
        geojson = {"features": []}
        result = group_aois_by_year_and_bin(geojson)
        assert result == {}

    def test_handles_missing_loss_by_year(self):
        """Test handling of features without loss_by_year."""
        geojson = {
            "features": [
                {
                    "properties": {
                        "bin_category": "low_loss",
                        # Missing loss_by_year
                    }
                }
            ]
        }
        result = group_aois_by_year_and_bin(geojson)
        assert result == {}

    def test_handles_invalid_year_values(self, caplog):
        """Test that invalid year values are skipped with warning."""
        geojson = {
            "features": [
                {
                    "properties": {
                        "bin_category": "low_loss",
                        "loss_by_year": {"invalid_year": 5.0},
                    }
                }
            ]
        }
        result = group_aois_by_year_and_bin(geojson)
        assert result == {}


class TestSelectStratifiedSamples:
    """Tests for select_stratified_samples function."""

    def test_selects_correct_number_of_samples(self):
        """Test that the correct number of samples is selected per bin."""
        grouped = {
            2010: {
                "low_loss": [{"id": f"aoi_{i}"} for i in range(100)],
                "high_loss": [{"id": f"aoi_{i}"} for i in range(50)],
            }
        }

        result = select_stratified_samples(grouped, samples_per_bin=10)

        total_selected = sum(
            len(features) for year_data in result.values()
            for features in year_data.values()
        )
        assert total_selected <= 20  # Max 10 per bin

    def test_handles_empty_grouped_aois(self):
        """Test handling of empty grouped AOIs."""
        grouped = {}
        result = select_stratified_samples(grouped, samples_per_bin=10)
        assert result == {}

    def test_handles_bin_with_fewer_samples_than_required(self):
        """Test that selection handles bins with fewer available samples."""
        grouped = {
            2010: {
                "rare_loss": [{"id": "aoi_1"}, {"id": "aoi_2"}],
            }
        }

        result = select_stratified_samples(grouped, samples_per_bin=10)

        # Should select all available (2) instead of requested (10)
        assert len(list(result.values())[0]["rare_loss"]) == 2

    def test_samples_are_random(self):
        """Test that random sampling produces different results."""
        grouped = {
            2010: {
                "medium_loss": [{"id": f"aoi_{i}"} for i in range(100)],
            }
        }

        result1 = select_stratified_samples(grouped, samples_per_bin=5)
        result2 = select_stratified_samples(grouped, samples_per_bin=5)

        # Results should be different due to randomness (with high probability)
        ids1 = {f["id"] for f in result1[2010]["medium_loss"]}
        ids2 = {f["id"] for f in result2[2010]["medium_loss"]}
        assert ids1 != ids2


class TestBalanceSamplesAcrossYears:
    """Tests for balance_samples_across_years function."""

    def test_distributes_samples_equally_across_years(self):
        """Test that samples are distributed equally across years."""
        selected = {
            2010: {"low_loss": [{"id": f"aoi_{i}"} for i in range(5)]},
            2015: {"low_loss": [{"id": f"aoi_{i + 5}"} for i in range(0)]},
            2020: {"low_loss": [{"id": f"aoi_{i + 5}"} for i in range(0)]},
        }

        balanced = balance_samples_across_years(selected, samples_per_bin=10)

        # Check that samples are distributed across years
        assert 2010 in balanced
        assert 2015 in balanced
        assert 2020 in balanced

        # Each year should have roughly equal count
        counts = {
            year: len(balanced[year]["low_loss"]) for year in balanced
            if "low_loss" in balanced[year]
        }
        max_count = max(counts.values())
        min_count = min(counts.values())
        assert max_count - min_count <= 1  # Difference of at most 1

    def test_handles_empty_selected_aois(self):
        """Test handling of empty selected AOIs."""
        selected = {}
        balanced = balance_samples_across_years(selected, samples_per_bin=10)
        assert balanced == {}

    def test_handles_missing_years(self):
        """Test that missing years in output are created."""
        selected = {
            2010: {"low_loss": [{"id": f"aoi_{i}"} for i in range(10)]},
        }

        balanced = balance_samples_across_years(selected, samples_per_bin=10)

        assert 2010 in balanced
        assert len(balanced[2010]["low_loss"]) == 10


class TestCreateSampleManifest:
    """Tests for create_sample_manifest function."""

    def test_creates_manifest_with_unique_ids(self):
        """Test that manifest has unique sample IDs."""
        selected = {
            2010: {
                "low_loss": [
                    {
                        "properties": {
                            "cell_id": "cell_001",
                            "minx": -60.5,
                            "miny": -10.2,
                            "maxx": -60.4,
                            "maxy": -10.1,
                            "loss_by_year": {"2010": 5.0},
                        }
                    }
                ]
            }
        }

        manifest = create_sample_manifest(selected)

        assert len(manifest) == 1
        assert manifest[0]["sample_id"] == "000001"
        assert manifest[0]["aoi_id"] == "cell_001"
        assert manifest[0]["year"] == 2010
        assert manifest[0]["loss_bin"] == "low_loss"

    def test_manifest_contains_all_required_fields(self):
        """Test that manifest includes all required fields."""
        selected = {
            2010: {
                "medium_loss": [
                    {
                        "properties": {
                            "cell_id": "cell_002",
                            "minx": -61.0,
                            "miny": -11.0,
                            "maxx": -60.9,
                            "maxy": -10.9,
                            "loss_by_year": {"2010": 25.0},
                        }
                    }
                ]
            }
        }

        manifest = create_sample_manifest(selected)

        required_fields = {
            "sample_id",
            "aoi_id",
            "year",
            "loss_bin",
            "minx",
            "miny",
            "maxx",
            "maxy",
            "loss_percentage",
        }
        assert required_fields.issubset(manifest[0].keys())

    def test_sequential_sample_ids(self):
        """Test that sample IDs are sequential."""
        selected = {
            2010: {
                "low_loss": [
                    {
                        "properties": {
                            "cell_id": f"cell_{i:03d}",
                            "minx": -60.5 - i * 0.1,
                            "miny": -10.2,
                            "maxx": -60.4 - i * 0.1,
                            "maxy": -10.1,
                            "loss_by_year": {"2010": 5.0},
                        }
                    }
                    for i in range(5)
                ]
            }
        }

        manifest = create_sample_manifest(selected)

        assert len(manifest) == 5
        for i, sample in enumerate(manifest, 1):
            assert sample["sample_id"] == f"{i:06d}"

    def test_handles_empty_selected_aois(self):
        """Test handling of empty selected AOIs."""
        selected = {}
        manifest = create_sample_manifest(selected)
        assert manifest == []


# ===== Metadata Tests =====


class TestCreateMetadataDict:
    """Tests for create_metadata_dict function."""

    def test_creates_valid_metadata_structure(self):
        """Test that metadata dict has correct structure."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        metadata = create_metadata_dict(manifest, "patches/")

        assert "metadata" in metadata
        assert "samples" in metadata
        assert metadata["metadata"]["total_samples"] == 1
        assert len(metadata["samples"]) == 1

    def test_adds_tiff_path_correctly(self):
        """Test that TIFF paths are generated correctly."""
        manifest = [
            {
                "sample_id": "000042",
                "aoi_id": "cell_042",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        metadata = create_metadata_dict(manifest, "custom_patches")

        assert metadata["samples"][0]["tiff_path"] == "custom_patches/000042.tif"

    def test_includes_all_sample_fields(self):
        """Test that all sample fields are included."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2020,
                "loss_bin": "high_loss",
                "minx": -61.0,
                "miny": -11.0,
                "maxx": -60.9,
                "maxy": -10.9,
                "loss_percentage": 75.0,
            }
        ]

        metadata = create_metadata_dict(manifest, "patches/")

        sample = metadata["samples"][0]
        assert sample["sample_id"] == "000001"
        assert sample["aoi_id"] == "cell_001"
        assert sample["year"] == 2020
        assert sample["loss_bin"] == "high_loss"
        assert sample["loss_percentage"] == 75.0
        assert sample["bbox"]["minx"] == -61.0


class TestWriteMetadataJson:
    """Tests for write_metadata_json function."""

    def test_writes_valid_json_file(self):
        """Test that JSON file is written correctly."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "metadata.json"
            write_metadata_json(manifest, str(output_path))

            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
            assert "metadata" in data
            assert "samples" in data
            assert len(data["samples"]) == 1

    def test_creates_parent_directories(self):
        """Test that parent directories are created."""
        manifest = []

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "a" / "b" / "c" / "metadata.json"
            write_metadata_json(manifest, str(nested_path))

            assert nested_path.parent.exists()
            assert nested_path.exists()


class TestWriteMetadataCsv:
    """Tests for write_metadata_csv function."""

    def test_writes_csv_with_correct_columns(self):
        """Test that CSV has correct columns."""
        pytest.importorskip("pandas")

        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "metadata.csv"
            write_metadata_csv(manifest, str(output_path))

            assert output_path.exists()
            import pandas as pd

            df = pd.read_csv(output_path)
            expected_columns = {
                "sample_id",
                "aoi_id",
                "year",
                "loss_bin",
                "minx",
                "miny",
                "maxx",
                "maxy",
                "loss_percentage",
                "tiff_path",
            }
            assert expected_columns.issubset(df.columns)

    def test_csv_data_matches_manifest(self):
        """Test that CSV data matches input manifest."""
        pytest.importorskip("pandas")
        import pandas as pd

        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            },
            {
                "sample_id": "000002",
                "aoi_id": "cell_002",
                "year": 2020,
                "loss_bin": "high_loss",
                "minx": -61.0,
                "miny": -11.0,
                "maxx": -60.9,
                "maxy": -10.9,
                "loss_percentage": 75.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "metadata.csv"
            write_metadata_csv(manifest, str(output_path))

            df = pd.read_csv(output_path, dtype={"sample_id": str})
            assert len(df) == 2
            assert df.iloc[0]["sample_id"] == "000001"
            assert df.iloc[1]["sample_id"] == "000002"

    def test_missing_pandas_raises_error(self):
        """Test that ImportError is raised if pandas not available."""
        manifest = []

        # Save the original pandas module
        import sys

        original_pandas = sys.modules.get("pandas")
        try:
            # Temporarily remove pandas from sys.modules and set it to None in the metadata module
            sys.modules["pandas"] = None
            # Reload the metadata module to pick up the None pandas
            import importlib

            import forest_change_framework.components.export.sample_extractor.metadata as metadata_module

            importlib.reload(metadata_module)
            with pytest.raises(ImportError, match="pandas required"):
                metadata_module.write_metadata_csv(manifest, "dummy.csv")
        finally:
            # Restore pandas
            if original_pandas is not None:
                sys.modules["pandas"] = original_pandas
            # Reload again to restore pandas
            import importlib

            import forest_change_framework.components.export.sample_extractor.metadata as metadata_module

            importlib.reload(metadata_module)


class TestValidateMetadata:
    """Tests for validate_metadata function."""

    def test_validates_missing_tiff_files(self):
        """Test that missing TIFF files are detected."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            report = validate_metadata(manifest, tmpdir)

            assert report["valid"] is False
            assert len(report["missing_files"]) == 1

    def test_detects_invalid_bboxes(self):
        """Test that invalid bounding boxes are detected."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.4,  # minx > maxx
                "miny": -10.2,
                "maxx": -60.5,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            report = validate_metadata(manifest, tmpdir)

            assert report["valid"] is False
            assert len(report["invalid_bboxes"]) == 1

    def test_detects_duplicate_sample_ids(self):
        """Test that duplicate sample IDs are detected."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            },
            {
                "sample_id": "000001",  # Duplicate
                "aoi_id": "cell_002",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -61.0,
                "miny": -11.0,
                "maxx": -60.9,
                "maxy": -10.9,
                "loss_percentage": 5.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            report = validate_metadata(manifest, tmpdir)

            assert report["valid"] is False
            assert len(report["duplicate_ids"]) == 1

    def test_valid_manifest_passes(self):
        """Test that valid manifest passes validation."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": -60.5,
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            patches_dir = Path(tmpdir)
            patches_dir.mkdir(exist_ok=True)
            # Create dummy TIFF file
            (patches_dir / "000001.tif").touch()

            report = validate_metadata(manifest, str(patches_dir))

            assert report["valid"] is True
            assert len(report["missing_files"]) == 0
            assert len(report["invalid_bboxes"]) == 0

    def test_detects_missing_bbox_values(self):
        """Test that missing bbox values are detected."""
        manifest = [
            {
                "sample_id": "000001",
                "aoi_id": "cell_001",
                "year": 2010,
                "loss_bin": "low_loss",
                "minx": None,  # Missing
                "miny": -10.2,
                "maxx": -60.4,
                "maxy": -10.1,
                "loss_percentage": 5.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            report = validate_metadata(manifest, tmpdir)

            assert report["valid"] is False
            assert len(report["invalid_bboxes"]) == 1


# ===== Extraction Tests =====


class TestCalculateGeotransform:
    """Tests for calculate_geotransform function."""

    def test_calculates_correct_transform(self):
        """Test that geotransform is calculated correctly."""
        bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        width = 340
        height = 367

        transform = calculate_geotransform(bbox, width, height)

        # Should return tuple of 6 values
        assert len(transform) == 6
        origin_x, pixel_width, _, origin_y, _, pixel_height = transform

        # Origin should be at top-left
        assert origin_x == -60.5
        assert origin_y == -10.1  # maxy in geographic coords

        # Pixel dimensions should be positive
        assert pixel_width > 0
        assert pixel_height < 0  # Negative for row-major order

    def test_transform_with_different_dimensions(self):
        """Test transform calculation with different dimensions."""
        bbox = {"minx": 0, "miny": 0, "maxx": 10, "maxy": 10}

        # Square case
        transform1 = calculate_geotransform(bbox, 100, 100)
        assert transform1[1] == 0.1  # pixel_width
        assert transform1[5] == -0.1  # pixel_height (negative)

        # Rectangular case
        transform2 = calculate_geotransform(bbox, 200, 100)
        assert transform2[1] == 0.05  # pixel_width
        assert transform2[5] == -0.1  # pixel_height


class TestExtractPatchFromVrt:
    """Tests for extract_patch_from_vrt function."""

    def test_missing_rasterio_raises_import_error(self):
        """Test that ImportError is raised if rasterio not available."""
        with patch("forest_change_framework.components.export.sample_extractor.extraction.rasterio", None):
            bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
            with pytest.raises(ImportError, match="rasterio required"):
                extract_patch_from_vrt("dummy.vrt", bbox)

    def test_invalid_vrt_file_raises_error(self):
        """Test that FileNotFoundError is raised for missing VRT."""
        bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        with pytest.raises(FileNotFoundError):
            extract_patch_from_vrt("/nonexistent/path.vrt", bbox)

    def test_invalid_bbox_raises_error(self):
        """Test that ValueError is raised for invalid bbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy VRT file
            vrt_path = Path(tmpdir) / "dummy.vrt"
            vrt_path.touch()

            # Test with invalid bbox (minx > maxx)
            bbox = {"minx": -60.4, "miny": -10.2, "maxx": -60.5, "maxy": -10.1}
            with pytest.raises(ValueError, match="Invalid bbox"):
                extract_patch_from_vrt(str(vrt_path), bbox)

            # Test with missing keys
            bbox = {"minx": -60.5, "miny": -10.2}
            with pytest.raises(ValueError, match="must contain keys"):
                extract_patch_from_vrt(str(vrt_path), bbox)

    @patch("forest_change_framework.components.export.sample_extractor.extraction.Path.exists")
    @patch("forest_change_framework.components.export.sample_extractor.extraction.rasterio")
    def test_extract_returns_numpy_array(self, mock_rasterio, mock_exists):
        """Test that extraction returns numpy array."""
        # Mock file exists check
        mock_exists.return_value = True

        # Mock rasterio
        mock_src = MagicMock()
        mock_src.window.return_value = MagicMock(col_off=0, row_off=0)
        mock_src.read.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_rasterio.open.return_value.__enter__.return_value = mock_src

        bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        result = extract_patch_from_vrt("dummy.vrt", bbox)

        assert isinstance(result, np.ndarray)
        assert result.shape == (100, 100)


class TestSaveGeotiff:
    """Tests for save_geotiff function."""

    def test_missing_rasterio_raises_import_error(self):
        """Test that ImportError is raised if rasterio not available."""
        with patch("forest_change_framework.components.export.sample_extractor.extraction.rasterio", None):
            data = np.zeros((100, 100), dtype=np.uint8)
            bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
            with pytest.raises(ImportError, match="rasterio required"):
                save_geotiff("dummy.tif", data, bbox)

    def test_invalid_data_shape_raises_error(self):
        """Test that ValueError is raised for invalid data shape."""
        bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        data_3d = np.zeros((10, 100, 100), dtype=np.uint8)

        with pytest.raises(ValueError, match="Expected 2D array"):
            save_geotiff("dummy.tif", data_3d, bbox)

    def test_missing_bbox_keys_raises_error(self):
        """Test that ValueError is raised for incomplete bbox."""
        data = np.zeros((100, 100), dtype=np.uint8)
        bbox = {"minx": -60.5, "miny": -10.2}  # Missing maxx, maxy

        with pytest.raises(ValueError, match="must contain keys"):
            save_geotiff("dummy.tif", data, bbox)

    @patch("forest_change_framework.components.export.sample_extractor.extraction.rasterio")
    def test_writes_geotiff_with_metadata(self, mock_rasterio):
        """Test that GeoTIFF is written with metadata tags."""
        # Mock rasterio
        mock_dst = MagicMock()
        mock_rasterio.open.return_value.__enter__.return_value = mock_dst

        data = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}
        metadata = {
            "sample_id": "000001",
            "aoi_id": "cell_001",
            "year": 2010,
            "loss_bin": "low_loss",
            "loss_percentage": 5.0,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.tif")
            save_geotiff(output_path, data, bbox, metadata=metadata)

            # Verify write was called
            mock_rasterio.open.assert_called_once()

    @patch("forest_change_framework.components.export.sample_extractor.extraction.rasterio")
    def test_creates_parent_directories(self, mock_rasterio):
        """Test that parent directories are created."""
        mock_dst = MagicMock()
        mock_rasterio.open.return_value.__enter__.return_value = mock_dst

        data = np.zeros((100, 100), dtype=np.uint8)
        bbox = {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1}

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = str(Path(tmpdir) / "a" / "b" / "c" / "test.tif")
            save_geotiff(nested_path, data, bbox)

            assert Path(nested_path).parent.exists()


# ===== Integration-like Tests =====


class TestFullWorkflow:
    """Tests for end-to-end sampling and metadata generation."""

    def test_complete_sampling_and_metadata_workflow(self):
        """Test complete workflow from grouping to manifest creation."""
        # Create test GeoJSON
        geojson = {
            "features": [
                {
                    "properties": {
                        "cell_id": f"cell_{i:03d}",
                        "bin_category": "low_loss" if i % 2 == 0 else "high_loss",
                        "minx": -60.5 - i * 0.01,
                        "miny": -10.2,
                        "maxx": -60.4 - i * 0.01,
                        "maxy": -10.1,
                        "loss_by_year": {"2010": 5.0, "2020": 10.0},
                    }
                }
                for i in range(20)
            ]
        }

        # Step 1: Group by year and bin
        grouped = group_aois_by_year_and_bin(geojson)
        assert len(grouped) == 2  # 2010 and 2020
        assert "low_loss" in grouped[2010]
        assert "high_loss" in grouped[2010]

        # Step 2: Select stratified samples
        selected = select_stratified_samples(grouped, samples_per_bin=5)
        total = sum(len(f) for y in selected.values() for f in y.values())
        assert total <= 10  # At most 5 per bin

        # Step 3: Balance across years
        balanced = balance_samples_across_years(selected, samples_per_bin=5)
        assert len(balanced) <= 2  # Max 2 years

        # Step 4: Create manifest
        manifest = create_sample_manifest(balanced)
        assert len(manifest) > 0
        assert all("sample_id" in s for s in manifest)

        # Step 5: Create metadata
        metadata = create_metadata_dict(manifest, "patches/")
        assert metadata["metadata"]["total_samples"] == len(manifest)
        assert len(metadata["samples"]) == len(manifest)
