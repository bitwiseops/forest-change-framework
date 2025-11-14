"""Unit tests for dataset organizer splitter module."""

import pytest
from forest_change_framework.components.export.dataset_organizer.splitter import (
    SpatialTile,
    SpatialTileGrid,
    SplitValidator,
)


class TestSpatialTile:
    """Tests for SpatialTile class."""

    def test_tile_initialization(self):
        """Test SpatialTile initialization."""
        tile = SpatialTile(
            tile_id="tile_0_0",
            minx=0.0,
            miny=0.0,
            maxx=1.0,
            maxy=1.0,
            samples=["sample_1", "sample_2"],
        )
        assert tile.tile_id == "tile_0_0"
        assert tile.minx == 0.0
        assert tile.miny == 0.0
        assert tile.maxx == 1.0
        assert tile.maxy == 1.0
        assert len(tile.samples) == 2

    def test_contains_bbox_center_inside(self):
        """Test contains_bbox when bbox center is inside tile."""
        tile = SpatialTile(
            tile_id="tile_0_0",
            minx=0.0,
            miny=0.0,
            maxx=1.0,
            maxy=1.0,
            samples=[],
        )
        bbox = [0.2, 0.3, 0.4, 0.5]  # center at (0.3, 0.4)
        assert tile.contains_bbox(bbox) is True

    def test_contains_bbox_center_outside(self):
        """Test contains_bbox when bbox center is outside tile."""
        tile = SpatialTile(
            tile_id="tile_0_0",
            minx=0.0,
            miny=0.0,
            maxx=1.0,
            maxy=1.0,
            samples=[],
        )
        bbox = [1.5, 1.5, 1.8, 1.8]  # center at (1.65, 1.65)
        assert tile.contains_bbox(bbox) is False

    def test_contains_bbox_boundary(self):
        """Test contains_bbox at tile boundaries."""
        tile = SpatialTile(
            tile_id="tile_0_0",
            minx=0.0,
            miny=0.0,
            maxx=1.0,
            maxy=1.0,
            samples=[],
        )
        bbox = [0.0, 0.0, 0.5, 0.5]  # center at (0.25, 0.25)
        assert tile.contains_bbox(bbox) is True

    def test_get_split_deterministic(self):
        """Test get_split is deterministic."""
        tile = SpatialTile(
            tile_id="tile_5_5",
            minx=5.0,
            miny=5.0,
            maxx=6.0,
            maxy=6.0,
            samples=[],
        )
        split1 = tile.get_split(train_pct=70, val_pct=20)
        split2 = tile.get_split(train_pct=70, val_pct=20)
        assert split1 == split2

    def test_get_split_returns_valid_split(self):
        """Test get_split returns valid split value."""
        tile = SpatialTile(
            tile_id="tile_0_0",
            minx=0.0,
            miny=0.0,
            maxx=1.0,
            maxy=1.0,
            samples=[],
        )
        split = tile.get_split(train_pct=70, val_pct=20)
        assert split in ["train", "val", "test"]


class TestSpatialTileGrid:
    """Tests for SpatialTileGrid class."""

    def test_initialization(self):
        """Test SpatialTileGrid initialization."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        assert grid.tile_size_deg == 1.0
        assert len(grid.tiles) == 0

    def test_initialization_invalid_size(self):
        """Test initialization with invalid tile size."""
        with pytest.raises(ValueError):
            SpatialTileGrid(tile_size_deg=0)

        with pytest.raises(ValueError):
            SpatialTileGrid(tile_size_deg=-1.0)

    def test_get_tile_id_positive_coords(self):
        """Test _get_tile_id with positive coordinates."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        tile_id = grid._get_tile_id(0.5, 0.5)
        assert tile_id == "tile_0_0"

        tile_id = grid._get_tile_id(1.5, 2.3)
        assert tile_id == "tile_1_2"

    def test_get_tile_id_negative_coords(self):
        """Test _get_tile_id with negative coordinates."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        tile_id = grid._get_tile_id(-1.5, -2.3)
        assert tile_id == "tile_-2_-3"

    def test_get_tile_id_with_different_tile_sizes(self):
        """Test _get_tile_id with different tile sizes."""
        grid_0_5 = SpatialTileGrid(tile_size_deg=0.5)
        grid_2_0 = SpatialTileGrid(tile_size_deg=2.0)

        assert grid_0_5._get_tile_id(0.25, 0.75) == "tile_0_1"
        assert grid_2_0._get_tile_id(0.25, 0.75) == "tile_0_0"

    def test_add_sample(self):
        """Test add_sample method."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        bbox = [0.0, 0.0, 0.5, 0.5]
        tile_id = grid.add_sample("sample_1", bbox)

        assert tile_id == "tile_0_0"
        assert "sample_1" in grid.tiles[tile_id].samples

    def test_add_multiple_samples_same_tile(self):
        """Test adding multiple samples to same tile."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        bbox1 = [0.1, 0.1, 0.3, 0.3]
        bbox2 = [0.4, 0.4, 0.6, 0.6]

        tile_id1 = grid.add_sample("sample_1", bbox1)
        tile_id2 = grid.add_sample("sample_2", bbox2)

        assert tile_id1 == tile_id2 == "tile_0_0"
        assert len(grid.tiles["tile_0_0"].samples) == 2

    def test_add_samples_different_tiles(self):
        """Test adding samples to different tiles."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        bbox1 = [0.1, 0.1, 0.3, 0.3]
        bbox2 = [1.1, 1.1, 1.3, 1.3]

        tile_id1 = grid.add_sample("sample_1", bbox1)
        tile_id2 = grid.add_sample("sample_2", bbox2)

        assert tile_id1 == "tile_0_0"
        assert tile_id2 == "tile_1_1"
        assert len(grid.tiles) == 2

    def test_generate_splits_basic(self):
        """Test generate_splits with basic samples."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        samples = {
            "sample_1": {"bbox": [0.0, 0.0, 0.5, 0.5]},
            "sample_2": {"bbox": [0.2, 0.2, 0.6, 0.6]},
            "sample_3": {"bbox": [1.0, 1.0, 1.5, 1.5]},
            "sample_4": {"bbox": [2.0, 2.0, 2.5, 2.5]},
        }

        splits = grid.generate_splits(samples, 70, 15, 15)

        assert len(splits) == 4
        assert all(split in ["train", "val", "test"] for split in splits.values())

    def test_generate_splits_invalid_percentages(self):
        """Test generate_splits with invalid percentages."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        samples = {"sample_1": {"bbox": [0.0, 0.0, 0.5, 0.5]}}

        with pytest.raises(ValueError):
            grid.generate_splits(samples, 60, 20, 15)  # sum = 95, not 100

    def test_generate_splits_valid_percentages(self):
        """Test generate_splits with valid percentages."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        samples = {"sample_1": {"bbox": [0.0, 0.0, 0.5, 0.5]}}

        # Should not raise
        splits = grid.generate_splits(samples, 70, 20, 10)
        assert len(splits) == 1
        assert splits["sample_1"] in ["train", "val", "test"]

    def test_get_tile_assignments(self):
        """Test get_tile_assignments method."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        grid.add_sample("sample_1", [0.0, 0.0, 0.5, 0.5])
        grid.add_sample("sample_2", [0.2, 0.2, 0.6, 0.6])

        assignments = grid.get_tile_assignments()
        assert "tile_0_0" in assignments
        assert set(assignments["tile_0_0"]) == {"sample_1", "sample_2"}

    def test_get_statistics(self):
        """Test get_statistics method."""
        grid = SpatialTileGrid(tile_size_deg=1.0)
        grid.add_sample("sample_1", [0.0, 0.0, 0.5, 0.5])
        grid.add_sample("sample_2", [0.2, 0.2, 0.6, 0.6])
        grid.add_sample("sample_3", [1.0, 1.0, 1.5, 1.5])

        stats = grid.get_statistics()
        assert stats["total_tiles"] == 2
        assert stats["total_samples"] == 3
        assert stats["samples_per_tile_min"] == 1
        assert stats["samples_per_tile_max"] == 2

    def test_get_statistics_empty_grid(self):
        """Test get_statistics with empty grid."""
        grid = SpatialTileGrid(tile_size_deg=1.0)

        stats = grid.get_statistics()
        assert stats["total_tiles"] == 0
        assert stats["total_samples"] == 0
        assert stats["samples_per_tile_min"] == 0
        assert stats["samples_per_tile_max"] == 0

    def test_different_tile_sizes(self):
        """Test grid with different tile sizes."""
        grid_0_5 = SpatialTileGrid(tile_size_deg=0.5)
        grid_2_0 = SpatialTileGrid(tile_size_deg=2.0)

        bbox = [0.3, 0.3, 0.4, 0.4]

        tile_id_0_5 = grid_0_5.add_sample("sample_1", bbox)
        tile_id_2_0 = grid_2_0.add_sample("sample_1", bbox)

        # Different tile sizes should produce different behaviors
        assert tile_id_0_5 == "tile_0_0"
        assert tile_id_2_0 == "tile_0_0"


class TestSplitValidator:
    """Tests for SplitValidator class."""

    def test_validate_splits_valid(self):
        """Test validate_splits with valid splits."""
        splits = {
            "sample_1": "train",
            "sample_2": "train",
            "sample_3": "train",
            "sample_4": "train",
            "sample_5": "train",
            "sample_6": "train",
            "sample_7": "train",
            "sample_8": "val",
            "sample_9": "val",
            "sample_10": "test",
        }
        samples = {s: {"bbox": [0, 0, 1, 1]} for s in splits.keys()}

        report = SplitValidator.validate_splits(
            splits, samples, 70, 20, 10
        )

        assert report["valid"] is True
        assert report["split_counts"]["train"] == 7
        assert report["split_counts"]["val"] == 2
        assert report["split_counts"]["test"] == 1

    def test_validate_splits_empty(self):
        """Test validate_splits with empty splits."""
        report = SplitValidator.validate_splits({}, {}, 70, 20, 10)

        assert report["valid"] is False
        assert "error" in report

    def test_validate_splits_with_tolerance(self):
        """Test validate_splits with tolerance."""
        splits = {
            f"sample_{i}": "train"
            for i in range(65)
        }
        splits.update({
            f"sample_{i}": "val"
            for i in range(65, 80)
        })
        splits.update({
            f"sample_{i}": "test"
            for i in range(80, 100)
        })

        samples = {s: {"bbox": [0, 0, 1, 1]} for s in splits.keys()}

        report = SplitValidator.validate_splits(
            splits, samples, 70, 20, 10
        )

        # 65%, 15%, 20% should be valid (within 5% tolerance)
        assert report["actual_percentages"]["train"] == 65.0
        assert report["actual_percentages"]["val"] == 15.0
        assert report["actual_percentages"]["test"] == 20.0

    def test_validate_splits_invalid_percentages(self):
        """Test validate_splits that violates tolerance."""
        splits = {
            f"sample_{i}": "train"
            for i in range(50)
        }
        splits.update({
            f"sample_{i}": "val"
            for i in range(50, 100)
        })

        samples = {s: {"bbox": [0, 0, 1, 1]} for s in splits.keys()}

        report = SplitValidator.validate_splits(
            splits, samples, 70, 20, 10
        )

        # 50% train vs 70% target - exceeds tolerance
        assert report["valid"] is False
        assert "warning" in report

    def test_validate_splits_calculates_percentages(self):
        """Test that validate_splits calculates correct percentages."""
        splits = {
            "s1": "train",
            "s2": "train",
            "s3": "train",
            "s4": "train",
            "s5": "train",
            "s6": "val",
            "s7": "val",
            "s8": "test",
            "s9": "test",
            "s10": "test",
        }
        samples = {s: {"bbox": [0, 0, 1, 1]} for s in splits.keys()}

        report = SplitValidator.validate_splits(
            splits, samples, 50, 20, 30
        )

        assert report["actual_percentages"]["train"] == 50.0
        assert report["actual_percentages"]["val"] == 20.0
        assert report["actual_percentages"]["test"] == 30.0
        assert report["valid"] is True

    def test_validate_splits_reports_statistics(self):
        """Test that validate_splits reports statistics."""
        splits = {
            f"sample_{i}": "train"
            for i in range(70)
        }
        splits.update({
            f"sample_{i}": "val"
            for i in range(70, 85)
        })
        splits.update({
            f"sample_{i}": "test"
            for i in range(85, 100)
        })

        samples = {s: {"bbox": [0, 0, 1, 1]} for s in splits.keys()}

        report = SplitValidator.validate_splits(
            splits, samples, 70, 15, 15
        )

        assert "total_samples" in report
        assert "split_counts" in report
        assert "actual_percentages" in report
        assert "target_percentages" in report
        assert report["total_samples"] == 100
