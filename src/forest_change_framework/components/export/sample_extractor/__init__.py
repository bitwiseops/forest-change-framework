"""Sample Extractor Component - Extract TIFF patches from Hansen data based on stratified AOI samples."""

from .sampling import (
    group_aois_by_year_and_bin,
    select_stratified_samples,
    balance_samples_across_years,
    create_sample_manifest,
)
from .extraction import (
    extract_patch_from_vrt,
    extract_patch_from_tiles,
    save_geotiff,
    calculate_geotransform,
)
from .metadata import (
    create_metadata_dict,
    write_metadata_csv,
    write_metadata_json,
    validate_metadata,
)
from .component import SampleExtractorComponent

__all__ = [
    "SampleExtractorComponent",
    "group_aois_by_year_and_bin",
    "select_stratified_samples",
    "balance_samples_across_years",
    "create_sample_manifest",
    "extract_patch_from_vrt",
    "extract_patch_from_tiles",
    "save_geotiff",
    "calculate_geotransform",
    "create_metadata_dict",
    "write_metadata_csv",
    "write_metadata_json",
    "validate_metadata",
]
