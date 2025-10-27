# Sample Extractor Component Development

## Component Overview
**Name:** Sample Extractor Component
**Category:** Export
**Version:** 1.0.0
**Purpose:** Extract spatially-bounded TIFF patches from Hansen tiles based on stratified samples from AOI GeoJSON

---

## Requirements

### Inputs
1. GeoJSON from AOI sampler (contains AOIs with bbox, year-by-year loss data, bin category)
2. Hansen VRT or tile directory (source of lossyear band data)

### Processing
1. Read GeoJSON and group AOIs by year and bin category
2. Stratified random sampling: Select N/bins total samples per bin, distributed across available years
3. For each selected sample:
   - Extract lossyear band in native 30m resolution
   - Clip to AOI bbox
   - Save as GeoTIFF

### Output
1. Directory of extracted TIFF patches (flat structure)
2. CSV/JSON metadata file mapping sample_id to properties (aoi_id, year, bin, bbox, path)

---

## Sampling Strategy
- **Distribution:** Equal per bin total (N/bins samples per bin)
- **Year handling:** Independent sampling per year (different AOIs per year)
- **Band:** Only lossyear
- **Resolution:** Native Hansen resolution (30m pixels)

---

## Development Phases

### Phase 1: Core Module Development - [✅] COMPLETE
- [✅] **sampling.py** (157 lines, 97% coverage)
  - [✅] `group_aois_by_year_and_bin()` - Organize GeoJSON features by year and loss bin
  - [✅] `select_stratified_samples()` - Select N/bins samples per bin
  - [✅] `balance_samples_across_years()` - Distribute selected samples across years
  - [✅] `create_sample_manifest()` - Generate unique IDs and metadata

- [✅] **extraction.py** (310 lines, 62% coverage)
  - [✅] `calculate_geotransform()` - Compute GDAL pixel-to-coordinate transform
  - [✅] `extract_patch_from_vrt()` - Clip lossyear band to bbox from VRT
  - [✅] `extract_patch_from_tiles()` - Handle tile-based Hansen data extraction
  - [✅] `save_geotiff()` - Write extracted patch with proper georeferencing and metadata

- [✅] **metadata.py** (269 lines, 62% coverage)
  - [✅] `create_metadata_dict()` - Build sample manifest as nested dict
  - [✅] `write_metadata_csv()` - Export to CSV format (requires pandas)
  - [✅] `write_metadata_json()` - Export to JSON format
  - [✅] `validate_metadata()` - Comprehensive validation with detailed reporting
  - [✅] `print_validation_report()` - Human-readable validation output

### Phase 2: Component Implementation - [✅] COMPLETE
- [✅] **component.py** (360 lines)
  - [✅] Component registration with decorator (@register_component)
  - [✅] Configuration parameters:
    - `aoi_geojson`: Path to GeoJSON from AOI sampler (required)
    - `hansen_vrt`: Path to Hansen VRT or tiles (required)
    - `output_dir`: Output directory (required)
    - `samples_per_bin`: Number of samples per loss bin (default: 10)
    - `metadata_format`: "csv", "json", or "both" (default: "both")
    - `patch_crs`: Output CRS (default: EPSG:4326)
    - `include_metadata_in_tiff`: Store metadata in TIFF tags (default: true)
    - `validate`: Validate metadata after extraction (default: true)
    - `band`: Hansen band to extract (default: 2 for lossyear)
  - [✅] `initialize()` method - Config validation with detailed error messages
  - [✅] `execute()` method - Full 8-step workflow orchestration
  - [✅] Event publishing for progress tracking (start, progress, complete, error)
  - [✅] `cleanup()` method
  - [✅] Helper methods:
    - `_load_geojson()` - Load and parse GeoJSON
    - `_extract_patches()` - Extract all TIFF patches with progress
    - `_write_metadata()` - Write metadata in configured format(s)
  - [✅] Full integration of Phase 1 modules

### Phase 3: Testing - [✅] COMPLETE (79 tests total)
- [✅] **Unit Tests** (tests/unit/test_components/test_sample_extractor.py - 40 tests)
  - [✅] Stratified sampling correctness (4 tests)
  - [✅] Year distribution verification (3 tests)
  - [✅] Manifest creation accuracy (4 tests)
  - [✅] Metadata generation (5 tests)
  - [✅] CSV/JSON output format validation (3 tests)
  - [✅] Geotransform calculation (2 tests)
  - [✅] TIFF extraction and saving (7 tests)
  - [✅] Error handling and edge cases (8 tests)
  - [✅] End-to-end workflow integration (1 test)

- [✅] **Phase 2 Component Tests** (tests/unit/test_components/test_sample_extractor_component.py - 22 tests)
  - [✅] Component initialization and configuration validation (7 tests)
  - [✅] GeoJSON loading and parsing (4 tests)
  - [✅] Event publishing verification (2 tests)
  - [✅] Metadata format options (csv, json, both) (3 tests)
  - [✅] Cleanup and configuration options (3 tests)
  - [✅] Workflow orchestration (3 tests)

- [✅] **Integration Tests** (tests/integration/test_sample_extractor_integration.py - 17 tests)
  - [✅] End-to-end with sample AOI GeoJSON
  - [✅] Component initialization and configuration validation
  - [✅] GeoJSON loading and property integrity
  - [✅] Stratified sampling by loss bin
  - [✅] Metadata format options (csv, json, both)
  - [✅] Output directory structure creation
  - [✅] Validation report structure and accuracy
  - [✅] Invalid bbox detection
  - [✅] Duplicate ID detection
  - [✅] Missing file detection
  - [✅] CSV and JSON export format validation
  - [✅] Sample ID uniqueness and sequential generation
  - [✅] Year distribution across samples
  - [✅] Loss bin distribution in manifest

---

## Configuration Schema

```python
{
    "samples_per_bin": 10,           # int: Number of samples per loss bin
    "output_format": "csv",          # "csv" or "json"
    "patch_crs": "EPSG:4326",       # Output CRS
    "include_metadata_in_tiff": True # Store metadata in TIFF tags
}
```

---

## Output Structure

```
sample_patches/
├── patches/
│   ├── sample_001.tif          # 30m lossyear band, georeferenced
│   ├── sample_002.tif
│   └── ...
├── samples_metadata.csv
└── samples_metadata.json
```

### Metadata CSV Format
```
sample_id,aoi_id,year,loss_bin,minx,miny,maxx,maxy,tiff_path,loss_percentage
001,cell_12345,2010,low_loss,-60.5,-10.2,-60.4,-10.1,patches/sample_001.tif,12.5
```

### Metadata JSON Format
```json
{
  "samples": [
    {
      "sample_id": "001",
      "aoi_id": "cell_12345",
      "year": 2010,
      "loss_bin": "low_loss",
      "bbox": {"minx": -60.5, "miny": -10.2, "maxx": -60.4, "maxy": -10.1},
      "tiff_path": "patches/sample_001.tif",
      "loss_percentage": 12.5
    }
  ]
}
```

---

## Key Features
- ✅ Stratified sampling for balanced dataset
- ✅ Independent per-year sampling
- ✅ Dual metadata output (CSV + JSON)
- ✅ Native 30m resolution preservation
- ✅ Georeferenced TIFF output with CRS info
- ✅ Memory-efficient block-based extraction
- ✅ Event-driven progress tracking
- ✅ Configurable sampling strategy

---

## Dependencies
- rasterio (TIFF extraction)
- pandas (metadata handling)
- geopandas (GeoJSON reading)
- numpy (data processing)

---

## Progress Tracker

### Phase 1: [✅] 100%
- [✅] sampling.py (100% - 4 functions, 157 lines, 97% coverage)
- [✅] extraction.py (100% - 4 functions, 310 lines, 62% coverage)
- [✅] metadata.py (100% - 5 functions, 269 lines, 62% coverage)

### Phase 2: [✅] 100%
- [✅] component.py (100% - Full implementation, 360 lines, 99% coverage)

### Phase 3: [✅] 100% (79 tests total, all passing)
- [✅] Phase 1 unit tests (100% - 40 tests, all passing)
- [✅] Phase 2 component tests (100% - 22 tests, all passing)
- [✅] Integration tests (100% - 17 tests, all passing)

---

## Notes
- Start with Phase 1 modules
- Design for memory efficiency (block-based extraction, streaming where possible)
- Follow existing component patterns from AOI Sampler
- Reuse validation and utility functions where applicable
