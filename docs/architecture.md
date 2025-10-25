# Architecture Documentation

## Overview

The Forest Change Framework is built on a modular, event-driven architecture that emphasizes loose coupling between components while maintaining clear dependencies and data flow.

## Core Principles

### 1. Modularity
- **Isolated Components**: Each component is self-contained and handles one responsibility
- **Pluggable Design**: Components can be added, removed, or replaced without modifying the framework
- **Category Organization**: Related components are organized into logical categories

### 2. Event-Driven Communication
- **Pub/Sub Pattern**: Components publish events and subscribe to events from others
- **Loose Coupling**: Components don't need to know about each other; they only know about the event bus
- **Asynchronous Flow**: Components can react to events independently

### 3. Configuration-Driven
- **External Configuration**: All parameters are externalized to configuration files
- **Flexibility**: Components can be reconfigured without code changes
- **Standards**: Supports JSON and YAML configuration formats

### 4. Auto-Discovery and Registration
- **Decorator-Based Registration**: Components self-register using `@register_component`
- **Automatic Discovery**: The registry maintains a catalog of all available components
- **Runtime Access**: Components can be instantiated on-demand

## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│           Forest Change Framework                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ BaseFramework (Orchestrator)                         │ │
│  │  - Component instantiation & lifecycle              │ │
│  │  - Configuration management                         │ │
│  │  - Event publishing/subscription                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                      ↓↑                                    │
│  ┌──────────────┬──────────────┬──────────────┐          │
│  │ Component    │ Event Bus    │ Config       │          │
│  │ Registry     │              │ Manager      │          │
│  └──────────────┴──────────────┴──────────────┘          │
│           ↓↑               ↓↑                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Components (Data Ingestion → Export Pipeline)     │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ ┌───────────┐ ┌─────────────┐ ┌──────────────┐    │  │
│  │ │Ingestion  │→│Preprocessing│→│ Analysis     │→...│  │
│  │ └───────────┘ └─────────────┘ └──────────────┘    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Utilities & Supporting Systems                      │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ Logger | Validators | Helpers | CLI                │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Component Lifecycle

Every component goes through a well-defined lifecycle:

```
┌─────────────┐
│ Registered  │  Component exists in registry
└──────┬──────┘
       │
       ↓
┌─────────────┐
│Instantiated │  Component instance created with event_bus and config
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Initialized │  initialize() called with configuration validation
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Executing  │  execute() called with input data
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Cleanup   │  cleanup() called to release resources
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Completed  │  Component lifecycle finished
└─────────────┘
```

## Component Registry System

The registry maintains a catalog of all available components:

```
ComponentRegistry
├── data_ingestion
│   ├── sample_component
│   │   ├── class: SampleComponent
│   │   ├── version: 1.0.0
│   │   ├── description: "..."
│   │   └── metadata: {...}
│   └── csv_loader
│       └── ...
├── preprocessing
│   ├── normalizer
│   └── ...
├── analysis
│   └── ...
└── visualization
    └── ...
```

### Registration Process

```python
@register_component(
    category="data_ingestion",
    name="sample_component",
    version="1.0.0",
    description="...",
    metadata={...}
)
class SampleComponent(BaseComponent):
    pass
```

1. Decorator intercepts class definition
2. Extracts metadata and component class
3. Calls `get_registry().register()`
4. Entry added to global registry
5. Component is now discoverable

## Event Bus Architecture

The event bus implements a publish/subscribe pattern:

```
┌─────────────────────────────────────────┐
│         Event Bus                       │
├─────────────────────────────────────────┤
│ _subscribers = {                        │
│   "event.name": [callback1, callback2], │
│   "other.event": [callback3],           │
│   ...                                   │
│ }                                       │
├─────────────────────────────────────────┤
│ Methods:                                │
│ - subscribe(event_name, callback)       │
│ - unsubscribe(event_name, callback)     │
│ - publish(event_name, event_data)       │
│ - get_subscribers(event_name)           │
│ - clear()                               │
└─────────────────────────────────────────┘
```

### Event Flow

```
Component A                EventBus              Component B
    │                        │                        │
    │─publish("data.ready")──│                        │
    │                        ├─notify subscribers─→   │
    │                        │                        │
    │                        │         on_data_ready()│
    │                        │                    │───┤
    │                        │                        │
```

## Configuration Management

The configuration system supports hierarchical, nested configurations:

```
ConfigManager
├── JSON/YAML Parser
├── Config Storage (dict)
└── Access Methods
    ├── get(key) - dot notation support
    ├── set(key, value)
    ├── merge(dict)
    ├── validate(schema)
    └── to_dict()
```

### Configuration Merging

```
base_config = {"db": {"host": "localhost", "port": 5432}}
override = {"db": {"port": 3306}}

merged = deep_merge(base_config, override)
# Result: {"db": {"host": "localhost", "port": 3306}}
```

## Interfaces and Contracts

### BaseComponent Interface

Every component must implement:

```python
class BaseComponent(ABC):
    def initialize(self, config: dict) -> None:
        """Setup and validate configuration"""

    def execute(self, *args, **kwargs) -> Any:
        """Perform component's core logic"""

    def cleanup(self) -> None:
        """Release resources"""

    @property
    def name(self) -> str:
        """Component identifier"""

    @property
    def version(self) -> str:
        """Semantic version"""
```

### BasePlugin Interface

For optional plugin functionality:

```python
class BasePlugin(ABC):
    def load(self, config: dict) -> None:
        """Initialize plugin"""

    def unload(self) -> None:
        """Cleanup plugin"""

    def on_enable(self) -> None:
        """Called when enabled"""

    def on_disable(self) -> None:
        """Called when disabled"""
```

### BaseMiddleware Interface

For cross-cutting concerns:

```python
class BaseMiddleware(ABC):
    def before(self, component_name: str, *args, **kwargs) -> None:
        """Before component execution"""

    def after(self, component_name: str, result: Any, error: Exception = None) -> Any:
        """After component execution"""
```

## Data Flow Patterns

### Sequential Pipeline

```
Data In → [Component A] → [Component B] → [Component C] → Results
           (events)      (events)        (events)
```

### Event-Driven Reactive

```
Event                 Component A              Component B
  │                        │                        │
  ├─data.loaded────────────│                        │
  │                    process()                     │
  │                        │                        │
  │                    publish event──────────────→ │
  │                                            process()
  │                                                 │
  │                                            publish event
```

### Parallel Components

```
Input Data
    │
    ├─→ [Component A] ──→ Event A
    │
    ├─→ [Component B] ──→ Event B
    │
    └─→ [Component C] ──→ Event C
```

## Dependency Management

Components should NOT have direct dependencies on each other:

```
❌ BAD - Direct dependency
class PreprocessComponent:
    def __init__(self):
        from components.analysis import MyAnalyzer
        self.analyzer = MyAnalyzer()  # Direct import!
```

```
✓ GOOD - Event-based communication
class PreprocessComponent:
    def execute(self, data):
        processed = self._process(data)
        self.publish_event("preprocessing.complete", {"data": processed})
        # Components interested in this event will react
```

## Error Handling Strategy

```
Component.execute()
    ↓
[Success] → publish event → cleanup() → return result
    ↓
[Error] → publish error event → cleanup() → raise exception
```

Each component should:
1. Validate inputs in `initialize()`
2. Handle expected errors in `execute()`
3. Always call `cleanup()` regardless of outcome
4. Publish error events for interested parties

## Logging Architecture

```
Framework Logger
├── Console Handler (INFO level)
├── File Handler (DEBUG level)
└── Rotation (10MB max, 5 backups)

Component Loggers
├── Named after module
├── Use standard logging API
└── Integrated with framework logging
```

## Scalability Considerations

### Current Design
- **Single-process**: Runs within a single Python process
- **Synchronous**: Components execute sequentially
- **In-memory**: Data passed between components via memory

### Future Extensions
- **Distributed Processing**: Distribute components across machines
- **Asynchronous Execution**: Non-blocking component execution
- **Message Queues**: Decouple components with message systems
- **Microservices**: Deploy components as services

## Extension Points

### 1. Custom Components
Add new components in category directories:
```
src/forest_change_framework/components/[category]/[component_name]/
```

### 2. Custom Plugins
Implement `BasePlugin` interface:
```python
class MyPlugin(BasePlugin):
    def load(self, config):
        pass
```

### 3. Custom Middleware
Implement `BaseMiddleware` interface:
```python
class MyMiddleware(BaseMiddleware):
    def before(self, name, *args, **kwargs):
        pass
```

### 4. Custom Validators
Add validation functions in `utils/validators.py`

### 5. CLI Extensions
Add commands in `cli/commands.py`

## Performance Characteristics

- **Component Registration**: O(1)
- **Component Discovery**: O(n) where n = number of categories
- **Component Instantiation**: O(1) after registration
- **Event Publishing**: O(n) where n = number of subscribers
- **Configuration Access**: O(depth) with dot notation

## Thread Safety

Current implementation is NOT thread-safe:
- Shared mutable state (registry, event bus)
- No locking mechanisms
- Single-threaded execution assumed

For multi-threaded use, wrap in thread locks or use multiprocessing.

## Testing Strategy

```
Unit Tests
├── Core functionality (registry, events, config)
├── Component interface compliance
├── Utility functions
└── Error handling

Integration Tests
├── Component lifecycle
├── Event flow
├── Pipeline execution
└── Configuration loading
```

## See Also

- [Component Categories](component-categories.md)
- [Getting Started](getting-started.md)
- [API Reference](api/)
