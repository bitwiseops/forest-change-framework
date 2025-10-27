"""Unit tests for AOI Sampler component."""

import pytest
import numpy as np
from pathlib import Path

from forest_change_framework.components.analysis.aoi_sampler.grid_utils import (
    create_grid_cells,
    cell_to_polygon,
    degrees_to_km,
    km_to_degrees,
    cells_to_geojson_features,
    create_geojson,
)
from forest_change_framework.components.analysis.aoi_sampler.statistics import (
    calculate_validity,
    calculate_loss_percentage,
    calculate_loss_by_year,
    calculate_treecover_stats,
    calculate_cell_statistics,
    aggregate_statistics,
)
from forest_change_framework.components.analysis.aoi_sampler.binning import (
    validate_bins_config,
    get_bin_for_value,
    bin_aois,
    filter_by_validity,
    get_bin_summary,
    apply_binning_and_filtering,
)
from forest_change_framework.core import get_registry


# ============================================================================
# Grid Utilities Tests
# ============================================================================


class TestGridUtils:
    """Tests for grid_utils module."""

    def test_degrees_to_km_latitude(self):
        """Test latitude conversion (latitude is constant: 111.32 km/degree)."""
        result = degrees_to_km(1.0, latitude=None)
        assert abs(result - 111.32) < 0.01

        result = degrees_to_km(10.0, latitude=None)
        assert abs(result - 1113.2) < 1.0

    def test_km_to_degrees_latitude(self):
        """Test inverse: kilometers to degrees (latitude)."""
        result = km_to_degrees(111.32, latitude=None)
        assert abs(result - 1.0) < 0.01

    def test_degrees_to_km_longitude(self):
        """Test longitude conversion varies with latitude."""
        # At equator (lat=0): cos(0) = 1, so same as latitude
        result = degrees_to_km(1.0, latitude=0.0)
        assert abs(result - 111.32) < 0.01

        # At 60° latitude: cos(60°) = 0.5, so half the distance
        result = degrees_to_km(1.0, latitude=60.0)
        assert abs(result - 55.66) < 1.0

    def test_create_grid_cells_single_cell(self):
        """Test grid creation with bbox that creates single cell."""
        bbox = {"minx": 0, "miny": 0, "maxx": 0.5, "maxy": 0.5}
        cells, count = create_grid_cells(bbox, cell_size_km=100.0)

        assert count == 1
        assert len(cells) == 1
        assert cells[0]["minx"] == 0
        assert cells[0]["miny"] == 0
        assert cells[0]["maxx"] == 0.5
        assert cells[0]["maxy"] == 0.5

    def test_create_grid_cells_multiple_cells(self):
        """Test grid creation with multiple cells."""
        bbox = {"minx": 0, "miny": 0, "maxx": 2, "maxy": 2}
        cells, count = create_grid_cells(bbox, cell_size_km=60.0)

        # Should create roughly 4 cells (2x2 grid)
        assert count > 1
        assert len(cells) == count

    def test_create_grid_cells_cell_ids_unique(self):
        """Test that all cell IDs are unique."""
        bbox = {"minx": 0, "miny": 0, "maxx": 2, "maxy": 2}
        cells, count = create_grid_cells(bbox, cell_size_km=60.0)

        cell_ids = [c["cell_id"] for c in cells]
        assert len(set(cell_ids)) == len(cell_ids)  # All unique
        assert cell_ids == list(range(count))  # Sequential from 0

    def test_create_grid_cells_invalid_bbox(self):
        """Test error on invalid bbox."""
        with pytest.raises(ValueError):
            create_grid_cells({"minx": 10, "miny": 0, "maxx": 0, "maxy": 10})

    def test_create_grid_cells_missing_bbox_key(self):
        """Test error on missing bbox key."""
        with pytest.raises(ValueError):
            create_grid_cells({"minx": 0, "miny": 0, "maxx": 10})  # Missing maxy

    def test_create_grid_cells_invalid_cell_size(self):
        """Test error on invalid cell size."""
        bbox = {"minx": 0, "miny": 0, "maxx": 10, "maxy": 10}

        with pytest.raises(ValueError):
            create_grid_cells(bbox, cell_size_km=0)

        with pytest.raises(ValueError):
            create_grid_cells(bbox, cell_size_km=-1)

    def test_cell_to_polygon(self):
        """Test conversion of cell to GeoJSON polygon."""
        cell = {"minx": 0, "miny": 0, "maxx": 1, "maxy": 1}
        polygon = cell_to_polygon(cell)

        assert polygon["type"] == "Polygon"
        coords = polygon["coordinates"][0]

        # Check polygon has 5 points (4 corners + closed ring)
        assert len(coords) == 5

        # Check first and last are same (closed ring)
        assert coords[0] == coords[-1]

        # Check corners are correct
        assert [0, 0] in coords
        assert [1, 0] in coords
        assert [1, 1] in coords
        assert [0, 1] in coords

    def test_cells_to_geojson_features(self):
        """Test conversion of cells to GeoJSON features."""
        cells = [
            {
                "minx": 0,
                "miny": 0,
                "maxx": 1,
                "maxy": 1,
                "cell_id": 0,
                "loss_percentage": 15.5,
                "data_validity": 95.0,
            },
            {
                "minx": 1,
                "miny": 0,
                "maxx": 2,
                "maxy": 1,
                "cell_id": 1,
                "loss_percentage": 22.3,
                "data_validity": 88.0,
            },
        ]

        features = cells_to_geojson_features(cells)

        assert len(features) == 2
        assert features[0]["type"] == "Feature"
        assert features[0]["geometry"]["type"] == "Polygon"
        assert features[0]["properties"]["loss_percentage"] == 15.5

    def test_create_geojson(self):
        """Test creation of complete GeoJSON FeatureCollection."""
        cells = [
            {
                "minx": 0,
                "miny": 0,
                "maxx": 1,
                "maxy": 1,
                "cell_id": 0,
                "loss_percentage": 15.5,
            }
        ]

        geojson = create_geojson(cells, crs="EPSG:4326")

        assert geojson["type"] == "FeatureCollection"
        assert geojson["crs"]["properties"]["name"] == "EPSG:4326"
        assert len(geojson["features"]) == 1


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Tests for statistics module."""

    def test_calculate_validity_all_valid(self):
        """Test validity calculation with all valid pixels."""
        datamask = np.ones((100, 100), dtype=np.uint8)
        validity = calculate_validity(datamask)

        assert validity == 100.0

    def test_calculate_validity_all_invalid(self):
        """Test validity calculation with no valid pixels."""
        datamask = np.zeros((100, 100), dtype=np.uint8)
        validity = calculate_validity(datamask)

        assert validity == 0.0

    def test_calculate_validity_partial(self):
        """Test validity calculation with partial valid pixels."""
        datamask = np.zeros((100, 100), dtype=np.uint8)
        datamask[:50, :] = 1  # Half valid

        validity = calculate_validity(datamask)
        assert abs(validity - 50.0) < 0.1

    def test_calculate_validity_empty(self):
        """Test validity calculation with empty array."""
        datamask = np.array([], dtype=np.uint8).reshape(0, 0)
        validity = calculate_validity(datamask)

        assert validity == 0.0

    def test_calculate_loss_percentage_no_loss(self):
        """Test loss calculation with no loss pixels."""
        lossyear = np.zeros((100, 100), dtype=np.uint8)
        datamask = np.ones((100, 100), dtype=np.uint8)

        loss_pct = calculate_loss_percentage(lossyear, datamask)
        assert loss_pct == 0.0

    def test_calculate_loss_percentage_all_loss(self):
        """Test loss calculation with all loss pixels."""
        lossyear = np.ones((100, 100), dtype=np.uint8) * 5  # Loss year 5
        datamask = np.ones((100, 100), dtype=np.uint8)

        loss_pct = calculate_loss_percentage(lossyear, datamask)
        assert loss_pct == 100.0

    def test_calculate_loss_percentage_partial(self):
        """Test loss calculation with partial loss."""
        lossyear = np.zeros((100, 100), dtype=np.uint8)
        lossyear[:25, :] = 5  # Top 25% has loss

        datamask = np.ones((100, 100), dtype=np.uint8)

        loss_pct = calculate_loss_percentage(lossyear, datamask)
        assert abs(loss_pct - 25.0) < 0.1

    def test_calculate_loss_percentage_with_invalid(self):
        """Test loss calculation ignores invalid pixels."""
        lossyear = np.ones((100, 100), dtype=np.uint8) * 5
        datamask = np.zeros((100, 100), dtype=np.uint8)
        datamask[:50, :] = 1  # Only top half valid

        loss_pct = calculate_loss_percentage(lossyear, datamask)

        # All loss pixels are in valid area, so 100%
        assert abs(loss_pct - 100.0) < 0.1

    def test_calculate_loss_by_year(self):
        """Test loss breakdown by year."""
        lossyear = np.zeros((100, 100), dtype=np.uint8)
        lossyear[:25, :] = 1  # 25% loss in year 2001 (offset 1 = 2000+1)
        lossyear[25:50, :] = 2  # 25% loss in year 2002 (offset 2 = 2000+2)

        datamask = np.ones((100, 100), dtype=np.uint8)

        loss_by_year = calculate_loss_by_year(lossyear, datamask)

        assert 2001 in loss_by_year
        assert 2002 in loss_by_year
        assert abs(loss_by_year[2001] - 25.0) < 0.1
        assert abs(loss_by_year[2002] - 25.0) < 0.1

    def test_calculate_treecover_stats(self):
        """Test tree cover statistics calculation."""
        treecover = np.full((100, 100), 50, dtype=np.uint8)  # All 50%
        datamask = np.ones((100, 100), dtype=np.uint8)

        stats = calculate_treecover_stats(treecover, datamask)

        assert stats["mean"] == 50.0
        assert stats["median"] == 50.0
        assert stats["std"] == 0.0
        assert stats["min"] == 50
        assert stats["max"] == 50

    def test_calculate_cell_statistics(self):
        """Test comprehensive statistics calculation."""
        treecover = np.full((100, 100), 60, dtype=np.uint8)
        lossyear = np.zeros((100, 100), dtype=np.uint8)
        lossyear[:20, :] = 5  # 20% loss

        datamask = np.ones((100, 100), dtype=np.uint8)

        stats = calculate_cell_statistics(
            treecover, lossyear, datamask, include_treecover_stats=True
        )

        assert "loss_percentage" in stats
        assert "data_validity" in stats
        assert stats["loss_percentage"] == 20.0
        assert stats["data_validity"] == 100.0
        assert stats["treecover"]["mean"] == 60.0

    def test_aggregate_statistics(self):
        """Test aggregation of statistics from multiple cells."""
        all_stats = [
            {"loss_percentage": 10, "data_validity": 90},
            {"loss_percentage": 20, "data_validity": 85},
            {"loss_percentage": 30, "data_validity": 95},
        ]

        agg = aggregate_statistics(all_stats)

        assert agg["total_cells"] == 3
        assert abs(agg["mean_loss_percentage"] - 20.0) < 0.1
        assert agg["median_loss_percentage"] == 20.0
        assert abs(agg["mean_data_validity"] - 90.0) < 0.1


# ============================================================================
# Binning Tests
# ============================================================================


class TestBinning:
    """Tests for binning module."""

    def test_validate_bins_valid(self):
        """Test validation of valid bins configuration."""
        bins = [
            {"name": "low", "min": 0, "max": 15},
            {"name": "medium", "min": 15, "max": 30},
            {"name": "high", "min": 30, "max": 100},
        ]

        is_valid, msg = validate_bins_config(bins)
        assert is_valid
        assert msg == ""

    def test_validate_bins_overlap(self):
        """Test validation detects overlapping bins."""
        bins = [
            {"name": "low", "min": 0, "max": 20},
            {"name": "medium", "min": 15, "max": 30},  # Overlaps with low
        ]

        is_valid, msg = validate_bins_config(bins)
        assert not is_valid
        assert "overlap" in msg.lower()

    def test_validate_bins_invalid_range(self):
        """Test validation detects invalid min/max."""
        bins = [{"name": "bad", "min": 30, "max": 15}]  # min > max

        is_valid, msg = validate_bins_config(bins)
        assert not is_valid

    def test_validate_bins_empty(self):
        """Test validation detects empty bins."""
        is_valid, msg = validate_bins_config([])
        assert not is_valid

    def test_get_bin_for_value(self):
        """Test bin assignment for values."""
        bins = [
            {"name": "low", "min": 0, "max": 15},
            {"name": "medium", "min": 15, "max": 30},
            {"name": "high", "min": 30, "max": 100},
        ]

        assert get_bin_for_value(5, bins) == "low"
        assert get_bin_for_value(20, bins) == "medium"
        assert get_bin_for_value(50, bins) == "high"
        assert get_bin_for_value(100, bins) == "high"  # Boundary included
        assert get_bin_for_value(150, bins) is None  # Out of range

    def test_bin_aois(self):
        """Test binning of AOIs."""
        aois = [
            {"loss_percentage": 5},
            {"loss_percentage": 20},
            {"loss_percentage": 50},
        ]

        bins = [
            {"name": "low", "min": 0, "max": 15},
            {"name": "high", "min": 15, "max": 100},
        ]

        binned = bin_aois(aois, bins)

        assert binned[0]["bin_category"] == "low"
        assert binned[1]["bin_category"] == "high"
        assert binned[2]["bin_category"] == "high"

    def test_filter_by_validity(self):
        """Test filtering AOIs by validity threshold."""
        aois = [
            {"loss_percentage": 10, "data_validity": 90},
            {"loss_percentage": 20, "data_validity": 75},  # Below 80% threshold
            {"loss_percentage": 30, "data_validity": 95},
        ]

        valid, invalid = filter_by_validity(aois, validity_threshold=0.8)

        assert len(valid) == 2
        assert len(invalid) == 0

        valid, invalid = filter_by_validity(aois, validity_threshold=0.8, keep_invalid=True)

        assert len(valid) == 2
        assert len(invalid) == 1
        assert invalid[0]["data_validity"] == 75

    def test_get_bin_summary(self):
        """Test generation of bin summary."""
        aois = [
            {"bin_category": "low"},
            {"bin_category": "low"},
            {"bin_category": "high"},
        ]

        summary = get_bin_summary(aois)

        assert summary["low"] == 2
        assert summary["high"] == 1

    def test_apply_binning_and_filtering(self):
        """Test complete binning and filtering pipeline."""
        aois = [
            {"loss_percentage": 5, "data_validity": 95},
            {"loss_percentage": 20, "data_validity": 90},
            {"loss_percentage": 40, "data_validity": 75},  # Invalid
            {"loss_percentage": 60, "data_validity": 85},
        ]

        bins = [
            {"name": "low", "min": 0, "max": 15},
            {"name": "medium", "min": 15, "max": 50},
            {"name": "high", "min": 50, "max": 100},
        ]

        output_aois, summary = apply_binning_and_filtering(
            aois, bins, validity_threshold=0.8, keep_invalid_aois=False
        )

        assert summary["total_aois"] == 4
        assert summary["valid_aois"] == 3
        assert summary["invalid_aois"] == 0  # Empty when not keeping invalid
        assert summary["excluded_aois"] == 1  # But we know 1 was excluded
        assert summary["bin_summary"]["low"] == 1
        assert summary["bin_summary"]["medium"] == 1
        assert summary["bin_summary"]["high"] == 1


# ============================================================================
# Component Tests
# ============================================================================


class TestAoiSamplerComponent:
    """Tests for AOI Sampler component."""

    def test_component_registered(self, clean_registry):
        """Test that component is registered."""
        registry = clean_registry
        components = registry.list_components("analysis")

        assert components is not None

    def test_component_instantiation(self, framework):
        """Test component can be instantiated with required config."""
        config = {
            "grid_cell_size_km": 1.0,
            "min_validity_threshold": 80.0,
            "loss_bins": [
                {"name": "low", "min": 0, "max": 15},
                {"name": "high", "min": 15, "max": 100},
            ],
        }
        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=config
        )

        assert component is not None
        assert component.name == "aoi_sampler"
        assert component.version == "1.0.0"

    def test_component_initialize(self, framework):
        """Test component initialization with valid config."""
        config = {
            "grid_cell_size_km": 2.0,
            "min_validity_threshold": 75.0,
            "loss_bins": [
                {"name": "low", "min": 0, "max": 15},
                {"name": "high", "min": 15, "max": 100},
            ],
        }
        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=config
        )

        # Component should initialize without error
        assert component is not None

    def test_component_initialize_missing_bins(self, framework):
        """Test component initialization fails without loss_bins."""
        config = {
            "grid_cell_size_km": 2.0,
            "min_validity_threshold": 75.0,
            # Missing loss_bins
        }

        with pytest.raises(Exception):  # ComponentError or ValueError
            framework.instantiate_component(
                "analysis", "aoi_sampler", instance_config=config
            )

    def test_component_initialize_invalid_grid_size(self, framework):
        """Test component initialization fails with invalid grid size."""
        config = {
            "grid_cell_size_km": -1.0,  # Invalid
            "min_validity_threshold": 75.0,
            "loss_bins": [{"name": "low", "min": 0, "max": 100}],
        }

        with pytest.raises(Exception):  # ComponentError or ValueError
            framework.instantiate_component(
                "analysis", "aoi_sampler", instance_config=config
            )

    def test_component_cleanup(self, framework):
        """Test component cleanup."""
        config = {
            "grid_cell_size_km": 1.0,
            "min_validity_threshold": 80.0,
            "loss_bins": [{"name": "low", "min": 0, "max": 100}],
        }
        component = framework.instantiate_component(
            "analysis", "aoi_sampler", instance_config=config
        )

        component.cleanup()

        # Should not raise
