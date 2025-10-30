# Implementation Plan: ML Training Dataset Generator

**Status**: Planning Phase
**Created**: 2025-10-28
**Last Updated**: 2025-10-28

---

## Project Overview

Create two new components to generate ML training datasets from forest change detection samples:

1. **imagery_downloader** (visualization category) - Downloads Sentinel-2 pre/post imagery from Google Earth Engine
2. **dataset_organizer** (export category) - Organizes imagery into train/val/test splits with (pre, post, label) triplets

---

## Requirements & Decisions

### Imagery Source
- **Selected**: Sentinel-2 (ESA Copernicus, 10m resolution)
- **Rationale**: Good availability, public access via Google Earth Engine

### Output Formats
- **Selected**: Both GeoTIFF (for metadata) and PNG/JPG (for ML training)
- **GeoTIFF**: Preserves geospatial metadata, projection info
- **PNG**: Smaller file size, standard for DL frameworks

### Data Split Strategy
- **Selected**: Spatial tiles (avoid data leakage)
- **Method**: Divide geographic space into tiles, assign tiles to train/val/test
- **Prevents**: Spatially adjacent samples appearing in different sets

### Label Definition
- **Selected**: Original TIFF patch from sample_extractor
- **Content**: The extracted GeoTIFF with ground truth forest loss data
- **Purpose**: Direct ground truth for supervised learning

### Cloud Cover Threshold
- **Selected**: <30% (configurable)
- **Flexibility**: User can adjust in config if needed

### Missing Imagery Handling
- **Selected**: Expand search dates automatically
- **Strategy**: If no imagery within ±30 days, try ±60 days, then ±90 days
- **Max Range**: 90 days before/after target date

### Component Structure
- **Selected**: Two separate components
- **imagery_downloader**: Pure data acquisition
- **dataset_organizer**: Pure data organization
- **Benefit**: Modularity, can run independently

---

## Implementation Details

### Component 1: imagery_downloader

**Category**: visualization
**Name**: imagery_downloader
**Version**: 1.0.0

#### Location
```
src/forest_change_framework/components/visualization/imagery_downloader/
├── __init__.py
├── component.py
├── gee_utils.py
├── sentinel2.py
├── image_processor.py
└── config_schema.py
```

#### Configuration
```python
imagery_downloader:
  # Input/Output paths
  aoi_geojson: str (path to sample_extractor output)

  # Sentinel-2 parameters
  cloud_cover_threshold: int [0-100], default 30
  initial_date_range: int (days), default 30
  max_date_range: int (days), default 90
  reproject_to_crs: str, default "EPSG:4326"
  bands: list, default ["B4", "B3", "B2"]

  # Output control
  output_format: list, options ["geotiff", "png"], default ["geotiff", "png"]
```

#### Workflow
1. Read GeoTIFF metadata: bbox (minx, miny, maxx, maxy) and year
2. Calculate target dates:
   - **Pre**: Jan 1st ± initial_date_range days of loss year
   - **Post**: Jan 1st ± initial_date_range days of year+1
3. Query Google Earth Engine for Sentinel-2 scenes:
   - Cloud cover < threshold
   - Overlaps bbox
   - Within date range
4. If no scenes found, expand date_range and retry (up to max_date_range)
5. Download scene(s) with lowest cloud cover
6. Reproject to specified CRS
7. Clip to bbox
8. Save as GeoTIFF
9. Generate PNG/JPG at standard size (e.g., 256×256, 512×512)
10. Store in organized directory structure
11. Publish progress events

#### Output Structure
```
output/imagery_downloader/
├── sample_000001/
│   ├── pre.tif
│   ├── pre.png
│   ├── post.tif
│   ├── post.png
│   └── metadata.json
├── sample_000002/
│   └── ...
└── download_log.csv
```

#### Key Implementation Files

**component.py**: ~300 lines
- BaseComponent subclass
- @register_component decorator
- initialize() → setup GEE authentication, config validation
- execute() → main workflow above
- cleanup() → close GEE session

**gee_utils.py**: ~200 lines
- GEE connection management
- Scene filtering logic
- Date range expansion algorithm
- Sentinel-2 band mapping

**sentinel2.py**: ~150 lines
- Sentinel-2 specific queries
- Cloud cover calculation
- Band info and defaults

**image_processor.py**: ~200 lines
- Download handling
- Reprojection (rasterio)
- PNG generation (PIL/matplotlib)
- Metadata JSON creation

#### Dependencies
- `earthengine-api` (Google Earth Engine)
- `rasterio` (already in project)
- `numpy` (already in project)
- `PIL` or `matplotlib` (for PNG generation)

#### Special Notes
- User must authenticate first: `earthengine authenticate`
- GEE has usage limits (free tier: ~40 API calls/second)
- Large areas may take time (show progress events)

---

### Component 2: dataset_organizer

**Category**: export
**Name**: dataset_organizer
**Version**: 1.0.0

#### Location
```
src/forest_change_framework/components/export/dataset_organizer/
├── __init__.py
├── component.py
├── splitter.py
├── organizer.py
├── metadata_generator.py
└── config_schema.py
```

#### Configuration
```python
dataset_organizer:
  # Input paths
  imagery_directory: str (path to imagery_downloader output)
  sample_patches_directory: str (path to sample_extractor output)

  # Split percentages
  train_percentage: float, default 70.0
  val_percentage: float, default 15.0
  test_percentage: float, default 15.0

  # Spatial split parameters
  spatial_tile_size_deg: float, default 1.0  # degrees (e.g., 1°×1°)

  # Output control
  image_format: str, choices ["png", "geotiff", "both"], default "png"
  create_metadata_csv: bool, default True
```

#### Workflow
1. Validate input directories exist
2. Discover all samples from imagery_downloader output
3. Extract bboxes from GeoTIFF metadata
4. Apply spatial tile-based splitting:
   - Divide bbox into tiles of size spatial_tile_size_deg
   - Assign tiles to train/val/test based on percentages
   - All samples in same tile → same split
5. Create output directory structure:
   ```
   train/ → sample_000001/, sample_000002/, ...
   val/   → ...
   test/  → ...
   ```
6. For each sample:
   - Create triplet directory
   - Copy pre.png/tif as `pre.*`
   - Copy post.png/tif as `post.*`
   - Copy label TIFF as `label.tif`
7. Generate metadata.csv with columns:
   - sample_id, split, pre_path, post_path, label_path, year, loss_bin, bbox_minx, bbox_miny, bbox_maxx, bbox_maxy
8. Validate integrity:
   - Count files match expected
   - Verify split percentages
   - Check all triplets complete
9. Generate report (console + log file)
10. Publish events

#### Output Structure
```
output/dataset_organizer/
├── train/
│   ├── sample_000001/
│   │   ├── pre.png
│   │   ├── post.png
│   │   └── label.tif
│   ├── sample_000002/
│   │   └── ...
│   └── ...
├── val/
│   ├── sample_000005/
│   │   └── ...
│   └── ...
├── test/
│   ├── sample_000010/
│   │   └── ...
│   └── ...
├── metadata.csv
├── split_report.txt
└── integrity_check.json
```

#### Key Implementation Files

**component.py**: ~250 lines
- BaseComponent subclass
- @register_component decorator
- initialize() → config validation, input directory checks
- execute() → main workflow above
- cleanup() → generate final report

**splitter.py**: ~250 lines
- Spatial tile class (bounds, split assignment)
- Tile grid generation from sample bboxes
- Split assignment logic
- Tile size handling for edge cases

**organizer.py**: ~200 lines
- Directory structure creation
- Triplet assembly (copy/symlink pre, post, label)
- Metadata extraction from GeoTIFFs
- Format conversion if needed (PNG from GeoTIFF)

**metadata_generator.py**: ~150 lines
- CSV generation from sample metadata
- Column definitions and ordering
- Metadata aggregation
- Report generation

#### Dependencies
- `rasterio` (read GeoTIFF metadata)
- `numpy` (array manipulation)
- `pandas` (CSV generation)
- Standard library: `os`, `shutil`, `pathlib`, `json`

---

## Integration Points

### With Existing Components
- **Input from sample_extractor**:
  - GeoTIFF patches with metadata
  - Bboxes and year information

- **Input from imagery_downloader**:
  - Pre/post Sentinel-2 imagery
  - GeoTIFF and PNG formats

### With GUI
- Both components appear in Component Panel
- imagery_downloader config dialog:
  - Input: path to sample_extractor output
  - Options: cloud_cover, date_range, bands
- dataset_organizer config dialog:
  - Inputs: paths to imagery_downloader and sample_extractor
  - Options: train/val/test percentages, tile size

### Event Publishing
Both components publish standard events:
- `{component_name}.start` → execution begins
- `{component_name}.progress` → during processing
- `{component_name}.complete` → on success
- `{component_name}.error` → on failure

---

## Testing Strategy

### [ ] Unit Tests

**imagery_downloader tests**:
- [ ] Date calculation for pre/post imagery
- [ ] Date range expansion algorithm
- [ ] Bbox extraction from GeoTIFF
- [ ] Cloud cover filtering logic
- [ ] Sentinel-2 band selection

**dataset_organizer tests**:
- [ ] Spatial tile grid generation
- [ ] Split assignment (verify percentages)
- [ ] Metadata CSV generation
- [ ] Integrity validation

### [ ] Integration Tests

- [ ] End-to-end: sample_extractor → imagery_downloader → dataset_organizer
- [ ] Output directory structure
- [ ] Metadata CSV format and correctness
- [ ] Train/val/test split verification
- [ ] File completeness (no missing triplets)

### [ ] Manual GUI Testing

- [ ] Launch GUI, select imagery_downloader
- [ ] Configure with test sample path
- [ ] Run and monitor logs
- [ ] Verify output structure
- [ ] Select dataset_organizer
- [ ] Configure split percentages
- [ ] Run and verify final structure

### [ ] Real Data Testing

- [ ] Small test set (5-10 samples)
- [ ] Verify Sentinel-2 downloads work
- [ ] Check imagery quality/alignment
- [ ] Validate train/val/test splits

---

## Configuration Files

### New: config/imagery_downloader.yaml
```yaml
imagery_downloader:
  cloud_cover_threshold: 30
  initial_date_range: 30
  max_date_range: 90
  reproject_to_crs: "EPSG:4326"
  bands: ["B4", "B3", "B2"]
  output_format: ["geotiff", "png"]
```

### New: config/dataset_organizer.yaml
```yaml
dataset_organizer:
  train_percentage: 70.0
  val_percentage: 15.0
  test_percentage: 15.0
  spatial_tile_size_deg: 1.0
  image_format: "png"
  create_metadata_csv: true
```

---

## Dependencies to Add

**requirements.txt or setup.py**:
```
earthengine-api>=0.1.400
rasterio>=1.3.0 (may already be present)
numpy>=1.20.0 (may already be present)
pandas>=1.3.0
Pillow>=8.0.0
```

**User Setup**:
```bash
pip install earthengine-api
earthengine authenticate  # Required before first use
```

---

## Implementation Checklist

### imagery_downloader

- [ ] Create directory structure
- [ ] Create component.py skeleton
- [ ] Implement GEE utilities (gee_utils.py)
- [ ] Implement Sentinel-2 logic (sentinel2.py)
- [ ] Implement image processor (image_processor.py)
- [ ] Add to schemas.py (component configuration)
- [ ] Add config file (config/imagery_downloader.yaml)
- [ ] Write unit tests
- [ ] Manual testing with small sample
- [ ] Integration testing with sample_extractor
- [ ] Commit

### dataset_organizer

- [ ] Create directory structure
- [ ] Create component.py skeleton
- [ ] Implement spatial splitter (splitter.py)
- [ ] Implement organizer (organizer.py)
- [ ] Implement metadata generator (metadata_generator.py)
- [ ] Add to schemas.py
- [ ] Add config file (config/dataset_organizer.yaml)
- [ ] Write unit tests
- [ ] Manual testing
- [ ] Integration testing with imagery_downloader
- [ ] Commit

### GUI Updates

- [ ] Add both components to GUI ComponentPanel
- [ ] Test component discovery
- [ ] Test configuration forms
- [ ] Test execution via GUI
- [ ] Verify logging and progress display

---

## Timeline Estimate

| Component | Phase | Estimate |
|-----------|-------|----------|
| imagery_downloader | Implementation | 3-4 hours |
| imagery_downloader | Testing | 2-3 hours |
| dataset_organizer | Implementation | 2-3 hours |
| dataset_organizer | Testing | 1-2 hours |
| Integration & GUI | Testing & refinement | 1-2 hours |
| **Total** | | **9-14 hours** |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Google Earth Engine API limits | Start with small test set, implement backoff retry |
| GEE authentication issues | Clear documentation, error handling for missing auth |
| Large downloads | Progress bars, show estimated time, allow resume |
| Spatial tile edge cases | Extra validation for bbox at tile boundaries |
| Missing imagery | Graceful handling with date range expansion |
| Slow performance | Implement batching, progress events every N samples |

---

## Next Steps

1. ✅ Get approval of plan (this document)
2. Commit GUI fixes (already staged)
3. Create imagery_downloader component
4. Create dataset_organizer component
5. Update schemas.py with both components
6. Create config files
7. Implement tests
8. Test full pipeline
9. Document in README

---

## Progress Tracking

**Phase**: imagery_downloader Implementation
**Completed**: 8/26 checklist items
**Last Activity**: imagery_downloader skeleton created 2025-10-28

### Completed
- [x] Create directory structure for imagery_downloader
- [x] Create component.py skeleton with @register_component
- [x] Implement gee_utils.py (Google Earth Engine utilities)
- [x] Implement sentinel2.py (Sentinel-2 band info)
- [x] Implement image_processor.py (Download/processing functions)
- [x] Add config_schema.py (GUI configuration)
- [x] Create README.md for imagery_downloader
- [x] Add to schemas.py (component configuration for GUI)

### In Progress
- [ ] Complete component.py with full execute() implementation
- [ ] Add unit tests for imagery_downloader
- [ ] Manual testing with small sample

### Next
- [ ] Create dataset_organizer component structure
- [ ] Implement dataset_organizer files
- [ ] Integration testing between components

Update this section as implementation proceeds.
