# Imagery Downloader Component

Download cloud-free Sentinel-2 satellite imagery from Google Earth Engine for forest change detection training datasets.

## Overview

This component downloads pre/post forest loss event Sentinel-2 imagery for samples extracted by the Sample Extractor component. It:

- Reads GeoTIFF patches with metadata (bbox, year)
- Queries Google Earth Engine for Sentinel-2 scenes
- Downloads cloud-free imagery (configurable threshold: default <30% cloud)
- Automatically expands search dates if needed (up to ±90 days)
- Saves imagery as both GeoTIFF (preserves metadata) and PNG (for ML training)
- Organizes output in a structured directory format

## Requirements

1. **Google Earth Engine Account**: Free account at https://earthengine.google.com/
2. **Authentication**: Run `earthengine authenticate` before first use
3. **Python Package**: `pip install earthengine-api`

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `aoi_geojson` | str (path) | Required | Path to GeoJSON from sample_extractor |
| `cloud_cover_threshold` | int | 30 | Max cloud cover % (0-100) |
| `initial_date_range` | int | 30 | Initial ±days around target date |
| `max_date_range` | int | 90 | Max ±days to expand search |
| `reproject_to_crs` | str | EPSG:4326 | Output coordinate reference system |
| `bands` | list | ["B4", "B3", "B2"] | Sentinel-2 bands to download |
| `output_format` | list | ["geotiff", "png"] | Output types |

## Usage

### Via CLI

```bash
forest-change-framework run visualization imagery_downloader \
  --aoi-geojson path/to/samples.geojson \
  --cloud-cover-threshold 30 \
  --initial-date-range 30
```

### Via GUI

1. Launch: `forest-change-framework gui`
2. Select "Imagery Downloader" from Components panel
3. Click "Configure"
4. Fill in settings:
   - AOI GeoJSON: Path to sample_extractor output
   - Cloud Cover: 30%
   - Date Range: 30 days
5. Click "Run"
6. Monitor progress in execution log

## Output Structure

```
data/imagery_downloader/
├── sample_000001/
│   ├── pre.tif              # Pre-event Sentinel-2 GeoTIFF
│   ├── pre.png              # Pre-event PNG thumbnail
│   ├── post.tif             # Post-event Sentinel-2 GeoTIFF
│   ├── post.png             # Post-event PNG thumbnail
│   └── metadata.json        # Download metadata
├── sample_000002/
│   └── ...
└── download_log.csv         # Summary of downloads
```

## Sentinel-2 Bands

Supported bands:
- **B2**: Blue (10m)
- **B3**: Green (10m)
- **B4**: Red (10m)
- **B8**: NIR (10m)
- **B5, B6, B7, B8A**: Red Edge (20m)
- **B11, B12**: SWIR (20m)

Common combinations:
- **RGB**: `["B4", "B3", "B2"]` - True color
- **NDVI**: `["B8", "B4"]` - Vegetation index
- **NDBI**: `["B11", "B8"]` - Built-up index
- **NDMI**: `["B8", "B11"]` - Moisture index

## Date Range Logic

The component automatically expands search dates if no suitable imagery is found:

1. Search for imagery within **±30 days** of target date
2. If found: Download and continue
3. If not found: Expand to **±60 days** and retry
4. If still not found: Expand to **±90 days** and retry
5. If no imagery found after max range: Skip sample and log warning

This ensures best cloud-free imagery is found without requiring manual date adjustments.

## Troubleshooting

### "Failed to initialize Google Earth Engine"

**Cause**: Not authenticated with GEE

**Solution**:
```bash
earthengine authenticate
```

### "AOI GeoJSON file not found"

**Cause**: Path doesn't exist or is incorrect

**Solution**: Verify path to sample_extractor output, ensure file exists

### "No suitable imagery found"

**Cause**: Sentinel-2 hasn't imaged that location during the date range

**Solution**:
- Try different region/date
- Increase cloud_cover_threshold
- Increase max_date_range

## Performance Notes

- Typical download: 10-30 seconds per sample
- Large areas: May take several minutes
- Google Earth Engine limits: ~40 API calls/second (free tier)
- For 1000 samples: ~30-50 minutes

## Next Component

Output from imagery_downloader feeds into **dataset_organizer**, which:
- Organizes imagery into train/val/test splits
- Creates (pre, post, label) triplets
- Generates metadata CSV for ML training

## References

- [Sentinel-2 on Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- [Earth Engine API Documentation](https://developers.google.com/earth-engine/guides)
- [Sentinel-2 Band Information](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/overview)
