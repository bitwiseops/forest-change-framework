"""Spatial tile-based splitting for train/val/test datasets."""

import logging
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SpatialTile:
    """Represents a geographic tile."""

    tile_id: str
    minx: float
    miny: float
    maxx: float
    maxy: float
    samples: List[str]

    def contains_bbox(self, bbox: List[float]) -> bool:
        """
        Check if tile contains bbox center or overlaps significantly.

        Args:
            bbox: [minx, miny, maxx, maxy]

        Returns:
            True if tile contains bbox center
        """
        bbox_center_x = (bbox[0] + bbox[2]) / 2
        bbox_center_y = (bbox[1] + bbox[3]) / 2
        return (
            self.minx <= bbox_center_x <= self.maxx
            and self.miny <= bbox_center_y <= self.maxy
        )

    def get_split(self, train_pct: float, val_pct: float) -> str:
        """
        Determine split (train/val/test) based on tile coordinates.

        Uses tile coordinates to deterministically assign split.
        This ensures consistency across runs.

        Args:
            train_pct: Training percentage (0-100)
            val_pct: Validation percentage (0-100)

        Returns:
            "train", "val", or "test"
        """
        # Use tile coordinates to generate deterministic hash
        hash_val = hash((round(self.minx, 1), round(self.miny, 1))) % 100

        if hash_val < train_pct:
            return "train"
        elif hash_val < train_pct + val_pct:
            return "val"
        else:
            return "test"


class SpatialTileGrid:
    """Generate and manage spatial tiles for dataset splitting."""

    def __init__(self, tile_size_deg: float):
        """
        Initialize tile grid.

        Args:
            tile_size_deg: Size of each tile in degrees (e.g., 1.0 for 1°×1°)
        """
        if tile_size_deg <= 0:
            raise ValueError("tile_size_deg must be positive")

        self.tile_size_deg = tile_size_deg
        self.tiles: Dict[str, SpatialTile] = {}

    def _get_tile_id(self, x: float, y: float) -> str:
        """
        Get tile ID for a coordinate.

        Args:
            x: Longitude
            y: Latitude

        Returns:
            Tile ID string
        """
        tile_x = int(x // self.tile_size_deg)
        tile_y = int(y // self.tile_size_deg)
        return f"tile_{tile_x}_{tile_y}"

    def add_sample(self, sample_id: str, bbox: List[float]) -> str:
        """
        Add sample to appropriate tile.

        Args:
            sample_id: Sample identifier
            bbox: [minx, miny, maxx, maxy]

        Returns:
            Tile ID where sample was placed
        """
        # Use center of bbox to determine tile
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2

        tile_id = self._get_tile_id(center_x, center_y)

        # Create tile if it doesn't exist
        if tile_id not in self.tiles:
            tile_x = int(center_x // self.tile_size_deg)
            tile_y = int(center_y // self.tile_size_deg)

            self.tiles[tile_id] = SpatialTile(
                tile_id=tile_id,
                minx=tile_x * self.tile_size_deg,
                miny=tile_y * self.tile_size_deg,
                maxx=(tile_x + 1) * self.tile_size_deg,
                maxy=(tile_y + 1) * self.tile_size_deg,
                samples=[],
            )

        self.tiles[tile_id].samples.append(sample_id)
        return tile_id

    def generate_splits(
        self,
        samples: Dict[str, Dict],
        train_percentage: float,
        val_percentage: float,
        test_percentage: float,
    ) -> Dict[str, str]:
        """
        Assign all samples to train/val/test splits based on spatial tiles.

        Args:
            samples: Dict mapping sample_id to {bbox, year, ...}
            train_percentage: Training percentage (0-100)
            val_percentage: Validation percentage (0-100)
            test_percentage: Test percentage (0-100)

        Returns:
            Dict mapping sample_id to split ("train", "val", "test")

        Raises:
            ValueError: If percentages don't sum to 100
        """
        total = train_percentage + val_percentage + test_percentage
        if abs(total - 100.0) > 0.1:
            raise ValueError(
                f"Percentages must sum to 100 (got {total})"
            )

        # Add all samples to tiles
        for sample_id, sample_data in samples.items():
            self.add_sample(sample_id, sample_data["bbox"])

        # Assign splits to tiles
        splits = {}
        for tile_id, tile in self.tiles.items():
            tile_split = tile.get_split(train_percentage, val_percentage)
            for sample_id in tile.samples:
                splits[sample_id] = tile_split

        return splits

    def get_tile_assignments(self) -> Dict[str, List[str]]:
        """
        Get mapping of tiles to samples.

        Returns:
            Dict mapping tile_id to list of sample_ids
        """
        assignments = {}
        for tile_id, tile in self.tiles.items():
            assignments[tile_id] = tile.samples
        return assignments

    def get_statistics(self) -> Dict:
        """
        Get statistics about tile coverage.

        Returns:
            Dict with tile count, samples per tile, etc.
        """
        sample_counts = [len(tile.samples) for tile in self.tiles.values()]

        return {
            "total_tiles": len(self.tiles),
            "total_samples": sum(sample_counts),
            "samples_per_tile_min": min(sample_counts) if sample_counts else 0,
            "samples_per_tile_max": max(sample_counts) if sample_counts else 0,
            "samples_per_tile_avg": (
                sum(sample_counts) / len(sample_counts)
                if sample_counts
                else 0
            ),
        }


class SplitValidator:
    """Validate split assignments."""

    @staticmethod
    def validate_splits(
        splits: Dict[str, str],
        samples: Dict[str, Dict],
        train_pct: float,
        val_pct: float,
        test_pct: float,
    ) -> Dict:
        """
        Validate split assignments match target percentages.

        Args:
            splits: Dict mapping sample_id to split
            samples: Original samples dict
            train_pct: Target training percentage
            val_pct: Target validation percentage
            test_pct: Target test percentage

        Returns:
            Validation report dict
        """
        total = len(splits)
        if total == 0:
            return {
                "valid": False,
                "error": "No samples in splits",
            }

        # Count samples per split
        split_counts = {"train": 0, "val": 0, "test": 0}
        for split in splits.values():
            if split in split_counts:
                split_counts[split] += 1

        # Calculate actual percentages
        actual_train = (split_counts["train"] / total) * 100
        actual_val = (split_counts["val"] / total) * 100
        actual_test = (split_counts["test"] / total) * 100

        # Allow 5% tolerance
        tolerance = 5.0

        is_valid = (
            abs(actual_train - train_pct) <= tolerance
            and abs(actual_val - val_pct) <= tolerance
            and abs(actual_test - test_pct) <= tolerance
        )

        report = {
            "valid": is_valid,
            "total_samples": total,
            "split_counts": split_counts,
            "target_percentages": {
                "train": train_pct,
                "val": val_pct,
                "test": test_pct,
            },
            "actual_percentages": {
                "train": round(actual_train, 2),
                "val": round(actual_val, 2),
                "test": round(actual_test, 2),
            },
        }

        if not is_valid:
            report["warning"] = (
                f"Split percentages outside tolerance. "
                f"Target: {train_pct}% / {val_pct}% / {test_pct}%, "
                f"Actual: {actual_train:.1f}% / {actual_val:.1f}% / {actual_test:.1f}%"
            )

        return report
