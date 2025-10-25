# Core API Reference

Complete API reference for core framework classes and functions.

## BaseFramework

The main framework orchestrator.

```python
from forest_change_framework import BaseFramework

framework = BaseFramework(config: Optional[Dict[str, Any]] = None)
```

### Methods

#### `__init__(config)`
Initialize the framework with optional configuration.

**Parameters:**
- `config` (dict, optional): Initial framework configuration

**Example:**
```python
framework = BaseFramework({
    "log_level": "DEBUG",
    "strict_mode": True
})
```

#### `get_component_class(category, name)`
Get a component class from the registry.

**Parameters:**
- `category` (str): Component category
- `name` (str): Component name

**Returns:**
- Component class

**Raises:**
- `FrameworkError`: If component not found

**Example:**
```python
ComponentClass = framework.get_component_class("analysis", "my_analyzer")
```

#### `instantiate_component(category, name, instance_config)`
Create and initialize a component instance.

**Parameters:**
- `category` (str): Component category
- `name` (str): Component name
- `instance_config` (dict, optional): Component configuration

**Returns:**
- Initialized component instance

**Raises:**
- `ComponentError`: If instantiation fails

**Example:**
```python
component = framework.instantiate_component(
    "data_ingestion",
    "csv_loader",
    {"input_path": "data.csv"}
)
```

#### `execute_component(category, name, *args, **kwargs)`
Execute a component from instantiation through cleanup.

**Parameters:**
- `category` (str): Component category
- `name` (str): Component name
- `*args`: Positional arguments for component
- `**kwargs`: Keyword arguments (config merged into first positional or kwargs)

**Returns:**
- Component execution result

**Raises:**
- `ComponentError`: If execution fails

**Example:**
```python
result = framework.execute_component(
    "analysis",
    "change_detector",
    data,
    threshold=0.7
)
```

#### `list_components(category)`
List registered components.

**Parameters:**
- `category` (str, optional): Filter by category

**Returns:**
- Dict mapping categories to component lists

**Example:**
```python
all_comps = framework.list_components()
analysis_comps = framework.list_components("analysis")
```

#### `get_component_info(category, name)`
Get metadata for a component.

**Parameters:**
- `category` (str): Component category
- `name` (str): Component name

**Returns:**
- Dictionary with component info

**Example:**
```python
info = framework.get_component_info("analysis", "detector")
print(info['version'], info['description'])
```

#### `subscribe_event(event_name, callback)`
Subscribe to a framework event.

**Parameters:**
- `event_name` (str): Event to subscribe to
- `callback` (callable): Callback function

**Example:**
```python
def on_complete(event_name, data):
    print(f"Event: {event_name}, Data: {data}")

framework.subscribe_event("detector.complete", on_complete)
```

#### `unsubscribe_event(event_name, callback)`
Unsubscribe from an event.

**Parameters:**
- `event_name` (str): Event name
- `callback` (callable): Callback to remove

#### `publish_event(event_name, event_data)`
Publish an event to the event bus.

**Parameters:**
- `event_name` (str): Event name
- `event_data` (any, optional): Event data

### Properties

#### `registry`
Access to the component registry.

```python
components = framework.registry.list_components()
```

#### `event_bus`
Access to the event bus.

```python
subscribers = framework.event_bus.get_subscribers("event.name")
```

#### `config`
Access to the framework configuration.

```python
value = framework.config.get("key.path")
```

## ComponentRegistry

Component registration and discovery system.

```python
from forest_change_framework import ComponentRegistry, get_registry

# Get global registry
registry = get_registry()

# Or create new instance
registry = ComponentRegistry()
```

### Methods

#### `register(component_class, name, category, version, description, metadata)`
Register a component.

**Parameters:**
- `component_class` (type): Component class
- `name` (str): Component name
- `category` (str): Component category
- `version` (str, optional): Version string (default: "1.0.0")
- `description` (str, optional): Description
- `metadata` (dict, optional): Additional metadata

**Example:**
```python
registry.register(
    MyComponent,
    "my_component",
    "analysis",
    version="2.0.0",
    description="My analyzer"
)
```

#### `get(category, name)`
Get a component class.

**Returns:**
- Component class

#### `get_info(category, name)`
Get component metadata.

**Returns:**
- Dictionary with component info

#### `list_components(category)`
List components by category.

**Parameters:**
- `category` (str, optional): Filter by category

**Returns:**
- Dict mapping categories to component lists

#### `list_categories()`
List all registered categories.

**Returns:**
- List of category names

#### `unregister(category, name)`
Unregister a component.

#### `clear()`
Clear all registered components (useful for testing).

## register_component Decorator

Register a component using a decorator.

```python
from forest_change_framework import register_component

@register_component(
    category="analysis",
    name="my_analyzer",
    version="1.0.0",
    description="My analyzer",
    metadata={"tags": ["analysis"]}
)
class MyAnalyzer(BaseComponent):
    pass
```

**Parameters:**
- `category` (str): Component category
- `name` (str, optional): Component name (defaults to snake_case class name)
- `version` (str, optional): Version (default: "1.0.0")
- `description` (str, optional): Component description
- `metadata` (dict, optional): Additional metadata

## ConfigManager

Configuration loading and management.

```python
from forest_change_framework import ConfigManager
```

### Factory Methods

#### `from_dict(config)`
Create from dictionary.

```python
config = ConfigManager.from_dict({"key": "value"})
```

#### `from_json(filepath)`
Load from JSON file.

```python
config = ConfigManager.from_json("config.json")
```

#### `from_yaml(filepath)`
Load from YAML file.

```python
config = ConfigManager.from_yaml("config.yaml")
```

### Methods

#### `get(key, default)`
Get configuration value using dot notation.

```python
db_host = config.get("database.host", "localhost")
```

#### `set(key, value)`
Set configuration value using dot notation.

```python
config.set("database.port", 5432)
```

#### `merge(other)`
Merge another configuration dictionary.

```python
config.merge({"new_key": "new_value"})
```

#### `to_dict()`
Get entire configuration as dictionary.

```python
all_config = config.to_dict()
```

#### `validate(schema)`
Validate against schema.

```python
schema = {"host": str, "port": int}
config.validate(schema)
```

## EventBus

Event publish/subscribe system.

```python
from forest_change_framework import EventBus

bus = EventBus()
```

### Methods

#### `subscribe(event_name, callback)`
Subscribe to an event.

```python
bus.subscribe("data.loaded", lambda name, data: print(data))
```

#### `unsubscribe(event_name, callback)`
Unsubscribe from an event.

#### `publish(event_name, event_data)`
Publish an event.

```python
bus.publish("data.loaded", {"records": 100})
```

#### `get_subscribers(event_name)`
Get list of subscribers for event.

```python
subscribers = bus.get_subscribers("event.name")
```

#### `clear()`
Clear all subscribers.

## Exceptions

### FrameworkError
Base exception for all framework errors.

### ComponentError
Component-related errors.

### RegistryError
Component registration/discovery errors.

### ConfigError
Configuration errors.

### ValidationError
Input validation errors.

### EventError
Event bus errors.

### PluginError
Plugin-related errors.

## Usage Example

```python
from forest_change_framework import (
    BaseFramework,
    register_component,
    ConfigManager
)
from forest_change_framework.interfaces import BaseComponent

# Define component
@register_component("analysis", "my_component")
class MyComponent(BaseComponent):
    @property
    def name(self) -> str:
        return "my_component"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict) -> None:
        pass

    def execute(self, data):
        return data

    def cleanup(self) -> None:
        pass

# Use framework
framework = BaseFramework()

# Subscribe to events
framework.subscribe_event("my_component.complete",
    lambda name, data: print(f"Done: {data}"))

# Execute component
result = framework.execute_component("analysis", "my_component", data)
```

## See Also

- [Components API](components.md)
- [Architecture](../architecture.md)
- [Getting Started](../getting-started.md)
