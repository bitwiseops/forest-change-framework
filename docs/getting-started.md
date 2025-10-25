# Getting Started Guide

This guide walks you through setting up and using the Forest Change Framework for the first time.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or conda package manager

### Step 1: Install the Framework

```bash
# Clone the repository
git clone https://github.com/bitwiseops/forest-change-framework.git
cd forest-change-framework

# Install in editable mode (for development)
pip install -e .

# Or install with all development tools
pip install -e ".[dev]"
```

### Step 2: Verify Installation

```bash
# Check that the CLI is available
forest-change-framework --help

# List installed components
forest-change-framework list-components
```

## Creating Your First Project

### Step 1: Initialize a Project

```bash
forest-change-framework init --name my_forest_project
cd my_forest_project
```

This creates:
```
my_forest_project/
├── config/
│   └── config.json
├── data/
└── output/
```

### Step 2: Prepare Sample Data

Create a sample CSV file at `data/sample.csv`:

```csv
date,latitude,longitude,ndvi,forest_cover
2020-01-15,45.123,-122.456,0.78,0.95
2020-02-20,45.124,-122.457,0.72,0.92
2020-03-18,45.125,-122.458,0.81,0.96
2020-04-22,45.126,-122.459,0.75,0.88
2020-05-19,45.127,-122.460,0.85,0.98
```

## Basic Usage

### Method 1: Using the CLI

```bash
# Run the sample component
forest-change-framework run data_ingestion sample_component \
  --config config/config.json
```

### Method 2: Programmatic Usage

Create a Python script `run_workflow.py`:

```python
from forest_change_framework import BaseFramework

# Initialize framework
framework = BaseFramework()

# Configure the component
config = {
    "input_path": "data/sample.csv",
    "delimiter": ",",
    "encoding": "utf-8"
}

# Execute component
print("Loading data...")
data = framework.execute_component(
    category="data_ingestion",
    name="sample_component",
    **config
)

print(f"Successfully loaded {len(data)} records")
for record in data[:3]:
    print(f"  - {record}")
```

Run it:
```bash
python run_workflow.py
```

## Working with Events

Components communicate through an event system. You can subscribe to component events:

Create `event_example.py`:

```python
from forest_change_framework import BaseFramework

def on_data_loaded(event_name, event_data):
    print(f"✓ Event received: {event_name}")
    print(f"  - Records: {event_data.get('record_count')}")
    print(f"  - Status: {event_data.get('status')}")

# Setup framework and events
framework = BaseFramework()
framework.subscribe_event("sample.complete", on_data_loaded)
framework.subscribe_event("sample.error", lambda name, data:
    print(f"✗ Error: {data.get('error')}"))

# Execute component
config = {"input_path": "data/sample.csv"}
result = framework.execute_component(
    "data_ingestion",
    "sample_component",
    **config
)
```

Run it:
```bash
python event_example.py
```

## Creating Your First Component

### Step 1: Create Component Directory

```bash
mkdir -p src/forest_change_framework/components/analysis/simple_filter
touch src/forest_change_framework/components/analysis/simple_filter/__init__.py
touch src/forest_change_framework/components/analysis/simple_filter/component.py
```

### Step 2: Implement the Component

Edit `src/forest_change_framework/components/analysis/simple_filter/component.py`:

```python
"""
Simple filter component that filters records based on a threshold.
"""

import logging
from typing import Any, Dict, List, Optional

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

logger = logging.getLogger(__name__)


@register_component(
    category="analysis",
    name="simple_filter",
    version="1.0.0",
    description="Filters records based on NDVI threshold"
)
class SimpleFilter(BaseComponent):
    """Filter records by NDVI value."""

    @property
    def name(self) -> str:
        return "simple_filter"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with threshold configuration."""
        self._config = config
        self.threshold = config.get("threshold", 0.7)
        logger.info(f"SimpleFilter initialized with threshold: {self.threshold}")

    def execute(self, data: List[Dict[str, Any]], *args, **kwargs) -> List[Dict[str, Any]]:
        """Filter records where NDVI exceeds threshold."""
        logger.debug(f"Filtering {len(data)} records")

        filtered = [
            record for record in data
            if float(record.get("ndvi", 0)) >= self.threshold
        ]

        self.publish_event("simple_filter.complete", {
            "input_count": len(data),
            "output_count": len(filtered),
            "threshold": self.threshold,
        })

        return filtered

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.debug("SimpleFilter cleaned up")
```

### Step 3: Update Component Module

Edit `src/forest_change_framework/components/analysis/simple_filter/__init__.py`:

```python
"""Simple filter component."""

from .component import SimpleFilter

__all__ = ["SimpleFilter"]
```

### Step 4: Use Your Component

Create `use_custom_component.py`:

```python
from forest_change_framework import BaseFramework

# Initialize framework
framework = BaseFramework()

# Load sample data
data_config = {"input_path": "data/sample.csv"}
data = framework.execute_component(
    "data_ingestion",
    "sample_component",
    **data_config
)

print(f"Loaded {len(data)} records")

# Filter data using our custom component
filter_config = {"threshold": 0.75}
filtered = framework.execute_component(
    "analysis",
    "simple_filter",
    data,
    **filter_config
)

print(f"Filtered to {len(filtered)} records (NDVI >= 0.75)")
```

Run it:
```bash
python use_custom_component.py
```

## Configuration Files

### JSON Configuration

Create `config.json`:

```json
{
  "data_ingestion": {
    "input_path": "data/sample.csv",
    "delimiter": ",",
    "encoding": "utf-8",
    "skip_errors": false
  },
  "analysis": {
    "threshold": 0.75,
    "method": "ndvi"
  },
  "output": {
    "format": "csv",
    "path": "output/results.csv"
  }
}
```

Use it:
```python
from forest_change_framework import ConfigManager

config = ConfigManager.from_json("config.json")
data_config = config.get("data_ingestion")
```

### YAML Configuration

Create `config.yaml`:

```yaml
data_ingestion:
  input_path: data/sample.csv
  delimiter: ","
  encoding: utf-8
  skip_errors: false

analysis:
  threshold: 0.75
  method: ndvi

output:
  format: csv
  path: output/results.csv
```

Use it:
```python
from forest_change_framework import ConfigManager

config = ConfigManager.from_yaml("config.yaml")
data_config = config.get("data_ingestion")
```

## Building a Complete Pipeline

Create `pipeline_example.py` that chains multiple components:

```python
from forest_change_framework import BaseFramework, setup_logging

# Setup logging
logger = setup_logging(__name__)

def pipeline():
    """Run a complete analysis pipeline."""
    framework = BaseFramework()

    # Subscribe to events
    def on_complete(event_name, data):
        print(f"✓ {event_name}: {data}")

    framework.subscribe_event("sample.complete", on_complete)
    framework.subscribe_event("simple_filter.complete", on_complete)

    # Step 1: Load data
    print("Step 1: Loading data...")
    data = framework.execute_component(
        "data_ingestion",
        "sample_component",
        input_path="data/sample.csv"
    )
    print(f"  Loaded {len(data)} records\n")

    # Step 2: Filter data
    print("Step 2: Filtering data...")
    filtered = framework.execute_component(
        "analysis",
        "simple_filter",
        data,
        threshold=0.75
    )
    print(f"  Filtered to {len(filtered)} records\n")

    # Step 3: Export results (if export component available)
    print("Pipeline complete!")
    return filtered

if __name__ == "__main__":
    results = pipeline()
```

Run it:
```bash
python pipeline_example.py
```

## Next Steps

1. **Read the [Architecture Documentation](architecture.md)** to understand the framework design
2. **Explore [Component Categories](component-categories.md)** to learn about each type
3. **Review [Examples](../examples/)** for more complex workflows
4. **Check the [API Documentation](api/)** for complete reference

## Troubleshooting

### Component Not Found

```
RegistryError: Component 'my_component' not found in category 'analysis'
```

**Solution**: Make sure your component is properly registered with `@register_component` decorator and the module is imported.

### Configuration Errors

```
ConfigError: Configuration file not found: config.json
```

**Solution**: Check that the file path is correct and relative to your current working directory.

### Import Errors

```
ModuleNotFoundError: No module named 'forest_change_framework'
```

**Solution**: Install the package in editable mode: `pip install -e .`

## Getting Help

- Check the [documentation](../docs/)
- Look at [examples](../examples/)
- Open an [issue on GitHub](https://github.com/bitwiseops/forest-change-framework/issues)
