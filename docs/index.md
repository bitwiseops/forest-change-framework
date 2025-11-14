# Forest Change Framework Documentation

Welcome to the Forest Change Framework documentation! This guide will help you get started with building modular, extensible forest change detection workflows.

## Quick Navigation

### Getting Started
- **[Getting Started Guide](getting-started.md)** - Step-by-step tutorial to install and run your first workflow
- **[Installation](../README.md#installation)** - Detailed installation instructions

### Understanding the Framework
- **[Architecture Documentation](architecture.md)** - Deep dive into the framework design and principles
- **[Component Categories](component-categories.md)** - Guide to the 5 component categories and when to use them

### Development
- **[Core API Reference](api/core.md)** - Complete API documentation for core framework classes
- **[Component API Reference](api/components.md)** - Guide to creating components and using interfaces

### Testing
- **[Testing Guide](testing.md)** - Comprehensive testing documentation
- **[Running Tests](#running-tests)** - Instructions for running the test suite
- **[Dataset Organizer Tests](#dataset-organizer-tests)** - Real-world test examples

### Examples
- **[Basic Usage](../examples/basic_usage.py)** - Simple example to get started
- **[Pipeline Example](../examples/pipeline_example.py)** - Multi-component workflow
- **[Custom Component Template](../examples/custom_component/example_component.py)** - Complete component template
- **[Plugin Example](../examples/plugin_example/my_plugin.py)** - Plugin development example

## Key Concepts

### Components
Self-contained units that perform specific tasks in the pipeline. Components are:
- **Modular**: Each component does one thing well
- **Configurable**: All parameters externalized to configuration
- **Discoverable**: Auto-registered via decorators
- **Reusable**: Use the same component in multiple workflows

### Event Bus
A pub/sub messaging system that allows components to communicate without direct dependencies:
- Components publish events when they complete work
- Other components subscribe to events
- Enables loose coupling and flexible workflows

### Registry
Automatically maintains a catalog of all available components:
- Components self-register using `@register_component` decorator
- Enables runtime discovery and instantiation
- Supports organizing components by category

### Categories
Components are organized into 5 logical categories:

1. **Data Ingestion** - Load data from various sources
2. **Preprocessing** - Clean and transform data
3. **Analysis** - Detect forest changes
4. **Visualization** - Render and display results
5. **Export** - Save results to various formats

## Typical Workflow

```
Data Ingestion
    ↓
  (event: data.loaded)
    ↓
Preprocessing
    ↓
  (event: data.processed)
    ↓
Analysis
    ↓
  (event: analysis.complete)
    ↓
Visualization
    ↓
  (event: visualization.complete)
    ↓
Export
```

## Installation

```bash
git clone https://github.com/bitwiseops/forest-change-framework.git
cd forest-change-framework

# Install in editable mode
pip install -e .

# Or install with development tools
pip install -e ".[dev]"
```

## Your First Component

Create a new component in 3 steps:

### 1. Create Component File
```python
from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

@register_component(
    category="analysis",
    name="my_analyzer",
    description="My custom forest analyzer"
)
class MyAnalyzer(BaseComponent):
    # Implement abstract methods
    pass
```

### 2. Implement Required Methods
```python
def initialize(self, config):
    """Setup with configuration"""
    pass

def execute(self, data):
    """Perform analysis"""
    return results

def cleanup(self):
    """Release resources"""
    pass

@property
def name(self):
    return "my_analyzer"

@property
def version(self):
    return "1.0.0"
```

### 3. Use Your Component
```python
from forest_change_framework import BaseFramework

framework = BaseFramework()
result = framework.execute_component(
    "analysis",
    "my_analyzer",
    data
)
```

For detailed guide, see [Getting Started](getting-started.md).

## Common Tasks

### List Available Components
```bash
forest-change-framework list-components
```

### Run a Component
```bash
forest-change-framework run analysis my_analyzer --config config.json
```

### Validate Configuration
```bash
forest-change-framework validate config.json
```

### Get Component Information
```bash
forest-change-framework info analysis my_analyzer
```

## Project Structure

```
forest-change-framework/
├── src/forest_change_framework/       # Main source code
│   ├── core/                          # Core framework classes
│   ├── interfaces/                    # Component interfaces
│   ├── components/                    # Component implementations
│   ├── utils/                         # Utilities and helpers
│   └── cli/                           # Command-line interface
├── tests/                             # Test suite
├── examples/                          # Example code
├── docs/                              # This documentation
└── README.md                          # Project overview
```

## Component Development Guide

For detailed information on developing components, see:
- [Component Categories](component-categories.md) - When to use each category
- [Component API Reference](api/components.md) - Interface specifications
- [Custom Component Example](../examples/custom_component/example_component.py) - Complete template

## API Documentation

### Core Framework
- [BaseFramework](api/core.md#baseframework) - Main orchestrator
- [ComponentRegistry](api/core.md#componentregistry) - Component management
- [ConfigManager](api/core.md#configmanager) - Configuration management
- [EventBus](api/core.md#eventbus) - Event pub/sub system

### Component Interfaces
- [BaseComponent](api/components.md#basecomponent) - Component base class
- [BasePlugin](api/components.md#baseplugin) - Plugin interface
- [BaseMiddleware](api/components.md#basemiddleware) - Middleware interface

## Running Tests

The framework includes a comprehensive test suite covering unit tests, integration tests, and real-world scenarios:

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test file
pytest tests/unit/test_core/test_registry.py -v

# Run dataset organizer tests
pytest tests/integration/test_dataset_organizer_real_data.py -v -s
```

See [Testing Guide](testing.md) for more details.

## Dataset Organizer Tests

The dataset organizer component includes comprehensive tests with real data:

- **58 Total Tests** - All passing
- **87.5% Average Coverage** - Across all modules
- **Real Data Tests** - Using actual sample_extractor output (80 samples)
- **Geographic Split Validation** - Verifies spatial distribution correctness

### Key Test Statistics
- Splitter module: **100% coverage** (27 tests)
- Organizer module: **89% coverage** (14 tests)
- Component integration: **84% coverage** (11 tests)
- Real-world scenarios: **6 tests** with actual data

For examples, see `tests/integration/test_dataset_organizer_real_data.py`.

## Troubleshooting

### Component not found
- Verify component is registered with `@register_component` decorator
- Check that the module is imported
- Use `list-components` to verify registration

### Configuration errors
- Ensure config file path is correct
- Use `validate` command to check config format
- Check configuration schema for required keys

### Import errors
- Ensure package is installed in editable mode: `pip install -e .`
- Check that all dependencies are installed: `pip install -r requirements.txt`

### Test failures
- Check that test data exists (e.g., `/data/sample_extractor_output/`)
- Verify dependencies are installed: `pip install -e ".[dev]"`
- Run with verbose output: `pytest -vv` to see detailed error messages

## Contributing

Contributions are welcome! Please see [Contributing Guidelines](../README.md#contributing).

## Support

- Check the [FAQs](getting-started.md#troubleshooting)
- Review [Architecture Documentation](architecture.md) for design questions
- Open an issue on [GitHub](https://github.com/bitwiseops/forest-change-framework/issues)

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) for details.

## Acknowledgments

Built with Python best practices, inspired by Apache Airflow, Django, and plugin architecture patterns.

---

**Last Updated**: November 2024
**Documentation Version**: 1.1
**Dataset Organizer Tests**: Added comprehensive test suite (58 tests, 87.5% coverage)
