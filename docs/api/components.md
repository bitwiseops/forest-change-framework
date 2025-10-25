# Component API Reference

Complete API reference for component interfaces.

## BaseComponent

Abstract base class that all components must inherit from.

```python
from forest_change_framework.interfaces import BaseComponent
from forest_change_framework import register_component

@register_component("category", "name")
class MyComponent(BaseComponent):
    pass
```

### Constructor

```python
def __init__(self, event_bus: EventBus, config: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `event_bus`: Reference to the central event bus
- `config`: Component configuration dictionary

**Example:**
```python
def __init__(self, event_bus, config=None):
    super().__init__(event_bus, config)
    self._initialized = False
```

### Abstract Methods

All of these MUST be implemented:

#### `initialize(config: Dict[str, Any]) -> None`
Initialize component with configuration.

Called after instantiation to set up resources and validate configuration.

**Parameters:**
- `config`: Component configuration dictionary

**Raises:**
- Exception: For configuration errors

**Example:**
```python
def initialize(self, config: Dict[str, Any]) -> None:
    self._config = config
    self.threshold = config.get("threshold")

    if self.threshold is None:
        raise ValueError("threshold is required")

    if not 0 <= self.threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
```

#### `execute(*args: Any, **kwargs: Any) -> Any`
Execute the component's core functionality.

This is called to perform the actual work.

**Parameters:**
- `*args`: Positional arguments specific to component
- `**kwargs`: Keyword arguments specific to component

**Returns:**
- Component-specific result

**Raises:**
- Exception: For runtime errors

**Example:**
```python
def execute(self, data, threshold=None):
    if threshold is None:
        threshold = self.threshold

    filtered = [x for x in data if x > threshold]

    self.publish_event("filter.complete", {
        "input_count": len(data),
        "output_count": len(filtered)
    })

    return filtered
```

#### `cleanup() -> None`
Clean up component resources.

Called after execution regardless of success or failure.

**Example:**
```python
def cleanup(self) -> None:
    if hasattr(self, '_connection'):
        self._connection.close()

    if hasattr(self, '_temp_files'):
        for f in self._temp_files:
            os.remove(f)
```

### Abstract Properties

#### `name -> str`
Get the component name (unique within category).

**Returns:**
- String identifier

**Example:**
```python
@property
def name(self) -> str:
    return "my_component"
```

#### `version -> str`
Get the component version.

**Returns:**
- Semantic version string (e.g., "1.0.0")

**Example:**
```python
@property
def version(self) -> str:
    return "2.1.0"
```

### Provided Methods

These are already implemented and available:

#### `publish_event(event_name: str, event_data: Any = None) -> None`
Publish an event through the framework event bus.

**Parameters:**
- `event_name`: Name of event to publish
- `event_data`: Optional data to include

**Example:**
```python
self.publish_event("component.started", {"source": "file.csv"})
# ... do work ...
self.publish_event("component.complete", {
    "records_processed": 1000,
    "time_seconds": 5.2
})
```

#### `subscribe_event(event_name: str, callback: Any) -> None`
Subscribe to an event through the event bus.

Allows component to react to events from other components.

**Parameters:**
- `event_name`: Event to subscribe to
- `callback`: Callable receiving (event_name, event_data)

**Example:**
```python
def __init__(self, event_bus, config=None):
    super().__init__(event_bus, config)
    self.subscribe_event("data.ready", self.on_data_ready)

def on_data_ready(self, event_name, data):
    print(f"Received data: {data}")
```

#### `get_config(key: str, default: Any = None) -> Any`
Get configuration value using dot notation.

**Parameters:**
- `key`: Configuration key (dot notation for nested)
- `default`: Default value if not found

**Returns:**
- Configuration value or default

**Example:**
```python
def initialize(self, config):
    self._config = config

def execute(self):
    output_path = self.get_config("output.path", "/tmp/output")
    timeout = self.get_config("timeout", 300)
```

## BasePlugin

Abstract base class for optional plugin functionality.

```python
from forest_change_framework.interfaces import BasePlugin

class MyPlugin(BasePlugin):
    pass
```

### Constructor

```python
def __init__(self, name: str, version: str = "1.0.0")
```

**Parameters:**
- `name`: Plugin name
- `version`: Plugin version

### Abstract Methods

#### `load(config: Optional[Dict[str, Any]] = None) -> None`
Load and initialize the plugin.

Called when plugin is being loaded into the framework.

**Parameters:**
- `config`: Optional plugin configuration

**Example:**
```python
def load(self, config):
    self.api_key = config.get("api_key") if config else None
    self.client = SomeAPIClient(api_key=self.api_key)
    print(f"{self.name} loaded successfully")
```

#### `unload() -> None`
Unload and clean up the plugin.

Called when plugin is being removed from the framework.

**Example:**
```python
def unload(self):
    if hasattr(self, 'client'):
        self.client.close()
    print(f"{self.name} unloaded")
```

### Optional Hooks

#### `on_enable() -> None`
Hook called when plugin is enabled.

Override if needed.

```python
def on_enable(self):
    logger.info(f"{self.name} is now active")
```

#### `on_disable() -> None`
Hook called when plugin is disabled.

Override if needed.

```python
def on_disable(self):
    logger.info(f"{self.name} is now inactive")
```

### Provided Methods

#### `get_info() -> Dict[str, Any]`
Get plugin metadata.

**Returns:**
- Dictionary with name, version, description

```python
info = plugin.get_info()
# {'name': 'my_plugin', 'version': '1.0.0', 'description': '...'}
```

## BaseMiddleware

Abstract base class for middleware components.

Middleware provides cross-cutting concerns that apply to multiple components.

```python
from forest_change_framework.interfaces import BaseMiddleware

class MyMiddleware(BaseMiddleware):
    pass
```

### Constructor

```python
def __init__(self, name: str)
```

**Parameters:**
- `name`: Middleware name

### Abstract Methods

#### `before(component_name: str, *args: Any, **kwargs: Any) -> None`
Hook called before component execution.

**Parameters:**
- `component_name`: Name of component about to execute
- `*args`: Arguments passed to component
- `**kwargs`: Keyword arguments passed to component

**Raises:**
- Exception: To prevent component execution

**Example:**
```python
def before(self, component_name, *args, **kwargs):
    logger.info(f"Executing {component_name}")
    logger.debug(f"Arguments: {args}, {kwargs}")
```

#### `after(component_name: str, result: Any, error: Optional[Exception] = None) -> Any`
Hook called after component execution.

**Parameters:**
- `component_name`: Name of component that executed
- `result`: Component result (None if error)
- `error`: Exception if component failed (None if successful)

**Returns:**
- Transformed result (or original result)

**Example:**
```python
def after(self, component_name, result, error=None):
    if error:
        logger.error(f"{component_name} failed: {error}")
        return None

    logger.info(f"{component_name} succeeded")
    return result
```

### Provided Methods

#### `get_info() -> Dict[str, Any]`
Get middleware metadata.

**Returns:**
- Dictionary with middleware info

## Complete Example

```python
from forest_change_framework.interfaces import BaseComponent
from forest_change_framework.core import register_component
from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


@register_component(
    category="preprocessing",
    name="outlier_remover",
    version="1.0.0",
    description="Removes outliers from numerical data",
    metadata={
        "author": "Flavio Cordari",
        "algorithm": "IQR",
    }
)
class OutlierRemover(BaseComponent):
    """Remove outliers using Interquartile Range method."""

    def __init__(self, event_bus: Any, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(event_bus, config)
        self._iqr_multiplier = 1.5
        self._columns = []

    @property
    def name(self) -> str:
        return "outlier_remover"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        self._config = config
        self._columns = config.get("columns", [])
        self._iqr_multiplier = config.get("iqr_multiplier", 1.5)

        if not self._columns:
            raise ValueError("columns configuration is required")

        if not isinstance(self._columns, list):
            raise ValueError("columns must be a list")

        logger.info(
            f"OutlierRemover initialized for columns: {self._columns}"
        )

    def execute(self, data: List[Dict[str, Any]], *args, **kwargs) -> List[Dict[str, Any]]:
        """Remove outliers from data."""
        logger.debug(f"Processing {len(data)} records")

        self.publish_event("outlier_remover.start", {
            "record_count": len(data),
            "columns": self._columns
        })

        try:
            cleaned = self._remove_outliers(data)

            self.publish_event("outlier_remover.complete", {
                "input_records": len(data),
                "output_records": len(cleaned),
                "records_removed": len(data) - len(cleaned),
                "percentage_removed": (len(data) - len(cleaned)) / len(data) * 100
            })

            return cleaned

        except Exception as e:
            logger.error(f"Error removing outliers: {e}")
            self.publish_event("outlier_remover.error", {
                "error": str(e)
            })
            raise

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.debug("OutlierRemover cleanup")

    def _remove_outliers(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove outliers using IQR method."""
        cleaned = []

        for record in data:
            is_outlier = False

            for col in self._columns:
                value = float(record.get(col, 0))
                # Simplified IQR check (real implementation would compute quartiles)
                if not self._is_valid(value):
                    is_outlier = True
                    break

            if not is_outlier:
                cleaned.append(record)

        return cleaned

    def _is_valid(self, value: float) -> bool:
        """Check if value is within acceptable range."""
        return -1000 <= value <= 10000  # Simplified bounds
```

## Usage Example

```python
from forest_change_framework import BaseFramework

# Create component instance through framework
framework = BaseFramework()

component = framework.instantiate_component(
    "preprocessing",
    "outlier_remover",
    {"columns": ["ndvi", "elevation"], "iqr_multiplier": 2.0}
)

# Execute component
data = [
    {"ndvi": 0.5, "elevation": 1000},
    {"ndvi": 0.7, "elevation": 1200},
    {"ndvi": 999, "elevation": 1100},  # Outlier
]

cleaned = component.execute(data)
component.cleanup()
```

## See Also

- [Core API](core.md)
- [Component Development Guide](../components/README.md)
- [Architecture](../architecture.md)
