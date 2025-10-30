"""Component configuration schemas for form generation.

This module defines explicit configuration schemas for all components,
enabling automatic form generation in the GUI.
"""

from typing import Any, Dict, List, Optional, Union

# Type definitions for schema fields
FieldType = Union[str, int, float, bool, list, dict]


class FieldSchema:
    """Schema definition for a single configuration field."""

    def __init__(
        self,
        name: str,
        type_: type,
        label: str,
        description: str = "",
        required: bool = False,
        default: Any = None,
        choices: Optional[List[Any]] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        file_filter: Optional[str] = None,  # For file pickers: "*.geojson;;*.json"
        widget_type: Optional[str] = None,  # Override default widget type
        group: str = "General",  # Field grouping in tabs/sections
    ) -> None:
        """
        Initialize field schema.

        Args:
            name: Configuration key name (e.g., "grid_cell_size_km")
            type_: Python type (str, int, float, bool, list, dict)
            label: Human-readable field label (e.g., "Grid Cell Size (km)")
            description: Help text explaining the field
            required: Whether field is required
            default: Default value if not provided
            choices: List of valid choices (for enums)
            min_value: Minimum numeric value
            max_value: Maximum numeric value
            min_length: Minimum string length
            max_length: Maximum string length
            file_filter: File picker filter (Qt format)
            widget_type: Override automatic widget type (e.g., "file", "directory")
            group: Tab/section name for grouping related fields
        """
        self.name = name
        self.type_ = type_
        self.label = label
        self.description = description
        self.required = required
        self.default = default
        self.choices = choices
        self.min_value = min_value
        self.max_value = max_value
        self.min_length = min_length
        self.max_length = max_length
        self.file_filter = file_filter
        self.widget_type = widget_type
        self.group = group


class ComponentSchema:
    """Schema definition for a component's configuration."""

    def __init__(
        self,
        component_name: str,
        category: str,
        fields: List[FieldSchema],
        description: str = "",
    ) -> None:
        """
        Initialize component schema.

        Args:
            component_name: Name of the component
            category: Component category (data_ingestion, analysis, etc.)
            fields: List of FieldSchema objects
            description: Component description
        """
        self.component_name = component_name
        self.category = category
        self.fields = fields
        self.description = description

    def get_field(self, name: str) -> Optional[FieldSchema]:
        """Get field schema by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary for JSON serialization."""
        return {
            "component": self.component_name,
            "category": self.category,
            "description": self.description,
            "fields": [
                {
                    "name": f.name,
                    "type": f.type_.__name__,
                    "label": f.label,
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                    "choices": f.choices,
                    "constraints": {
                        "min": f.min_value,
                        "max": f.max_value,
                    },
                    "widget": f.widget_type,
                    "group": f.group,
                }
                for f in self.fields
            ],
        }


# ============================================================================
# Component Schemas
# ============================================================================

HANSEN_SCHEMA = ComponentSchema(
    component_name="hansen",
    category="data_ingestion",
    description="Download and mosaic Hansen Forest Change data by biome",
    fields=[
        FieldSchema(
            name="data_folder",
            type_=str,
            label="Data Folder",
            description="Path to store downloaded Hansen tiles",
            required=False,
            default="./data/hansen_tiles",
            widget_type="directory",
            group="Paths",
        ),
        FieldSchema(
            name="output_folder",
            type_=str,
            label="Output Folder",
            description="Path where VRT mosaic will be saved",
            required=False,
            default="./data/hansen_output",
            widget_type="directory",
            group="Paths",
        ),
        FieldSchema(
            name="version",
            type_=str,
            label="Dataset Version",
            description="Hansen dataset version to download",
            required=False,
            default="GFC-2024-v1.12",
            group="Settings",
        ),
        FieldSchema(
            name="timeout",
            type_=int,
            label="Download Timeout (seconds)",
            description="Maximum seconds to wait for each tile download",
            required=False,
            default=30,
            min_value=5,
            max_value=300,
            group="Settings",
        ),
    ],
)

AOI_SAMPLER_SCHEMA = ComponentSchema(
    component_name="aoi_sampler",
    category="analysis",
    description="Sample areas of interest from Hansen data",
    fields=[
        FieldSchema(
            name="hansen_vrt",
            type_=str,
            label="Hansen VRT File",
            description="Path to Hansen VRT mosaic",
            required=True,
            widget_type="file",
            file_filter="VRT Files (*.vrt);;All Files (*)",
            group="Input",
        ),
        FieldSchema(
            name="grid_cell_size_km",
            type_=float,
            label="Grid Cell Size (km)",
            description="Size of each grid cell in kilometers",
            required=False,
            default=1.0,
            min_value=0.1,
            max_value=100.0,
            group="Grid Settings",
        ),
        FieldSchema(
            name="min_validity_threshold",
            type_=float,
            label="Min Validity Threshold (%)",
            description="Minimum data validity percentage for inclusion",
            required=False,
            default=80.0,
            min_value=0.0,
            max_value=100.0,
            group="Validation",
        ),
        FieldSchema(
            name="output_format",
            type_=str,
            label="Output Format",
            description="Format for output data",
            required=False,
            default="geojson",
            choices=["geojson", "json"],
            widget_type="combo",
            group="Output",
        ),
        FieldSchema(
            name="include_loss_by_year",
            type_=bool,
            label="Include Loss by Year",
            description="Calculate annual loss breakdown",
            required=False,
            default=True,
            group="Output",
        ),
        FieldSchema(
            name="keep_invalid_aois",
            type_=bool,
            label="Keep Invalid AOIs",
            description="Include AOIs with low data validity (marked as invalid)",
            required=False,
            default=False,
            group="Validation",
        ),
        FieldSchema(
            name="create_visualizations",
            type_=bool,
            label="Create Visualizations",
            description="Generate yearly loss maps",
            required=False,
            default=False,
            group="Output",
        ),
        FieldSchema(
            name="visualization_dpi",
            type_=int,
            label="Visualization DPI",
            description="Resolution for generated maps",
            required=False,
            default=150,
            min_value=72,
            max_value=600,
            group="Output",
        ),
    ],
)

SAMPLE_EXTRACTOR_SCHEMA = ComponentSchema(
    component_name="sample_extractor",
    category="export",
    description="Extract stratified samples from AOI data",
    fields=[
        FieldSchema(
            name="aoi_geojson",
            type_=str,
            label="AOI GeoJSON File",
            description="Path to GeoJSON file from AOI sampler",
            required=True,
            widget_type="file",
            file_filter="GeoJSON Files (*.geojson);;JSON Files (*.json)",
            group="Input",
        ),
        FieldSchema(
            name="hansen_vrt",
            type_=str,
            label="Hansen VRT File",
            description="Path to Hansen VRT mosaic",
            required=True,
            widget_type="file",
            file_filter="VRT Files (*.vrt);;All Files (*)",
            group="Input",
        ),
        FieldSchema(
            name="samples_per_bin",
            type_=int,
            label="Samples per Bin",
            description="Number of samples to extract per loss bin",
            required=False,
            default=10,
            min_value=1,
            max_value=1000,
            group="Sampling",
        ),
        FieldSchema(
            name="metadata_format",
            type_=str,
            label="Metadata Format",
            description="Format for exporting metadata",
            required=False,
            default="both",
            choices=["csv", "json", "both"],
            widget_type="combo",
            group="Output",
        ),
        FieldSchema(
            name="patch_crs",
            type_=str,
            label="Patch CRS",
            description="Coordinate reference system for extracted patches",
            required=False,
            default="EPSG:4326",
            group="Output",
        ),
        FieldSchema(
            name="include_metadata_in_tiff",
            type_=bool,
            label="Include Metadata in TIFF",
            description="Store metadata as TIFF tags",
            required=False,
            default=True,
            group="Output",
        ),
        FieldSchema(
            name="validate",
            type_=bool,
            label="Validate Output",
            description="Validate metadata and patches after extraction",
            required=False,
            default=True,
            group="Validation",
        ),
        FieldSchema(
            name="band",
            type_=int,
            label="Hansen Band",
            description="Band number to extract (2=lossyear)",
            required=False,
            default=2,
            choices=[1, 2, 3],
            widget_type="combo",
            group="Input",
        ),
    ],
)

IMAGERY_DOWNLOADER_SCHEMA = ComponentSchema(
    component_name="imagery_downloader",
    category="visualization",
    description="Download Sentinel-2 satellite imagery from Google Earth Engine",
    fields=[
        FieldSchema(
            name="aoi_geojson",
            type_=str,
            label="AOI GeoJSON File",
            description="Path to GeoJSON file from sample_extractor",
            required=True,
            widget_type="file",
            file_filter="GeoJSON Files (*.geojson);;JSON Files (*.json)",
            group="Input",
        ),
        FieldSchema(
            name="cloud_cover_threshold",
            type_=int,
            label="Cloud Cover Threshold (%)",
            description="Maximum cloud cover percentage to accept (0-100)",
            required=False,
            default=30,
            min_value=0,
            max_value=100,
            group="Sentinel-2 Settings",
        ),
        FieldSchema(
            name="initial_date_range",
            type_=int,
            label="Initial Date Range (±days)",
            description="Initial ±days around target date to search",
            required=False,
            default=30,
            min_value=1,
            max_value=180,
            group="Sentinel-2 Settings",
        ),
        FieldSchema(
            name="max_date_range",
            type_=int,
            label="Max Date Range (±days)",
            description="Maximum ±days to expand search if no imagery found",
            required=False,
            default=90,
            min_value=1,
            max_value=365,
            group="Sentinel-2 Settings",
        ),
        FieldSchema(
            name="reproject_to_crs",
            type_=str,
            label="Output CRS",
            description="Target coordinate reference system for output imagery",
            required=False,
            default="EPSG:4326",
            group="Output Settings",
        ),
        FieldSchema(
            name="bands",
            type_=list,
            label="Sentinel-2 Bands",
            description="Bands to download (e.g., B4=Red, B3=Green, B2=Blue)",
            required=False,
            default=["B4", "B3", "B2"],
            group="Sentinel-2 Settings",
        ),
        FieldSchema(
            name="output_format",
            type_=list,
            label="Output Formats",
            description="Save as GeoTIFF (metadata) and/or PNG (ML training)",
            required=False,
            default=["geotiff", "png"],
            choices=["geotiff", "png"],
            widget_type="multi_select",
            group="Output Settings",
        ),
    ],
)

DATASET_ORGANIZER_SCHEMA = ComponentSchema(
    component_name="dataset_organizer",
    category="export",
    description="Organize satellite imagery into ML training datasets with spatial splits",
    fields=[
        FieldSchema(
            name="imagery_directory",
            type_=str,
            label="Imagery Directory",
            description="Path to imagery_downloader output directory",
            required=True,
            widget_type="directory",
            group="Input",
        ),
        FieldSchema(
            name="sample_patches_directory",
            type_=str,
            label="Sample Patches Directory",
            description="Path to sample_extractor output directory",
            required=True,
            widget_type="directory",
            group="Input",
        ),
        FieldSchema(
            name="train_percentage",
            type_=float,
            label="Training Percentage (%)",
            description="Percentage of samples for training",
            required=False,
            default=70.0,
            min_value=0.0,
            max_value=100.0,
            group="Split Settings",
        ),
        FieldSchema(
            name="val_percentage",
            type_=float,
            label="Validation Percentage (%)",
            description="Percentage of samples for validation",
            required=False,
            default=15.0,
            min_value=0.0,
            max_value=100.0,
            group="Split Settings",
        ),
        FieldSchema(
            name="test_percentage",
            type_=float,
            label="Test Percentage (%)",
            description="Percentage of samples for testing",
            required=False,
            default=15.0,
            min_value=0.0,
            max_value=100.0,
            group="Split Settings",
        ),
        FieldSchema(
            name="spatial_tile_size_deg",
            type_=float,
            label="Spatial Tile Size (degrees)",
            description="Size of each geographic tile for split assignment (e.g., 1.0°×1.0°)",
            required=False,
            default=1.0,
            min_value=0.1,
            max_value=10.0,
            group="Split Settings",
        ),
        FieldSchema(
            name="image_format",
            type_=str,
            label="Output Image Format",
            description="Output format for organized imagery",
            required=False,
            default="png",
            choices=["png", "geotiff", "both"],
            widget_type="combo",
            group="Output Settings",
        ),
        FieldSchema(
            name="create_metadata_csv",
            type_=bool,
            label="Create Metadata CSV",
            description="Generate metadata CSV file with sample information",
            required=False,
            default=True,
            group="Output Settings",
        ),
    ],
)

# Schema registry for all components
COMPONENT_SCHEMAS: Dict[str, ComponentSchema] = {
    "hansen": HANSEN_SCHEMA,
    "aoi_sampler": AOI_SAMPLER_SCHEMA,
    "sample_extractor": SAMPLE_EXTRACTOR_SCHEMA,
    "imagery_downloader": IMAGERY_DOWNLOADER_SCHEMA,
    "dataset_organizer": DATASET_ORGANIZER_SCHEMA,
}


def get_schema(component_name: str) -> Optional[ComponentSchema]:
    """Get schema for a component by name."""
    return COMPONENT_SCHEMAS.get(component_name)


def list_schemas() -> List[str]:
    """List all available component schemas."""
    return list(COMPONENT_SCHEMAS.keys())
