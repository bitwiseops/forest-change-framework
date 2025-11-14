# Component Categories Guide

This guide explains each component category and when to use components from each.

## Overview

Components are organized into 5 categories representing stages in a typical forest change analysis pipeline:

```
Data Ingestion → Preprocessing → Analysis → Visualization → Export
```

## 1. Data Ingestion

**Purpose**: Load forest change data from various sources

**Responsibilities**:
- Connect to data sources (files, databases, APIs)
- Parse and validate data
- Handle authentication/authorization
- Report data quality metrics
- Handle errors gracefully

### When to Use
- Loading satellite imagery
- Reading tabular forest metrics data
- Fetching data from APIs
- Querying databases
- Reading stream data

### Example Sources
- **Files**: CSV, GeoTIFF, NetCDF, HDF5
- **Databases**: PostgreSQL, MongoDB, Elasticsearch
- **Cloud**: AWS S3, Google Cloud Storage, Azure
- **APIs**: USGS, Google Earth Engine, GEDI
- **Streams**: Real-time satellite feeds, sensor networks

### Event Naming Pattern
```
{component_name}.start
{component_name}.progress
{component_name}.complete  ← primary event
{component_name}.error
```

### Configuration Example
```json
{
  "source_type": "s3",
  "bucket": "forest-data",
  "key": "satellite_imagery/2020/*",
  "region": "us-west-2",
  "profile": "default"
}
```

### Component Template
See [Data Ingestion README](../src/forest_change_framework/components/data_ingestion/README.md)

## 2. Preprocessing

**Purpose**: Clean, validate, and transform raw data for analysis

**Responsibilities**:
- Validate data integrity
- Handle missing values
- Normalize data ranges
- Transform formats
- Filter outliers
- Align spatial/temporal data

### When to Use
- Cleaning noisy satellite imagery
- Harmonizing multi-source data
- Handling gaps in time series
- Normalizing spectral indices
- Geospatial alignment and registration
- Temporal interpolation

### Data Quality Checks
- Missing value detection
- Outlier identification
- Range validation
- Format verification
- Metadata completeness

### Event Naming Pattern
```
{component_name}.start
{component_name}.progress
{component_name}.complete  ← primary event
{component_name}.error
```

### Configuration Example
```json
{
  "method": "knn",
  "k_neighbors": 5,
  "missing_threshold": 0.3,
  "normalize_method": "minmax",
  "temporal_interpolation": true
}
```

### Component Template
See [Preprocessing README](../src/forest_change_framework/components/preprocessing/README.md)

## 3. Analysis

**Purpose**: Detect forest changes and compute analysis metrics

**Responsibilities**:
- Implement change detection algorithms
- Calculate forest metrics
- Perform statistical analysis
- Identify trends and anomalies
- Generate classified outputs
- Report confidence/uncertainty

### When to Use
- Detecting forest loss/gain
- Computing spectral indices (NDVI, EVI, etc.)
- Classifying forest types
- Trend analysis
- Anomaly detection
- Impact assessment

### Common Algorithms
- **Change Detection**: BFAST, LandTrendr, CubistR, CCDC
- **Classification**: Random Forest, SVM, CNN
- **Metrics**: Vegetation indices, biomass estimation, forest cover
- **Temporal**: Trend analysis, phenology, seasonality

### Event Naming Pattern
```
{component_name}.start
{component_name}.progress
{component_name}.complete  ← primary event
{component_name}.error
```

### Configuration Example
```json
{
  "algorithm": "ndvi_change_detector",
  "threshold": 0.15,
  "min_duration": 2,
  "confidence_level": 0.95,
  "temporal_window": 1
}
```

### Component Template
See [Analysis README](../src/forest_change_framework/components/analysis/README.md)

## 4. Visualization

**Purpose**: Render analysis results as maps, charts, and reports

**Responsibilities**:
- Create cartographic outputs
- Generate charts and graphs
- Build interactive dashboards
- Produce summary statistics
- Create publication-ready figures
- Generate reports

### When to Use
- Creating change maps
- Generating time series plots
- Building interactive web dashboards
- Creating PDF reports
- Producing publication figures
- Generating maps for stakeholders

### Output Types
- **Maps**: GeoTIFF, PNG, SVG with proper projections
- **Charts**: Line plots, bar charts, histograms, scatter plots
- **Dashboards**: Interactive web interfaces
- **Reports**: PDF, HTML with analysis summaries
- **3D**: 3D terrain with change overlays

### Event Naming Pattern
```
{component_name}.start
{component_name}.progress
{component_name}.complete  ← primary event
{component_name}.error
```

### Configuration Example
```json
{
  "output_format": "png",
  "resolution": "300dpi",
  "projection": "EPSG:4326",
  "color_scheme": "viridis",
  "include_legend": true,
  "title": "Forest Change 2020-2024"
}
```

### Component Template
See [Visualization README](../src/forest_change_framework/components/visualization/README.md)

## 5. Export

**Purpose**: Save results to various formats and destinations

**Responsibilities**:
- Write data to files
- Upload to storage systems
- Insert into databases
- Publish via APIs
- Generate data packages
- Manage output metadata
- Organize ML training datasets

### When to Use
- Saving results to disk
- Uploading to cloud storage
- Writing to databases
- Publishing via web services
- Creating data packages for sharing
- Archiving results
- Organizing satellite imagery into training datasets

### Output Destinations
- **Local**: Files (CSV, JSON, GeoJSON, GeoTIFF)
- **Databases**: PostgreSQL, MongoDB, Elasticsearch
- **Cloud**: AWS S3, Google Cloud Storage, Azure Blob
- **APIs**: HTTP endpoints, FTP, SFTP
- **Archives**: ZIP, TAR with metadata
- **ML Datasets**: Organized train/val/test splits with metadata

### Event Naming Pattern
```
{component_name}.start
{component_name}.progress
{component_name}.complete  ← primary event
{component_name}.error
```

### Configuration Example
```json
{
  "destination": "s3",
  "bucket": "forest-results",
  "path": "2024/change_analysis/",
  "format": "geojson",
  "compression": "gzip",
  "public": false
}
```

### Example: Dataset Organizer Component

The **dataset_organizer** component organizes satellite imagery into ML training datasets:

**Purpose**: Create train/val/test splits from imagery and sample patches using spatial tiling to prevent data leakage

**Configuration**:
```json
{
  "imagery_directory": "path/to/imagery_downloader_output",
  "sample_patches_directory": "path/to/sample_extractor_output",
  "train_percentage": 70.0,
  "val_percentage": 15.0,
  "test_percentage": 15.0,
  "spatial_tile_size_deg": 1.0,
  "image_format": "png",
  "create_metadata_csv": true
}
```

**Output Structure**:
```
output/
├── train/
│   ├── {sample_id}/
│   │   ├── pre.png (pre-event imagery)
│   │   ├── post.png (post-event imagery)
│   │   └── label.tif (ground truth)
│   └── ... (more samples)
├── val/
├── test/
└── metadata.csv (sample metadata and paths)
```

**Key Features**:
- **Geographic Tiling**: Prevents spatial data leakage by assigning all samples in a tile to same split
- **Flexible Formats**: Supports PNG, GeoTIFF, or both formats
- **Metadata Tracking**: Generates CSV with sample information and file paths
- **Comprehensive Validation**: Verifies triplet integrity and split distribution

**Testing**: Comprehensive test suite with 58 tests (87.5% coverage) including:
- 27 unit tests for spatial tiling algorithm
- 14 unit tests for directory organization
- 11 integration tests with mock data
- 6 real-world tests with actual sample_extractor output

See [Dataset Organizer Tests](../tests/integration/test_dataset_organizer_real_data.py) for examples.

### Component Template
See [Export README](../src/forest_change_framework/components/export/README.md)

## Category Selection Guide

### Decision Tree

```
I want to...
├── Load data from a source
│   └── → Use Data Ingestion
├── Clean/transform the data
│   └── → Use Preprocessing
├── Analyze/detect changes
│   └── → Use Analysis
├── Create maps/charts
│   └── → Use Visualization
└── Save results
    └── → Use Export
```

### Example Workflows

#### Workflow 1: Basic Change Detection
```
CSV Loader (Ingestion)
  ↓
Missing Value Handler (Preprocessing)
  ↓
NDVI Change Detector (Analysis)
  ↓
Change Map Renderer (Visualization)
  ↓
GeoJSON Exporter (Export)
```

#### Workflow 2: Multi-Source Analysis
```
Satellite Data Loader (Ingestion) ─┐
Cloud Cover Remover (Preprocessing) │
                                    ├→ Data Harmonizer (Preprocessing)
Ground Truth Loader (Ingestion)   ─┤        ↓
                                    └→ Classification (Analysis)
                                         ↓
                                     Web Dashboard (Visualization)
                                         ↓
                                     Cloud Uploader (Export)
```

#### Workflow 3: Time Series Analysis
```
Time Series Loader (Ingestion)
  ↓
Temporal Interpolator (Preprocessing)
  ↓
Trend Analyzer (Analysis)
  ↓
Timeline Plotter (Visualization)
  ↓
CSV Exporter (Export)
```

## Inter-Category Communication

Components in different categories communicate ONLY through events:

```
Ingestion Component
  ├─ publishes → "ingestion.complete"
  │
Preprocessing Component (subscribes to "ingestion.complete")
  ├─ publishes → "preprocessing.complete"
  │
Analysis Component (subscribes to "preprocessing.complete")
  ├─ publishes → "analysis.complete"
  │
Visualization Component (subscribes to "analysis.complete")
  ├─ publishes → "visualization.complete"
  │
Export Component (subscribes to "visualization.complete")
```

## Best Practices

### 1. Single Responsibility
- Each component does ONE thing well
- Don't combine responsibilities from different categories
- Keep logic focused and testable

### 2. Clear Contracts
- Document input/output requirements
- Define configuration schema
- Specify event payloads

### 3. Error Handling
- Validate all inputs
- Provide meaningful error messages
- Publish error events

### 4. Performance
- Consider memory usage for large datasets
- Log timing information
- Optimize algorithms

### 5. Configurability
- Externalize all parameters
- Support sensible defaults
- Validate configuration early

## See Also

- [Architecture Documentation](architecture.md)
- [Getting Started Guide](getting-started.md)
- [API Reference](api/)
- [Component Development](../src/forest_change_framework/components/)
