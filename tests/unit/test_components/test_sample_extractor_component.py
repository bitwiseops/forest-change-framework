"""Unit tests for Sample Extractor Component (Phase 2)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from forest_change_framework.components.export.sample_extractor.component import (
    SampleExtractorComponent,
)


class TestSampleExtractorComponentInitialization:
    """Tests for component initialization and configuration."""

    def test_component_properties(self, event_bus):
        """Test that component has correct name and version."""
        component = SampleExtractorComponent(event_bus)
        assert component.name == "sample_extractor"
        assert component.version == "1.0.0"

    def test_initialize_with_valid_config(self, event_bus):
        """Test successful initialization with valid configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy files
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            config = {
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "samples_per_bin": 5,
                "metadata_format": "csv",
            }

            component = SampleExtractorComponent(event_bus)
            component.initialize(config)

            assert component._samples_per_bin == 5
            assert component._metadata_format == "csv"

    def test_initialize_with_defaults(self, event_bus):
        """Test that optional config parameters use defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            config = {
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
            }

            component = SampleExtractorComponent(event_bus)
            component.initialize(config)

            assert component._samples_per_bin == 10  # default
            assert component._metadata_format == "both"  # default
            assert component._patch_crs == "EPSG:4326"  # default
            assert component._include_metadata_in_tiff is True  # default
            assert component._validate_output is True  # default
            assert component._band == 2  # default (lossyear)

    def test_initialize_missing_required_config(self, event_bus):
        """Test that initialization fails with missing required config."""
        component = SampleExtractorComponent(event_bus)

        config = {
            "aoi_geojson": "/fake/path.geojson",
            # Missing hansen_vrt and output_dir
        }

        with pytest.raises(ValueError, match="Required config parameter missing"):
            component.initialize(config)

    def test_initialize_missing_aoi_file(self, event_bus):
        """Test that initialization fails if AOI GeoJSON doesn't exist."""
        component = SampleExtractorComponent(event_bus)

        config = {
            "aoi_geojson": "/nonexistent/path.geojson",
            "hansen_vrt": "/fake/hansen.vrt",
            "output_dir": "/fake/output",
        }

        with pytest.raises(ValueError, match="AOI GeoJSON file not found"):
            component.initialize(config)

    def test_initialize_invalid_metadata_format(self, event_bus):
        """Test that initialization fails with invalid metadata format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            config = {
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "metadata_format": "invalid",
            }

            component = SampleExtractorComponent(event_bus)
            with pytest.raises(ValueError, match="metadata_format must be one of"):
                component.initialize(config)

    def test_initialize_invalid_samples_per_bin(self, event_bus):
        """Test that initialization fails with invalid samples_per_bin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            config = {
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "samples_per_bin": -5,  # Invalid: negative
            }

            component = SampleExtractorComponent(event_bus)
            with pytest.raises(ValueError, match="samples_per_bin must be positive"):
                component.initialize(config)


class TestSampleExtractorComponentLoadGeojson:
    """Tests for GeoJSON loading."""

    def test_load_valid_geojson(self, event_bus):
        """Test loading valid GeoJSON."""
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"id": 1},
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            geojson_path = Path(tmpdir) / "test.geojson"
            geojson_path.write_text(json.dumps(geojson_data))

            component = SampleExtractorComponent(event_bus)
            result = component._load_geojson(str(geojson_path))

            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) == 1

    def test_load_geojson_missing_features(self, event_bus):
        """Test loading GeoJSON without features key."""
        geojson_data = {"type": "FeatureCollection"}

        with tempfile.TemporaryDirectory() as tmpdir:
            geojson_path = Path(tmpdir) / "test.geojson"
            geojson_path.write_text(json.dumps(geojson_data))

            component = SampleExtractorComponent(event_bus)
            result = component._load_geojson(str(geojson_path))

            assert "features" in result
            assert result["features"] == []

    def test_load_geojson_file_not_found(self, event_bus):
        """Test loading nonexistent GeoJSON."""
        component = SampleExtractorComponent(event_bus)

        with pytest.raises(FileNotFoundError):
            component._load_geojson("/nonexistent/path.geojson")

    def test_load_invalid_json(self, event_bus):
        """Test loading invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            geojson_path = Path(tmpdir) / "invalid.geojson"
            geojson_path.write_text("not valid json {")

            component = SampleExtractorComponent(event_bus)
            with pytest.raises(ValueError, match="Failed to parse GeoJSON"):
                component._load_geojson(str(geojson_path))


class TestSampleExtractorComponentEvents:
    """Tests for event publishing."""

    def test_publish_start_event(self, event_bus):
        """Test that start event is published on execute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            component = SampleExtractorComponent(event_bus)
            component.initialize({
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
            })

            # Mock event publishing
            events = []
            component.publish_event = lambda name, data: events.append((name, data))

            try:
                # Will fail later due to empty geojson, but we can test start event
                component.execute()
            except Exception:
                pass

            # Check start event was published
            assert any(name == "sample_extractor.start" for name, _ in events)

    def test_publish_error_event(self, event_bus):
        """Test that error event is published on failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            # Create a valid GeoJSON so it gets past initial load
            aoi_data = {
                "features": [
                    {
                        "properties": {
                            "cell_id": "cell_001",
                            "bin_category": "low_loss",
                            "minx": -60.5,
                            "miny": -10.2,
                            "maxx": -60.4,
                            "maxy": -10.1,
                            "loss_by_year": {"2010": 5.0},
                        }
                    }
                ]
            }
            aoi_path.write_text(json.dumps(aoi_data))
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            component = SampleExtractorComponent(event_bus)
            component.initialize({
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "samples_per_bin": 1,
            })

            # Mock event publishing
            events = []
            component.publish_event = lambda name, data: events.append((name, data))

            # Execute will fail due to mocked extract_patch_from_vrt raising error
            with patch(
                "forest_change_framework.components.export.sample_extractor.component.extract_patch_from_vrt"
            ) as mock_extract:
                mock_extract.side_effect = Exception("Test extraction error")
                try:
                    component.execute()
                except Exception:
                    pass

            # Check error event was published
            error_events = [
                (name, data) for name, data in events
                if name == "sample_extractor.error"
            ]
            assert len(error_events) > 0


class TestSampleExtractorComponentMetadataFormats:
    """Tests for metadata format handling."""

    def test_write_metadata_csv_only(self, event_bus):
        """Test writing CSV metadata only."""
        pytest.importorskip("pandas")

        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")
            output_dir = Path(tmpdir)

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

            component = SampleExtractorComponent(event_bus)
            component.initialize({
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(output_dir),
                "metadata_format": "csv",
            })
            files = component._write_metadata(manifest, output_dir)

            # GeoJSON is always written, plus CSV when metadata_format includes csv
            assert len(files) == 2
            assert any(f.endswith("samples_metadata.csv") for f in files)
            assert any(f.endswith("samples.geojson") for f in files)
            assert all(Path(f).exists() for f in files)

    def test_write_metadata_json_only(self, event_bus):
        """Test writing JSON metadata only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")
            output_dir = Path(tmpdir)

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

            component = SampleExtractorComponent(event_bus)
            component.initialize({
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(output_dir),
                "metadata_format": "json",
            })
            files = component._write_metadata(manifest, output_dir)

            # GeoJSON is always written, plus JSON when metadata_format includes json
            assert len(files) == 2
            assert any(f.endswith("samples_metadata.json") for f in files)
            assert any(f.endswith("samples.geojson") for f in files)
            assert all(Path(f).exists() for f in files)

    def test_write_metadata_both(self, event_bus):
        """Test writing both CSV and JSON metadata."""
        pytest.importorskip("pandas")

        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")
            output_dir = Path(tmpdir)

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

            component = SampleExtractorComponent(event_bus)
            component.initialize({
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(output_dir),
                "metadata_format": "both",
            })
            files = component._write_metadata(manifest, output_dir)

            # GeoJSON is always written, plus CSV and JSON when metadata_format is both
            assert len(files) == 3
            assert any(f.endswith("samples_metadata.csv") for f in files)
            assert any(f.endswith("samples_metadata.json") for f in files)
            assert any(f.endswith("samples.geojson") for f in files)
            assert all(Path(f).exists() for f in files)


class TestSampleExtractorComponentCleanup:
    """Tests for cleanup method."""

    def test_cleanup_succeeds(self, event_bus):
        """Test that cleanup completes successfully."""
        component = SampleExtractorComponent(event_bus)
        # Should not raise any exception
        component.cleanup()


class TestSampleExtractorComponentWorkflow:
    """Integration-like tests for component workflow."""

    @patch(
        "forest_change_framework.components.export.sample_extractor.component.extract_patch_from_vrt"
    )
    @patch(
        "forest_change_framework.components.export.sample_extractor.component.validate_metadata"
    )
    def test_execute_workflow_with_mock(self, mock_validate, mock_extract, event_bus):
        """Test execute() workflow with mocked patch extraction."""
        pytest.importorskip("pandas")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            aoi_geojson = {
                "features": [
                    {
                        "properties": {
                            "cell_id": "cell_001",
                            "bin_category": "low_loss",
                            "minx": -60.5,
                            "miny": -10.2,
                            "maxx": -60.4,
                            "maxy": -10.1,
                            "loss_by_year": {"2010": 5.0},
                        }
                    },
                    {
                        "properties": {
                            "cell_id": "cell_002",
                            "bin_category": "high_loss",
                            "minx": -61.0,
                            "miny": -11.0,
                            "maxx": -60.9,
                            "maxy": -10.9,
                            "loss_by_year": {"2010": 50.0},
                        }
                    },
                ]
            }

            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text(json.dumps(aoi_geojson))

            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            # Mock extraction to return dummy array
            mock_extract.return_value = np.zeros((100, 100), dtype=np.uint8)

            # Mock validation
            mock_validate.return_value = {
                "valid": True,
                "total_samples": 2,
                "missing_files": [],
                "invalid_bboxes": [],
                "duplicate_ids": [],
                "errors": [],
                "warnings": [],
            }

            component = SampleExtractorComponent(event_bus)
            component.initialize({
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "samples_per_bin": 1,
                "metadata_format": "both",
                "validate": True,
            })

            # Execute
            result = component.execute()

            # Verify
            assert result["status"] == "success"
            assert result["sample_count"] > 0
            assert len(result["metadata_files"]) > 0
            assert result["validation_report"] is not None

    def test_execute_with_empty_geojson(self, event_bus):
        """Test execute with empty GeoJSON (no samples selected)."""
        pytest.importorskip("pandas")

        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')

            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            component = SampleExtractorComponent(event_bus)
            component.initialize({
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "samples_per_bin": 10,
                "validate": False,  # Skip validation
            })

            # Execute should handle empty manifest gracefully
            result = component.execute()

            assert result["status"] == "success"
            assert result["sample_count"] == 0


class TestSampleExtractorComponentConfiguration:
    """Tests for component configuration handling."""

    def test_case_insensitive_metadata_format(self, event_bus):
        """Test that metadata format is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            config = {
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "metadata_format": "JSON",  # Uppercase
            }

            component = SampleExtractorComponent(event_bus)
            component.initialize(config)

            # Should be converted to lowercase
            assert component._metadata_format == "json"

    def test_band_configuration(self, event_bus):
        """Test that band configuration is correctly set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            config = {
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "band": 1,  # Request first band instead of lossyear
            }

            component = SampleExtractorComponent(event_bus)
            component.initialize(config)

            assert component._band == 1

    def test_crs_configuration(self, event_bus):
        """Test that CRS configuration is correctly set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aoi_path = Path(tmpdir) / "aoi.geojson"
            aoi_path.write_text('{"features": []}')
            hansen_path = Path(tmpdir) / "hansen.vrt"
            hansen_path.write_text("")

            config = {
                "aoi_geojson": str(aoi_path),
                "hansen_vrt": str(hansen_path),
                "output_dir": str(Path(tmpdir) / "output"),
                "patch_crs": "EPSG:3857",  # Web Mercator
            }

            component = SampleExtractorComponent(event_bus)
            component.initialize(config)

            assert component._patch_crs == "EPSG:3857"
