#!/usr/bin/env python3
"""Test component configuration forms.

This script demonstrates the auto-generated configuration forms
for components.
"""

from src.forest_change_framework.gui.schemas import (
    get_schema,
    list_schemas,
    AOI_SAMPLER_SCHEMA,
    SAMPLE_EXTRACTOR_SCHEMA,
)
from src.forest_change_framework.gui.forms import FormWidget

import json


def test_schema_loading():
    """Test loading schemas."""
    print("=" * 60)
    print("Testing Schema Loading")
    print("=" * 60)

    schemas = list_schemas()
    print(f"Available schemas: {schemas}")

    for schema_name in schemas:
        schema = get_schema(schema_name)
        if schema:
            print(f"\n{schema_name}:")
            print(f"  Category: {schema.category}")
            print(f"  Description: {schema.description}")
            print(f"  Fields: {len(schema.fields)}")
            for field in schema.fields:
                print(f"    - {field.name} ({field.type_.__name__}) [group: {field.group}]")


def test_aoi_sampler_schema():
    """Test AOI sampler schema."""
    print("\n" + "=" * 60)
    print("Testing AOI Sampler Schema")
    print("=" * 60)

    schema = get_schema("aoi_sampler")
    assert schema is not None, "AOI sampler schema not found"

    print(f"Component: {schema.component_name}")
    print(f"Category: {schema.category}")
    print(f"Fields:")

    for field in schema.fields:
        print(f"\n  {field.label} ({field.name})")
        print(f"    Type: {field.type_.__name__}")
        print(f"    Required: {field.required}")
        print(f"    Default: {field.default}")
        if field.choices:
            print(f"    Choices: {field.choices}")
        if field.description:
            print(f"    Description: {field.description}")
        print(f"    Group: {field.group}")


def test_sample_extractor_schema():
    """Test sample extractor schema."""
    print("\n" + "=" * 60)
    print("Testing Sample Extractor Schema")
    print("=" * 60)

    schema = get_schema("sample_extractor")
    assert schema is not None, "Sample extractor schema not found"

    print(f"Component: {schema.component_name}")
    print(f"Category: {schema.category}")

    # Group fields by group
    grouped = {}
    for field in schema.fields:
        if field.group not in grouped:
            grouped[field.group] = []
        grouped[field.group].append(field)

    print(f"Field groups: {list(grouped.keys())}")
    for group_name, fields in grouped.items():
        print(f"\n  {group_name}:")
        for field in fields:
            print(f"    - {field.label}")


def test_schema_json_serialization():
    """Test JSON serialization of schemas."""
    print("\n" + "=" * 60)
    print("Testing Schema JSON Serialization")
    print("=" * 60)

    schema = get_schema("hansen")
    if schema:
        schema_dict = schema.to_dict()
        json_str = json.dumps(schema_dict, indent=2, default=str)
        print("Hansen schema as JSON:")
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)


def test_form_config_extraction():
    """Test configuration extraction from form."""
    print("\n" + "=" * 60)
    print("Testing Form Configuration Extraction (Headless)")
    print("=" * 60)

    schema = get_schema("aoi_sampler")
    assert schema is not None, "AOI sampler schema not found"

    # Test with sample initial config
    initial_config = {
        "hansen_vrt": "/data/hansen.vrt",
        "grid_cell_size_km": 2.5,
        "min_validity_threshold": 75.0,
    }

    # Test that we can inspect the schema
    print("Sample initial config:", initial_config)

    # Check field retrieval
    field = schema.get_field("grid_cell_size_km")
    if field:
        print(f"\nFound field 'grid_cell_size_km':")
        print(f"  Label: {field.label}")
        print(f"  Type: {field.type_.__name__}")
        print(f"  Min: {field.min_value}, Max: {field.max_value}")


if __name__ == "__main__":
    test_schema_loading()
    test_aoi_sampler_schema()
    test_sample_extractor_schema()
    test_schema_json_serialization()
    test_form_config_extraction()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
