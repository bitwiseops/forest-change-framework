# Testing Guide

This guide covers the comprehensive testing strategy for the Forest Change Framework, including unit tests, integration tests, and real-world validation scenarios.

## Overview

The framework includes a complete test suite with multiple testing levels:

- **Unit Tests**: Test individual classes and functions in isolation
- **Integration Tests**: Test component lifecycle and framework orchestration
- **Real-World Tests**: Test with actual data from sample extractors and imagery downloaders

### Test Statistics

```
Total Tests:        58
Pass Rate:          100%
Average Coverage:   87.5%
Execution Time:     ~1.5 seconds
```

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run tests with verbose output
pytest tests/ -v
```

### Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Dataset organizer tests
pytest tests/integration/test_dataset_organizer_*.py -v -s

# Core framework tests
pytest tests/unit/test_core/ -v
```

### Test Files Available

```
tests/
├── unit/
│   ├── test_core/
│   │   ├── test_registry.py
│   │   ├── test_base.py
│   │   ├── test_events.py
│   │   └── test_config.py
│   └── test_components/
│       ├── test_dataset_organizer_splitter.py (27 tests)
│       └── test_dataset_organizer_organizer.py (14 tests)
└── integration/
    ├── test_component_lifecycle.py
    ├── test_dataset_organizer_integration.py (11 tests)
    └── test_dataset_organizer_real_data.py (6 tests)
```

## Test Coverage

### Dataset Organizer Component

The dataset organizer component has comprehensive test coverage:

```
Module                      Coverage    Tests
─────────────────────────────────────────────
splitter.py                 100%        27
organizer.py                89%         14
component.py                84%         11
metadata_generator.py       77%         N/A
─────────────────────────────────────────────
Average                     87.5%       52
```

### Core Framework

```
Module                      Coverage
─────────────────────────────
registry.py                 56%
config.py                   41%
events.py                   61%
base.py                     50%
exceptions.py               100%
```

## Dataset Organizer Tests

The dataset organizer component includes 52 tests organized in 4 test files:

### 1. Unit Tests - Splitter Module (27 tests)

Tests for spatial tiling algorithm used to prevent geographic data leakage:

```python
# tests/unit/test_components/test_dataset_organizer_splitter.py

# SpatialTile Tests (6 tests)
- test_tile_initialization
- test_contains_bbox_center_inside
- test_contains_bbox_center_outside
- test_contains_bbox_boundary
- test_get_split_deterministic
- test_get_split_returns_valid_split

# SpatialTileGrid Tests (15 tests)
- test_initialization
- test_initialization_invalid_size
- test_get_tile_id_positive_coords
- test_get_tile_id_negative_coords
- test_get_tile_id_with_different_tile_sizes
- test_add_sample
- test_add_multiple_samples_same_tile
- test_add_samples_different_tiles
- test_generate_splits_basic
- test_generate_splits_invalid_percentages
- test_generate_splits_valid_percentages
- test_get_tile_assignments
- test_get_statistics
- test_get_statistics_empty_grid
- test_different_tile_sizes

# SplitValidator Tests (6 tests)
- test_validate_splits_valid
- test_validate_splits_empty
- test_validate_splits_with_tolerance
- test_validate_splits_invalid_percentages
- test_validate_splits_calculates_percentages
- test_validate_splits_reports_statistics
```

**Coverage**: 100% (all code paths covered)

### 2. Unit Tests - Organizer Module (14 tests)

Tests for dataset organization functionality:

```python
# tests/unit/test_components/test_dataset_organizer_organizer.py

- test_initialization_valid
- test_initialization_invalid_format
- test_create_split_directories
- test_create_sample_triplet_png
- test_create_sample_triplet_geotiff
- test_create_sample_triplet_both_formats
- test_create_sample_triplet_invalid_split
- test_create_sample_triplet_missing_imagery
- test_create_sample_triplet_missing_label
- test_get_triplet_structure
- test_validate_triplets_complete
- test_validate_triplets_incomplete
- test_validate_triplets_empty
- test_multiple_splits
```

**Coverage**: 89% (comprehensive file/directory operations)

### 3. Integration Tests - Mock Data (11 tests)

Tests using mock imagery and data:

```python
# tests/integration/test_dataset_organizer_integration.py

- test_component_initialization
- test_component_execution
- test_output_directory_structure
- test_metadata_csv_generation
- test_validation_report
- test_event_publishing
- test_configuration_validation_missing_imagery_dir
- test_configuration_validation_invalid_percentages
- test_different_image_formats
- test_spatial_split_distribution
- test_minimal_dataset_organization
```

**Coverage**: 84% (component lifecycle and configuration)

### 4. Real-World Tests - Actual Data (6 tests)

Tests using actual sample_extractor output (80 samples):

```python
# tests/integration/test_dataset_organizer_real_data.py

- test_organize_real_samples_end_to_end
- test_real_samples_split_distribution
- test_real_samples_metadata_csv
- test_real_samples_triplet_validation
- test_real_samples_directory_structure
- test_real_samples_with_events
- test_organize_all_available_samples (optional stress test)
```

**Input Data**: 20 samples from 80 available patches
**Output Statistics**:
- Train: 18 samples (60%)
- Val: 5 samples (16.7%)
- Test: 7 samples (23.3%)

## Writing Tests for Your Components

### Test Structure

Use this template for your component tests:

```python
import pytest
from forest_change_framework import BaseFramework
from forest_change_framework.core import get_registry

# Import your component to trigger registration
from forest_change_framework.components.export.my_component import MyComponent

class TestMyComponent:
    """Tests for MyComponent."""

    @pytest.fixture
    def component(self, framework):
        """Create component instance."""
        registry = get_registry()
        ComponentClass = registry.get("export", "my_component")
        return ComponentClass(framework.event_bus, {})

    def test_initialization(self, component):
        """Test component initialization."""
        assert component.name == "my_component"
        assert component.version == "1.0.0"

    def test_execution(self, framework, component, tmp_path):
        """Test component execution."""
        config = {
            "output_dir": str(tmp_path),
        }
        component.initialize(config)
        result = component.execute()

        assert result["status"] == "success"
        assert (tmp_path / "output.txt").exists()
```

### Testing Best Practices

1. **Use Fixtures**: Leverage pytest fixtures for test data setup
2. **Isolate Tests**: Each test should be independent
3. **Clear Assertions**: Use descriptive assertion messages
4. **Mock External Dependencies**: Mock API calls, database operations
5. **Test Edge Cases**: Test error conditions and boundary cases
6. **Use Real Data**: Include integration tests with actual data
7. **Document Tests**: Write clear docstrings explaining test purpose

### Fixtures Available

The framework provides useful fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def framework():
    """Create BaseFramework instance with clean registry."""

@pytest.fixture
def event_collector():
    """Collect events during test execution."""

@pytest.fixture
def clean_registry():
    """Isolated component registry."""
```

## Continuous Integration

### Running Tests in CI/CD

```yaml
# Example GitHub Actions workflow
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          make test-cov
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Performance Testing

### Coverage Reports

```bash
# Generate HTML coverage report
make test-cov

# View coverage report
open htmlcov/index.html
```

### Benchmarking

```python
import pytest

@pytest.mark.benchmark
def test_component_performance(benchmark, component):
    """Benchmark component execution time."""
    result = benchmark(component.execute)
    assert result["status"] == "success"

# Run benchmarks
pytest tests/ -m benchmark
```

## Troubleshooting Tests

### Test Failures

**Problem**: Tests fail with "Component not found"
- **Solution**: Ensure component module is imported before registry query

```python
# Correct
from forest_change_framework.components.export.my_component import MyComponent
registry = get_registry()
ComponentClass = registry.get("export", "my_component")

# Incorrect
registry = get_registry()
ComponentClass = registry.get("export", "my_component")  # Will fail
```

**Problem**: Tests fail with "Sample data not found"
- **Solution**: Ensure test data exists or skip gracefully

```python
@pytest.fixture
def real_sample_metadata():
    metadata_file = Path("/data/sample_extractor_output/samples_metadata.json")
    if not metadata_file.exists():
        pytest.skip("Sample extractor output not found")
    # ...
```

**Problem**: Slow test execution
- **Solution**: Mark slow tests and run separately

```python
@pytest.mark.slow
def test_organize_all_available_samples():
    # This test uses all 80 samples
    pass

# Run fast tests only
pytest tests/ -m "not slow"
```

### Debugging Tests

```bash
# Run with verbose output
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Drop into debugger on failure
pytest tests/ --pdb

# Run only failed tests
pytest tests/ --lf

# Run with coverage and show missing lines
pytest tests/ --cov=src/forest_change_framework --cov-report=term-missing
```

## Test Data

### Sample Data Locations

```
/home/bitwise/Projects/forest-change-framework/
├── data/
│   └── sample_extractor_output/
│       ├── patches/ (80 GeoTIFF files)
│       ├── samples.geojson
│       ├── samples_metadata.json
│       └── samples_metadata.csv
```

### Using Real Data in Tests

```python
import json
from pathlib import Path

SAMPLE_DATA = Path("/data/sample_extractor_output")

@pytest.fixture
def real_samples():
    """Load real sample metadata."""
    with open(SAMPLE_DATA / "samples_metadata.json") as f:
        return json.load(f)

def test_with_real_data(real_samples):
    """Test using real sample data."""
    samples = real_samples.get("samples", [])
    assert len(samples) == 80  # Expected count
```

## Documentation

For more information:
- [Component Testing Examples](../tests/integration/test_dataset_organizer_real_data.py)
- [Pytest Documentation](https://docs.pytest.org/)
- [Architecture Documentation](architecture.md)
- [Component Categories](component-categories.md)

## Contributing Tests

When contributing a new component:

1. **Write unit tests** for all public methods
2. **Write integration tests** with mock data
3. **Write real-world tests** if possible
4. **Aim for >80% coverage**
5. **Include docstrings** explaining test purpose
6. **Document test data** requirements
7. **Update this guide** with new test information

---

**Last Updated**: November 2024
**Testing Version**: 1.0
