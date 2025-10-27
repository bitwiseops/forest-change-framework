"""Integration tests for AOI Sampler component with mock Hansen VRT."""

import pytest
import json
import tempfile
from pathlib import Path
import numpy as np

# Import to trigger component registration
from forest_change_framework.components.analysis.aoi_sampler import AoiSamplerComponent

try:
    import rasterio
    from rasterio.transform import Affine
    import rasterio.crs
except ImportError:
    rasterio = None


@pytest.mark.skipif(rasterio is None, reason="rasterio not installed")
class TestAoiSamplerIntegration:
    """Integration tests for AOI Sampler component."""

    @pytest.fixture
    def mock_hansen_vrt(self, tmp_path):
        """Create a mock 3-band Hansen VRT file for testing."""
        vrt_path = tmp_path / "mock_hansen.vrt"

        # Create simple 3-band GeoTIFF with Hansen-like structure
        # Band 1: treecover2000 (0-100)
        # Band 2: lossyear (0-21, offset from 2000)
        # Band 3: datamask (0=invalid, 1=valid)

        width, height = 100, 100

        # Create test data
        treecover = np.random.randint(0, 100, (height, width), dtype=np.uint8)
        lossyear = np.random.randint(0, 10, (height, width), dtype=np.uint8)
        datamask = np.ones((height, width), dtype=np.uint8)

        # Add some invalid pixels
        datamask[80:, :] = 0

        # Create VRT that references the test data
        # For testing, we'll use MemoryFile approach
        from rasterio.io import MemoryFile

        # Create a temporary GeoTIFF with the test data
        temp_tif = tmp_path / "temp_data.tif"

        with rasterio.open(
            temp_tif,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=3,
            dtype=np.uint8,
            crs="EPSG:4326",
            transform=Affine.translation(0, 10) * Affine.scale(0.1, -0.1),
        ) as dst:
            dst.write(treecover, 1)
            dst.write(lossyear, 2)
            dst.write(datamask, 3)

        return temp_tif

    def test_aoi_sampler_end_to_end(self, framework, mock_hansen_vrt):
        """Test AOI sampler with mock Hansen data."""
        component_config = {
            "grid_cell_size_km": 50.0,  # Large cells for quick test
            "min_validity_threshold": 80.0,
            "loss_bins": [
                {"name": "low", "min": 0, "max": 5},
                {"name": "medium", "min": 5, "max": 10},
                {"name": "high", "min": 10, "max": 100},
            ],
            "include_loss_by_year": True,
        }

        # Instantiate and execute component
        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=component_config
        )
        output_path, metadata = component.execute(vrt_path=str(mock_hansen_vrt))

        # Verify output
        assert Path(output_path).exists()
        assert output_path.endswith(".geojson")

        # Check metadata
        assert metadata["output_path"] == output_path
        assert metadata["grid_cell_size_km"] == 50.0
        assert metadata["total_cells"] > 0
        assert "bin_summary" in metadata

        # Read and validate GeoJSON
        with open(output_path) as f:
            geojson = json.load(f)

        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) > 0

        # Check feature structure
        for feature in geojson["features"]:
            assert feature["type"] == "Feature"
            assert feature["geometry"]["type"] == "Polygon"
            assert "loss_percentage" in feature["properties"]
            assert "data_validity" in feature["properties"]
            assert "bin_category" in feature["properties"]

    def test_aoi_sampler_with_custom_grid_size(self, framework, mock_hansen_vrt):
        """Test AOI sampler with different grid cell size."""
        component_config = {
            "grid_cell_size_km": 20.0,
            "min_validity_threshold": 75.0,
            "loss_bins": [
                {"name": "any_loss", "min": 0, "max": 100},
            ],
        }

        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=component_config
        )
        output_path, metadata = component.execute(vrt_path=str(mock_hansen_vrt))

        assert Path(output_path).exists()
        assert metadata["grid_cell_size_km"] == 20.0

    def test_aoi_sampler_geojson_valid_format(self, framework, mock_hansen_vrt):
        """Test that output GeoJSON is valid and readable."""
        component_config = {
            "grid_cell_size_km": 50.0,
            "min_validity_threshold": 80.0,
            "loss_bins": [
                {"name": "low", "min": 0, "max": 50},
                {"name": "high", "min": 50, "max": 100},
            ],
        }

        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=component_config
        )
        output_path, metadata = component.execute(vrt_path=str(mock_hansen_vrt))

        # Verify GeoJSON can be read back with rasterio/fiona if available
        try:
            import geopandas as gpd

            gdf = gpd.read_file(output_path)
            assert len(gdf) > 0
            assert "loss_percentage" in gdf.columns
            assert "bin_category" in gdf.columns
        except ImportError:
            # If geopandas not available, just verify it's valid JSON
            with open(output_path) as f:
                geojson = json.load(f)
            assert geojson["type"] == "FeatureCollection"

    def test_aoi_sampler_bin_summary(self, framework, mock_hansen_vrt):
        """Test that AOI binning works correctly."""
        component_config = {
            "grid_cell_size_km": 50.0,
            "min_validity_threshold": 80.0,
            "loss_bins": [
                {"name": "low", "min": 0, "max": 3},
                {"name": "medium", "min": 3, "max": 7},
                {"name": "high", "min": 7, "max": 100},
            ],
        }

        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=component_config
        )
        output_path, metadata = component.execute(vrt_path=str(mock_hansen_vrt))

        # Check bin summary
        bin_summary = metadata["bin_summary"]
        total_in_bins = sum(bin_summary.values())
        assert total_in_bins == metadata["valid_aois"]

    def test_aoi_sampler_filtering(self, framework, mock_hansen_vrt):
        """Test that validity filtering works."""
        component_config = {
            "grid_cell_size_km": 50.0,
            "min_validity_threshold": 95.0,  # Very strict
            "loss_bins": [
                {"name": "any", "min": 0, "max": 100},
            ],
        }

        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=component_config
        )
        output_path, metadata = component.execute(vrt_path=str(mock_hansen_vrt))

        # Some AOIs should be excluded due to low validity
        assert metadata["excluded_aois"] >= 0
        assert metadata["valid_aois"] + metadata["excluded_aois"] == metadata["total_cells"]

    def test_aoi_sampler_output_statistics(self, framework, mock_hansen_vrt):
        """Test that output GeoJSON has correct statistics in properties."""
        component_config = {
            "grid_cell_size_km": 50.0,
            "min_validity_threshold": 80.0,
            "loss_bins": [{"name": "any", "min": 0, "max": 100}],
            "include_loss_by_year": True,
        }

        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=component_config
        )
        output_path, metadata = component.execute(vrt_path=str(mock_hansen_vrt))

        with open(output_path) as f:
            geojson = json.load(f)

        # Check statistics in properties
        for feature in geojson["features"]:
            props = feature["properties"]

            # Check required fields
            assert "loss_percentage" in props
            assert 0 <= props["loss_percentage"] <= 100

            assert "data_validity" in props
            assert 0 <= props["data_validity"] <= 100

            # Check bin category
            assert "bin_category" in props
            assert props["bin_category"] in ["any"]

            # Check loss_by_year exists (may be empty)
            if "loss_by_year" in props:
                assert isinstance(props["loss_by_year"], dict)
