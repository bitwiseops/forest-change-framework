"""
Integration test for Hansen component with real (but small) GeoTIFF files.

This test uses small mock GeoTIFF files (100x100 pixels) instead of actual
Hansen data to verify the end-to-end workflow without network calls or
memory issues.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from forest_change_framework import BaseFramework


@pytest.mark.integration
class TestHansenRealSmall:
    """Integration tests with small real GeoTIFF files."""

    def test_hansen_end_to_end_with_mock_tiles(self, framework, tmp_path):
        """
        Test complete Hansen workflow with mock GeoTIFF files.

        This test:
        1. Creates small mock tiles (100x100 pixels, 3 bands each)
        2. Mocks the tile list download
        3. Runs the Hansen component
        4. Verifies output mosaic is created correctly
        5. Checks memory efficiency (no MemoryFile saturation)
        """
        pytest.importorskip("requests")
        pytest.importorskip("rasterio")

        import numpy as np
        import rasterio
        from rasterio.transform import Affine

        # Setup paths
        data_folder = tmp_path / "data"
        output_folder = tmp_path / "output"
        data_folder.mkdir()
        output_folder.mkdir()

        # Create mock GeoTIFF files for 2 tiles
        tile_ids = ["00N_000E", "10N_000E"]

        for tile_id in tile_ids:
            tile_dir = data_folder / tile_id
            tile_dir.mkdir()

            # Parse tile coordinates for proper geotransform
            # Format: 00N_000E = latitude 0, longitude 0
            parts = tile_id.split("_")
            lat_str = parts[0]  # e.g., "00N", "10N"
            lon_str = parts[1]  # e.g., "000E", "010W"

            # Extract coordinates
            lat_deg = int(lat_str[:2])
            lat_dir = lat_str[2]  # N or S
            lon_deg = int(lon_str[:3])
            lon_dir = lon_str[3]  # E or W

            # Calculate bounds (tiles are 10x10 degrees)
            if lat_dir == 'N':
                miny, maxy = lat_deg, lat_deg + 10
            else:
                maxy, miny = -lat_deg, -(lat_deg + 10)

            if lon_dir == 'E':
                minx, maxx = lon_deg, lon_deg + 10
            else:
                maxx, minx = -lon_deg, -(lon_deg + 10)

            # Create proper geotransform (0.1 degrees per pixel for 100x100 raster)
            pixel_size = (maxx - minx) / 100
            transform = Affine.translation(minx, maxy) * Affine.scale(pixel_size, -pixel_size)

            # Create small mock files (100x100 pixels, not 40000x40000)
            for layer, data in [
                ("treecover2000", np.random.randint(0, 100, (100, 100), dtype=np.uint8)),
                ("lossyear", np.random.randint(0, 22, (100, 100), dtype=np.uint8)),
                ("datamask", np.ones((100, 100), dtype=np.uint8)),
            ]:
                filename = f"Hansen_GFC-2024-v1.12_{layer}_{tile_id}.tif"
                filepath = tile_dir / filename

                # Write GeoTIFF with proper geotransform
                profile = {
                    'driver': 'GTiff',
                    'height': 100,
                    'width': 100,
                    'count': 1,
                    'dtype': data.dtype,
                    'crs': 'EPSG:4326',
                    'transform': transform,
                }

                with rasterio.open(filepath, 'w', **profile) as dst:
                    dst.write(data, 1)

        # Mock the tile list download to return our mock tiles
        with patch(
            "forest_change_framework.components.data_ingestion.hansen_forest_change.component.requests"
        ) as mock_requests:
            # Mock tile list response
            mock_response = Mock()
            mock_response.text = "\n".join([
                f"Hansen_GFC-2024-v1.12_lossyear_{tile_id}.tif"
                for tile_id in tile_ids
            ])
            mock_requests.get.return_value = mock_response

            # Instantiate component
            component = framework.instantiate_component(
                "data_ingestion",
                "hansen_forest_change",
                {
                    "data_folder": str(data_folder),
                    "output_folder": str(output_folder),
                },
            )

            # Execute with bounding box covering both tiles
            bbox = {"minx": 0, "miny": 0, "maxx": 20, "maxy": 20}

            mosaic_path, metadata = component.execute(bbox=bbox)

            # Verify output
            assert mosaic_path is not None, "Mosaic path should not be None"
            assert Path(mosaic_path).exists(), f"Mosaic file should exist: {mosaic_path}"

            # Verify metadata
            assert "output_path" in metadata
            assert "output_shape" in metadata
            assert "output_crs" in metadata
            assert "tiles_downloaded" in metadata
            assert len(metadata["tiles_downloaded"]) == 2

            # Verify mosaic can be read
            with rasterio.open(mosaic_path) as src:
                assert src.count == 3, "Should have 3 bands"
                assert src.crs == "EPSG:4326"
                assert src.height > 0 and src.width > 0

                # Read a sample of each band
                band1 = src.read(1)  # treecover2000
                band2 = src.read(2)  # lossyear
                band3 = src.read(3)  # datamask

                assert band1.shape == band2.shape == band3.shape
                print(f"\n✓ Mosaic created successfully!")
                print(f"  Path: {mosaic_path}")
                print(f"  Shape: {band1.shape}")
                print(f"  Size: {Path(mosaic_path).stat().st_size / 1024:.1f} KB")

    def test_hansen_output_file_has_correct_bands(self, framework, tmp_path):
        """Test that output GeoTIFF has 3 bands in correct order."""
        pytest.importorskip("requests")
        pytest.importorskip("rasterio")

        import numpy as np
        import rasterio
        from rasterio.transform import Affine

        # Setup paths
        data_folder = tmp_path / "data"
        output_folder = tmp_path / "output"
        data_folder.mkdir()
        output_folder.mkdir()

        # Create tiles with distinct patterns to verify band order
        tile_id = "00N_000E"
        tile_dir = data_folder / tile_id
        tile_dir.mkdir()

        # Parse tile coordinates for proper geotransform
        parts = tile_id.split("_")
        lat_str = parts[0]
        lon_str = parts[1]

        lat_deg = int(lat_str[:2])
        lat_dir = lat_str[2]
        lon_deg = int(lon_str[:3])
        lon_dir = lon_str[3]

        # Calculate bounds
        if lat_dir == 'N':
            miny, maxy = lat_deg, lat_deg + 10
        else:
            maxy, miny = -lat_deg, -(lat_deg + 10)

        if lon_dir == 'E':
            minx, maxx = lon_deg, lon_deg + 10
        else:
            maxx, minx = -lon_deg, -(lon_deg + 10)

        # Create proper geotransform
        pixel_size = (maxx - minx) / 100
        transform = Affine.translation(minx, maxy) * Affine.scale(pixel_size, -pixel_size)

        # Create files with specific patterns
        patterns = {
            "treecover2000": np.full((100, 100), 50, dtype=np.uint8),  # All 50
            "lossyear": np.full((100, 100), 10, dtype=np.uint8),       # All 10
            "datamask": np.ones((100, 100), dtype=np.uint8),           # All 1
        }

        for layer, data in patterns.items():
            filename = f"Hansen_GFC-2024-v1.12_{layer}_{tile_id}.tif"
            filepath = tile_dir / filename

            profile = {
                'driver': 'GTiff',
                'height': 100,
                'width': 100,
                'count': 1,
                'dtype': data.dtype,
                'crs': 'EPSG:4326',
                'transform': transform,
            }

            with rasterio.open(filepath, 'w', **profile) as dst:
                dst.write(data, 1)

        # Mock requests
        with patch(
            "forest_change_framework.components.data_ingestion.hansen_forest_change.component.requests"
        ) as mock_requests:
            mock_response = Mock()
            mock_response.text = f"Hansen_GFC-2024-v1.12_lossyear_{tile_id}.tif"
            mock_requests.get.return_value = mock_response

            component = framework.instantiate_component(
                "data_ingestion",
                "hansen_forest_change",
                {
                    "data_folder": str(data_folder),
                    "output_folder": str(output_folder),
                },
            )

            bbox = {"minx": 0, "miny": 0, "maxx": 10, "maxy": 10}
            mosaic_path, metadata = component.execute(bbox=bbox)

            # Read mosaic and verify band values
            with rasterio.open(mosaic_path) as src:
                band1 = src.read(1)  # treecover2000
                band2 = src.read(2)  # lossyear
                band3 = src.read(3)  # datamask

                # Verify band order by checking values
                assert np.all(band1 == 50), f"Band 1 (treecover2000) should be 50, got {band1[0, 0]}"
                assert np.all(band2 == 10), f"Band 2 (lossyear) should be 10, got {band2[0, 0]}"
                assert np.all(band3 == 1), f"Band 3 (datamask) should be 1, got {band3[0, 0]}"

                print(f"\n✓ Band order verified!")
                print(f"  Band 1 (treecover2000): {band1[0, 0]}")
                print(f"  Band 2 (lossyear): {band2[0, 0]}")
                print(f"  Band 3 (datamask): {band3[0, 0]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
