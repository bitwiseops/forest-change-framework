# Export Components

Export components handle saving and exporting results to various formats and destinations.

## Purpose

Export components are responsible for:
- Exporting data to various file formats (CSV, GeoJSON, GeoTIFF, NetCDF, etc.)
- Writing to databases (PostgreSQL, MongoDB, etc.)
- Uploading to cloud storage (S3, GCS, Azure, etc.)
- Publishing reports and summaries
- API data delivery

## Creating a New Component

### Naming Conventions

- **Directory name**: `snake_case_name` (e.g., `geojson_exporter`, `s3_uploader`, `database_writer`, `csv_export`)
- **Component name**: Matches directory name
- **Class name**: `PascalCase` (e.g., `GeoJSONExporter`, `S3Uploader`, `DatabaseWriter`, `CSVExport`)

### Event Naming Conventions

- `{component_name}.start`: When starting export
- `{component_name}.progress`: During export with progress data
- `{component_name}.complete`: When successfully exported
- `{component_name}.error`: When an error occurs

Example:
```python
self.publish_event("geojson_exporter.complete", {
    "output_path": "s3://bucket/data.geojson",
    "records_exported": 5000,
    "file_size_mb": 12.3,
})
```

### Configuration Example

```python
def initialize(self, config: Dict[str, Any]) -> None:
    self.output_path = config.get("output_path")
    self.format = config.get("format", "geojson")
    self.compression = config.get("compression", None)
```

## Minimal Template

```python
from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

@register_component(
    category="export",
    name="my_exporter",
    version="1.0.0",
    description="Exports results to various formats",
)
class MyExporter(BaseComponent):
    @property
    def name(self) -> str:
        return "my_exporter"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict) -> None:
        self._config = config
        self.output_path = config.get("output_path")

    def execute(self, data: Any, *args, **kwargs) -> str:
        # Export data
        output = self._export(data)
        self.publish_event("my_exporter.complete", {
            "output": output,
            "records": len(data) if isinstance(data, list) else 1,
        })
        return output

    def cleanup(self) -> None:
        pass

    def _export(self, data):
        # TODO: Implement export logic
        return self.output_path
```

## Best Practices

1. **Validate Output Path**: Ensure directory exists or can be created
2. **Handle Errors**: Provide clear error messages for I/O failures
3. **Report Statistics**: Include export metrics (size, records, duration)
4. **Support Compression**: Offer optional compression for large files
5. **Streaming Export**: For large datasets, export in chunks to save memory
6. **Validation**: Verify exported data integrity
7. **Metadata**: Include metadata about the export (timestamp, source, etc.)

## Common Export Formats

- **Tabular**: CSV, TSV, Excel (XLSX)
- **Geospatial**: GeoJSON, Shapefile, GeoTIFF, NetCDF
- **Database**: PostgreSQL, MongoDB, Elasticsearch
- **Cloud**: AWS S3, Google Cloud Storage, Azure Blob Storage
- **Web**: HTTP API, REST endpoint

## See Also

- [Framework Architecture](../../docs/architecture.md)
- [Visualization Components](../visualization/README.md)
- [Data Ingestion Components](../data_ingestion/README.md)
