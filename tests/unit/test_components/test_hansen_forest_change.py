"""
Unit tests for the Hansen Forest Change component.

Tests the Hansen forest change data ingestion component functionality,
including lat/lon grid parsing, tile discovery, and component lifecycle.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from forest_change_framework import BaseFramework
from forest_change_framework.components.data_ingestion.hansen_forest_change import (
    HansenForestChangeComponent,
)
from forest_change_framework.components.data_ingestion.hansen_forest_change.grid_utils import (
    parse_tile_list,
    bbox_to_tiles,
    get_tile_bounds,
)


@pytest.mark.unit
class TestGridUtils:
    """Test grid utility functions for lat/lon tiles."""

    def test_get_tile_bounds_00N_000E(self):
        """Test tile bounds calculation for 00N_000E (equator, prime meridian)."""
        bounds = get_tile_bounds("00N_000E")
        assert bounds["minx"] == 0.0
        assert bounds["maxx"] == 10.0
        assert bounds["miny"] == 0.0
        assert bounds["maxy"] == 10.0

    def test_get_tile_bounds_10N_010E(self):
        """Test tile bounds calculation for 10N_010E."""
        bounds = get_tile_bounds("10N_010E")
        assert bounds["minx"] == 10.0
        assert bounds["maxx"] == 20.0
        assert bounds["miny"] == 10.0
        assert bounds["maxy"] == 20.0

    def test_get_tile_bounds_10S_010W(self):
        """Test tile bounds calculation for 10S_010W (southern, western)."""
        bounds = get_tile_bounds("10S_010W")
        assert bounds["minx"] == -20.0
        assert bounds["maxx"] == -10.0
        assert bounds["miny"] == -20.0
        assert bounds["maxy"] == -10.0

    def test_get_tile_bounds_case_insensitive(self):
        """Test that tile IDs are case insensitive."""
        bounds1 = get_tile_bounds("00N_000E")
        bounds2 = get_tile_bounds("00n_000e")
        assert bounds1 == bounds2

    def test_get_tile_bounds_invalid_format(self):
        """Test error on invalid tile ID format."""
        with pytest.raises(ValueError):
            get_tile_bounds("invalid")

        with pytest.raises(ValueError):
            get_tile_bounds("90N_000E")  # latitude out of range

        with pytest.raises(ValueError):
            get_tile_bounds("00N_190E")  # longitude out of range

    def test_parse_tile_list(self):
        """Test parsing tile list from filenames."""
        lines = [
            "Hansen_GFC-2024-v1.12_lossyear_00N_000E.tif",
            "Hansen_GFC-2024-v1.12_lossyear_10N_010E.tif",
            "Hansen_GFC-2024-v1.12_lossyear_00N_010W.tif",
        ]
        tiles = parse_tile_list(lines)

        assert len(tiles) == 3
        assert "00N_000E" in tiles
        assert "10N_010E" in tiles
        assert "00N_010W" in tiles

    def test_parse_tile_list_with_whitespace(self):
        """Test parsing tile list with whitespace."""
        lines = [
            "  Hansen_GFC-2024-v1.12_lossyear_00N_000E.tif  ",
            "Hansen_GFC-2024-v1.12_lossyear_10N_010E.tif\n",
            "\tHansen_GFC-2024-v1.12_lossyear_00N_010W.tif\t",
        ]
        tiles = parse_tile_list(lines)

        assert len(tiles) == 3
        assert "00N_000E" in tiles

    def test_parse_tile_list_ignores_invalid(self):
        """Test that invalid tiles are skipped."""
        lines = [
            "Hansen_GFC-2024-v1.12_lossyear_00N_000E.tif",
            "invalid_filename.tif",
            "Hansen_GFC-2024-v1.12_lossyear_10N_010E.tif",
            "Hansen_GFC-2024-v1.12_lossyear_90N_000E.tif",  # invalid latitude
        ]
        tiles = parse_tile_list(lines)

        assert len(tiles) == 2
        assert "00N_000E" in tiles
        assert "10N_010E" in tiles

    def test_bbox_to_tiles_single_tile(self):
        """Test finding tiles for a small bbox."""
        tiles = {
            "00N_000E": get_tile_bounds("00N_000E"),
            "10N_000E": get_tile_bounds("10N_000E"),
            "00N_010E": get_tile_bounds("00N_010E"),
        }

        # Bbox entirely within 00N_000E
        bbox = {"minx": 1, "miny": 1, "maxx": 9, "maxy": 9}
        result = bbox_to_tiles(bbox, tiles)

        assert len(result) == 1
        assert "00N_000E" in result

    def test_bbox_to_tiles_multiple_tiles(self):
        """Test finding multiple overlapping tiles."""
        tiles = {
            "00N_000E": get_tile_bounds("00N_000E"),
            "10N_000E": get_tile_bounds("10N_000E"),
            "00N_010E": get_tile_bounds("00N_010E"),
            "10N_010E": get_tile_bounds("10N_010E"),
        }

        # Bbox spanning 2x2 tiles
        bbox = {"minx": 5, "miny": 5, "maxx": 15, "maxy": 15}
        result = bbox_to_tiles(bbox, tiles)

        assert len(result) == 4

    def test_bbox_to_tiles_invalid_bbox_missing_key(self):
        """Test error when bbox missing required key."""
        tiles = {"00N_000E": get_tile_bounds("00N_000E")}
        bbox = {"minx": 0, "miny": 0, "maxx": 10}  # missing maxy

        with pytest.raises(ValueError):
            bbox_to_tiles(bbox, tiles)

    def test_bbox_to_tiles_invalid_bbox_coordinates(self):
        """Test error with invalid coordinates."""
        tiles = {"00N_000E": get_tile_bounds("00N_000E")}

        # minx > maxx
        with pytest.raises(ValueError):
            bbox_to_tiles({"minx": 100, "miny": 0, "maxx": 50, "maxy": 10}, tiles)

        # out of WGS84 bounds
        with pytest.raises(ValueError):
            bbox_to_tiles({"minx": -200, "miny": 0, "maxx": 0, "maxy": 10}, tiles)

    def test_bbox_to_tiles_empty_result(self):
        """Test when no tiles overlap bbox."""
        tiles = {"00N_000E": get_tile_bounds("00N_000E")}

        # Bbox far from 00N_000E
        bbox = {"minx": 100, "miny": 50, "maxx": 110, "maxy": 60}
        result = bbox_to_tiles(bbox, tiles)

        assert len(result) == 0


@pytest.mark.unit
class TestHansenForestChangeComponent:
    """Test HansenForestChangeComponent functionality."""

    def test_component_registered(self):
        """Test that component is registered."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        categories = registry.list_categories()
        assert "data_ingestion" in categories

        components = registry.list_components("data_ingestion")
        assert "hansen_forest_change" in components["data_ingestion"]

    def test_component_instantiation(self, framework, tmp_path):
        """Test instantiating the component."""
        component = framework.instantiate_component(
            "data_ingestion",
            "hansen_forest_change",
            {"data_folder": str(tmp_path)},
        )

        assert component is not None
        assert component.name == "hansen_forest_change"
        assert component.version == "1.0.0"

    def test_component_initialize_creates_folder(self, framework, tmp_path):
        """Test that initialize creates data and output folders."""
        data_folder = tmp_path / "hansen_data"
        output_folder = tmp_path / "hansen_output"
        assert not data_folder.exists()
        assert not output_folder.exists()

        framework.instantiate_component(
            "data_ingestion",
            "hansen_forest_change",
            {"data_folder": str(data_folder), "output_folder": str(output_folder)},
        )

        assert data_folder.exists()
        assert output_folder.exists()

    def test_component_requires_bbox(self, framework, tmp_path):
        """Test that execute requires bbox parameter."""
        component = framework.instantiate_component(
            "data_ingestion",
            "hansen_forest_change",
            {"data_folder": str(tmp_path)},
        )

        with pytest.raises(ValueError, match="bbox"):
            component.execute()

    def test_component_publishes_start_event(self, framework, tmp_path, event_collector):
        """Test that component publishes start event."""
        pytest.importorskip("requests")

        from unittest.mock import patch

        with patch(
            "forest_change_framework.components.data_ingestion.hansen_forest_change.component.requests"
        ) as mock_requests:
            # Mock tile list download
            mock_response = Mock()
            mock_response.text = "Hansen_GFC-2024-v1.12_lossyear_00N_000E.tif\nHansen_GFC-2024-v1.12_lossyear_10N_010E.tif"
            mock_requests.get.return_value = mock_response

            framework.subscribe_event("hansen.start", event_collector.collect)

            output_folder = tmp_path / "output"
            component = framework.instantiate_component(
                "data_ingestion",
                "hansen_forest_change",
                {"data_folder": str(tmp_path), "output_folder": str(output_folder)},
            )

            bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}

            try:
                component.execute(bbox=bbox)
            except Exception:
                pass  # We expect this to fail due to mocking, just checking for events

            assert event_collector.has_event("hansen.start")

    def test_component_publishes_tile_list_event(
        self, framework, tmp_path, event_collector
    ):
        """Test that component publishes tile list event."""
        pytest.importorskip("requests")

        from unittest.mock import patch

        with patch(
            "forest_change_framework.components.data_ingestion.hansen_forest_change.component.requests"
        ) as mock_requests:
            mock_response = Mock()
            mock_response.text = "Hansen_GFC-2024-v1.12_lossyear_00N_000E.tif"
            mock_requests.get.return_value = mock_response

            framework.subscribe_event("hansen.tile_list_downloaded", event_collector.collect)

            output_folder = tmp_path / "output"
            component = framework.instantiate_component(
                "data_ingestion",
                "hansen_forest_change",
                {"data_folder": str(tmp_path), "output_folder": str(output_folder)},
            )

            bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}

            try:
                component.execute(bbox=bbox)
            except Exception:
                pass

            assert event_collector.has_event("hansen.tile_list_downloaded")

    def test_component_cleanup(self, framework, tmp_path):
        """Test component cleanup method."""
        component = framework.instantiate_component(
            "data_ingestion",
            "hansen_forest_change",
            {"data_folder": str(tmp_path)},
        )

        # Set some internal state
        component._tiles_available = {"00N_000E": {}}
        component._downloaded_tiles = {"00N_000E": {}}

        assert len(component._tiles_available) > 0
        assert len(component._downloaded_tiles) > 0

        component.cleanup()

        assert len(component._tiles_available) == 0
        assert len(component._downloaded_tiles) == 0
        # Cleanup is now simpler since we don't manage MemoryFiles anymore

    def test_metadata_includes_band_info(self, framework, tmp_path):
        """Test that metadata includes band information."""
        component = framework.instantiate_component(
            "data_ingestion",
            "hansen_forest_change",
            {"data_folder": str(tmp_path)},
        )

        # Create metadata
        bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}
        tile_ids = ["00N_000E", "10N_000E"]
        output_path = tmp_path / "test_mosaic.tif"
        mosaic_info = {"shape": (1000, 1000), "crs": "EPSG:4326"}
        metadata = component._prepare_metadata(bbox, tile_ids, output_path, mosaic_info)

        # Verify structure
        assert "band_info" in metadata
        assert "band_1" in metadata["band_info"]
        assert "band_2" in metadata["band_info"]
        assert "band_3" in metadata["band_info"]

        # Verify band names
        assert metadata["band_info"]["band_1"]["name"] == "treecover2000"
        assert metadata["band_info"]["band_2"]["name"] == "lossyear"
        assert metadata["band_info"]["band_3"]["name"] == "datamask"

        # Verify output path info is included
        assert "output_path" in metadata
        assert "output_shape" in metadata
        assert "output_crs" in metadata
        assert metadata["output_shape"] == (1000, 1000)
        assert metadata["output_crs"] == "EPSG:4326"


@pytest.mark.unit
class TestHansenGridIntegration:
    """Integration tests for grid utilities with component."""

    def test_bbox_to_tiles_all_tiles(self):
        """Test tile discovery with realistic dataset."""
        # Build a grid of tiles
        tiles = {}
        latitudes = ["00N", "10N", "20N"]
        longitudes = ["000E", "010E", "020E"]

        for lat in latitudes:
            for lon in longitudes:
                tile_id = f"{lat}_{lon}"
                tiles[tile_id] = get_tile_bounds(tile_id)

        # Bbox covering multiple tiles
        bbox = {"minx": 5, "miny": 5, "maxx": 25, "maxy": 25}
        result = bbox_to_tiles(bbox, tiles)

        # Should find several tiles
        assert len(result) > 0
        assert all("_" in t for t in result)

    def test_tile_bounds_north_south_coverage(self):
        """Test that tiles cover north and south correctly."""
        # Northern hemisphere tiles
        north_bounds = get_tile_bounds("00N_000E")
        assert north_bounds["maxy"] == 10.0
        assert north_bounds["miny"] == 0.0

        # Southern hemisphere tiles
        south_bounds = get_tile_bounds("10S_000E")
        assert south_bounds["maxy"] == -10.0
        assert south_bounds["miny"] == -20.0

    def test_tile_bounds_east_west_coverage(self):
        """Test that tiles cover east and west correctly."""
        # Eastern hemisphere
        east_bounds = get_tile_bounds("00N_000E")
        assert east_bounds["minx"] == 0.0
        assert east_bounds["maxx"] == 10.0

        # Western hemisphere
        west_bounds = get_tile_bounds("00N_010W")
        assert west_bounds["minx"] == -20.0
        assert west_bounds["maxx"] == -10.0


@pytest.mark.unit
class TestHansenErrorHandling:
    """Test error handling in Hansen component."""

    def test_invalid_data_folder(self, framework):
        """Test error when data folder cannot be created."""
        from forest_change_framework.core.exceptions import ComponentError

        with pytest.raises(ComponentError):
            framework.instantiate_component(
                "data_ingestion",
                "hansen_forest_change",
                {"data_folder": "/root/impossible/path/hansen_tiles"},
            )

    def test_tile_download_error(self, framework, tmp_path, event_collector):
        """Test handling of download errors."""
        pytest.importorskip("requests")

        from unittest.mock import patch

        with patch(
            "forest_change_framework.components.data_ingestion.hansen_forest_change.component.requests"
        ) as mock_requests:
            mock_requests.get.side_effect = Exception("Network error")

            framework.subscribe_event("hansen.error", event_collector.collect)

            output_folder = tmp_path / "output"
            component = framework.instantiate_component(
                "data_ingestion",
                "hansen_forest_change",
                {"data_folder": str(tmp_path), "output_folder": str(output_folder)},
            )

            bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}

            with pytest.raises(IOError):
                component.execute(bbox=bbox)

            assert event_collector.has_event("hansen.error")

    def test_bbox_validation(self, framework, tmp_path):
        """Test bbox validation in execute."""
        pytest.importorskip("requests")

        from unittest.mock import patch

        output_folder = tmp_path / "output"
        component = framework.instantiate_component(
            "data_ingestion",
            "hansen_forest_change",
            {"data_folder": str(tmp_path), "output_folder": str(output_folder)},
        )

        # Invalid bbox (minx > maxx)
        with patch(
            "forest_change_framework.components.data_ingestion.hansen_forest_change.component.requests"
        ):
            with pytest.raises(ValueError):
                component.execute(bbox={"minx": 100, "miny": 0, "maxx": 50, "maxy": 20})
