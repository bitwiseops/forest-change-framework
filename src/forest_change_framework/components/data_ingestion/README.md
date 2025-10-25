# Data Ingestion Components

Data ingestion components handle loading forest change data from various sources. These components are the entry point of the processing pipeline.

## Purpose

Data ingestion components are responsible for:
- Connecting to data sources (files, databases, APIs, cloud services)
- Reading and parsing data in various formats
- Validating data integrity
- Publishing standardized data for downstream components
- Handling connection errors and timeouts gracefully

## Creating a New Component

### 1. Component Structure

Create a new subdirectory for your component:

```
data_ingestion/
├── my_component/
│   ├── __init__.py
│   ├── component.py
│   └── README.md
└── sample_component/
    ├── __init__.py
    └── component.py
```

### 2. Naming Conventions

- **Directory name**: `snake_case_name` (e.g., `csv_loader`, `geotiff_reader`, `database_connector`)
- **Component name**: Matches directory name (passed to `@register_component` decorator)
- **Class name**: `PascalCase` version of component name (e.g., `CSVLoader`, `GeoTiffReader`, `DatabaseConnector`)
- **Module name**: `component.py` (unless you split into multiple files)

### 3. Interface Requirements

All data ingestion components MUST implement `BaseComponent`:

```python
from forest_change_framework.interfaces import BaseComponent

class MyComponent(BaseComponent):
    def initialize(self, config: dict) -> None:
        """Validate configuration and prepare resources."""
        pass

    def execute(self, *args, **kwargs) -> Any:
        """Load and return data."""
        pass

    def cleanup(self) -> None:
        """Release resources."""
        pass

    @property
    def name(self) -> str:
        """Return component name."""
        return "my_component"

    @property
    def version(self) -> str:
        """Return semantic version."""
        return "1.0.0"
```

### 4. Registration

Register your component using the `@register_component` decorator:

```python
from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

@register_component(
    category="data_ingestion",
    name="my_component",
    version="1.0.0",
    description="Brief description of what this component does",
    metadata={
        "author": "Flavio Cordari",
        "supported_formats": ["CSV", "GeoTIFF"],
        "tags": ["raster", "geospatial"],
    }
)
class MyComponent(BaseComponent):
    pass
```

### 5. Event Naming Conventions

Data ingestion components should publish events following this pattern:

- `{component_name}.start`: When starting to load data
- `{component_name}.progress`: During loading (with progress data)
- `{component_name}.complete`: When successfully loaded
- `{component_name}.error`: When an error occurs

Example:
```python
self.publish_event("my_component.start", {"source": "file.csv"})
self.publish_event("my_component.progress", {"loaded": 50, "total": 100})
self.publish_event("my_component.complete", {"records": 100, "size_mb": 5.2})
```

### 6. Configuration

Components should be fully configurable via configuration dictionaries. Required config keys should be validated in `initialize()`:

```python
def initialize(self, config: dict) -> None:
    self.input_path = config.get("input_path")
    self.encoding = config.get("encoding", "utf-8")

    if not self.input_path:
        raise ValueError("input_path is required")
```

### 7. Error Handling

Handle errors gracefully and provide meaningful error messages:

```python
try:
    # Your code
    pass
except FileNotFoundError as e:
    self.publish_event("my_component.error", {
        "error_type": "FileNotFoundError",
        "message": str(e),
        "file": self.input_path,
    })
    raise
```

## Minimal Component Template

```python
"""
My data ingestion component.

Brief description of what this component does.
"""

import logging
from typing import Any, Dict, Optional

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

logger = logging.getLogger(__name__)


@register_component(
    category="data_ingestion",
    name="my_component",
    version="1.0.0",
    description="Loads data from [source type]",
)
class MyComponent(BaseComponent):
    """
    My custom data ingestion component.

    Configuration:
        - source (str): Data source location/path
        - encoding (str): File encoding (default: utf-8)
    """

    def __init__(self, event_bus: Any, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(event_bus, config)
        self._data = None

    @property
    def name(self) -> str:
        return "my_component"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        if not self.get_config("source"):
            raise ValueError("'source' configuration is required")
        logger.info("Component initialized")

    def execute(self, *args, **kwargs) -> Any:
        source = self.get_config("source")
        logger.debug(f"Loading data from {source}")

        try:
            # Load your data here
            self._data = self._load_data(source)

            # Publish success event
            self.publish_event("my_component.complete", {
                "records": len(self._data) if isinstance(self._data, list) else 1,
            })

            return self._data
        except Exception as e:
            self.publish_event("my_component.error", {"error": str(e)})
            raise

    def cleanup(self) -> None:
        self._data = None
        logger.debug("Component cleaned up")

    def _load_data(self, source: str) -> Any:
        """Load data from source."""
        # TODO: Implement your data loading logic
        return []
```

## Best Practices

1. **Validate Early**: Check all required configuration in `initialize()`
2. **Log Thoroughly**: Use logging at DEBUG, INFO, and ERROR levels
3. **Publish Events**: Emit events so other components can react
4. **Handle Large Data**: Consider memory usage for large datasets
5. **Type Hints**: Use complete type hints for all public methods
6. **Docstrings**: Document configuration options and behavior
7. **Error Messages**: Provide clear, actionable error messages
8. **No Direct Dependencies**: Never import from other components in different categories

## Testing Your Component

Create a test file in `tests/unit/test_components/`:

```python
import pytest
from forest_change_framework import BaseFramework

def test_my_component_loads_data():
    framework = BaseFramework()
    component = framework.instantiate_component("data_ingestion", "my_component", {
        "source": "/path/to/data.csv"
    })
    result = component.execute()
    assert result is not None
    assert len(result) > 0
```

## See Also

- [Component Interface Documentation](../../docs/api/components.md)
- [Sample Component](sample_component/)
- [Framework Architecture](../../docs/architecture.md)
