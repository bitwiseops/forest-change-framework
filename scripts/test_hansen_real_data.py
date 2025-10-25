#!/usr/bin/env python
"""
Real-world test of Hansen forest change component.

Downloads actual data from Google Storage and tests the mosaic creation.
Starts with a small area (1-2 tiles) for quick testing.
"""

import logging
from pathlib import Path
from forest_change_framework import BaseFramework

# Import components to trigger registration
from forest_change_framework.components.data_ingestion.hansen_forest_change import HansenForestChangeComponent

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_hansen_real_data():
    """Test Hansen component with real data from Google Storage."""

    print("=" * 80)
    print("HANSEN FOREST CHANGE COMPONENT - REAL DATA TEST")
    print("=" * 80)

    # Initialize framework
    print("\n1. Initializing framework...")
    framework = BaseFramework()

    # Create data folder
    data_folder = Path("/tmp/hansen_test_data")
    data_folder.mkdir(parents=True, exist_ok=True)
    print(f"   Data folder: {data_folder}")

    # Instantiate component
    print("\n2. Instantiating Hansen component...")
    component = framework.instantiate_component(
        "data_ingestion",
        "hansen_forest_change",
        {"data_folder": str(data_folder), "timeout": 60}
    )
    print(f"   Component: {component.name} v{component.version}")

    # Define small bounding box (1-2 tiles)
    # Using area around equator and prime meridian (00N_000E, 10N_000E)
    bbox = {"minx": 0, "miny": 0, "maxx": 10, "maxy": 20}
    print(f"\n3. Testing with small bbox: {bbox}")
    print(f"   This should download 2 tiles: 00N_000E, 10N_000E")

    try:
        # Execute component
        print("\n4. Downloading and processing tiles...")
        mosaic, metadata = component.execute(bbox=bbox)

        if mosaic is None:
            print("   ERROR: Mosaic creation failed!")
            return False

        # Check mosaic properties
        print("\n5. MOSAIC PROPERTIES:")
        print(f"   - Shape: {mosaic.height} x {mosaic.width} pixels")
        print(f"   - Bands: {mosaic.count}")
        print(f"   - Data type: {mosaic.dtypes}")
        print(f"   - CRS: {mosaic.crs}")
        print(f"   - Bounds: {mosaic.bounds}")
        print(f"   - Resolution: {mosaic.res}")
        print(f"   - Transform: {mosaic.transform}")

        # Verify band count
        if mosaic.count != 3:
            print(f"   ERROR: Expected 3 bands, got {mosaic.count}")
            return False

        # Read and check band data
        print("\n6. BAND DATA STATISTICS:")
        for band_idx in range(1, 4):
            band_data = mosaic.read(band_idx)
            print(f"   Band {band_idx}:")
            print(f"     - Min: {band_data.min()}")
            print(f"     - Max: {band_data.max()}")
            print(f"     - Mean: {band_data.mean():.2f}")
            print(f"     - Dtype: {band_data.dtype}")

        # Check metadata
        print("\n7. METADATA:")
        print(f"   - Version: {metadata['version']}")
        print(f"   - Bbox requested: {metadata['bbox']}")
        print(f"   - Tiles requested: {metadata['tiles_requested']}")
        print(f"   - Tiles downloaded: {metadata['tiles_downloaded']}")
        print(f"   - Tiles failed: {metadata['tiles_failed']}")
        print(f"   - Data folder: {metadata['data_folder']}")

        # Check band info
        print(f"\n8. BAND INFORMATION:")
        if 'band_info' in metadata:
            for band_key, band_info in metadata['band_info'].items():
                print(f"   {band_key}: {band_info['name']}")
                print(f"      -> {band_info['description']}")
        else:
            print("   ERROR: band_info not in metadata!")
            return False

        # Check downloaded files
        print(f"\n9. DOWNLOADED FILES:")
        downloaded_count = 0
        for tile_id in metadata['tiles_downloaded']:
            tile_path = data_folder / tile_id
            if tile_path.exists():
                files = list(tile_path.glob("*.tif"))
                print(f"   {tile_id}: {len(files)} files")
                for f in files:
                    print(f"      - {f.name}")
                downloaded_count += len(files)
            else:
                print(f"   {tile_id}: NOT FOUND")

        print(f"\n   Total downloaded: {downloaded_count} files")

        # Summary
        print("\n" + "=" * 80)
        print("✅ TEST SUCCESSFUL!")
        print("=" * 80)
        print(f"\nMosaic Summary:")
        print(f"  - Resolution: {mosaic.height}h x {mosaic.width}w pixels")
        print(f"  - Bands: 3 (treecover2000, lossyear, datamask)")
        print(f"  - Tiles mosaicked: {len(metadata['tiles_downloaded'])}")
        print(f"  - Data folder: {metadata['data_folder']}")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hansen_real_data()
    exit(0 if success else 1)
