# Forest Change Framework

A modular, extensible Python framework for forest change detection and analysis. Build sophisticated forest monitoring workflows by composing independent, reusable components.

## Key Features

- **Modular Architecture**: Components are independent and pluggable
- **Event-Driven Communication**: Components communicate via pub/sub events, enabling loose coupling
- **Configuration-Driven**: All components fully configurable via JSON/YAML
- **Auto-Discovery**: Components self-register using simple decorators
- **Extensible Design**: Easy to add new components, plugins, and middleware
- **Production-Ready**: Comprehensive error handling, logging, and validation
- **CLI Tools**: Command-line interface for project management and component execution
- **Well-Tested**: High code coverage with unit and integration tests

## Installation

### From Source

```bash
git clone https://github.com/bitwiseops/forest-change-framework.git
cd forest-change-framework

# Install in editable mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### From Package (when available)

```bash
pip install forest-change-framework
```

## Quick Start

### 1. Initialize a Project

```bash
forest-change-framework init --name my_forest_project
cd my_forest_project
```

### 2. List Available Components

```bash
forest-change-framework list-components
```

### 3. Basic Usage

```python
from forest_change_framework import BaseFramework

# Create framework instance
framework = BaseFramework()

# Configure and execute a component
result = framework.execute_component(
    category="data_ingestion",
    name="sample_component",
    input_path="data/sample.csv"
)

print(f"Loaded {len(result)} records")
```

### 4. Subscribe to Events

```python
def on_data_loaded(event_name, data):
    print(f"Event received: {event_name}")
    print(f"Data: {data}")

framework.subscribe_event("sample.complete", on_data_loaded)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Forest Change Framework                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Components (Modular Processing Stages)          │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ ┌─────────────────────────────────────────────┐ │  │
│  │ │ Data Ingestion  →  Preprocessing           │ │  │
│  │ │ (Load data)        (Clean & transform)     │ │  │
│  │ └─────────────────────────────────────────────┘ │  │
│  │         ↓                                        │  │
│  │ ┌─────────────────────────────────────────────┐ │  │
│  │ │ Analysis  →  Visualization  →  Export      │ │  │
│  │ │ (Detect)    (Render)           (Save)      │ │  │
│  │ └─────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│         ↕ Event Bus (Pub/Sub Communication)            │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Registry     │  │ Config       │  │ Logger       │ │
│  │ (Discovery)  │  │ (Settings)   │  │ (Monitoring) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Component Categories

The framework organizes components into logical categories:

### 1. **Data Ingestion**
Components for loading forest change data from various sources:
- File-based (CSV, GeoTIFF, NetCDF)
- Database sources (PostgreSQL, MongoDB)
- Remote APIs and cloud services
- Real-time data streams

### 2. **Preprocessing**
Components for data cleaning and transformation:
- Missing value handling
- Data normalization
- Format conversion
- Geospatial alignment

### 3. **Analysis**
Components for forest change detection:
- Change detection algorithms (NDVI, spectral indices)
- Trend analysis
- Anomaly detection
- Impact assessment

### 4. **Visualization**
Components for rendering results:
- Change maps
- Time series charts
- Interactive dashboards
- 3D visualizations

### 5. **Export**
Components for saving results:
- Multiple file formats (GeoJSON, Shapefile, GeoTIFF)
- Database storage
- Cloud upload (S3, GCS)
- Report generation

## Creating Your First Component

### 1. Create Component Structure

```bash
mkdir -p src/forest_change_framework/components/analysis/my_analyzer
touch src/forest_change_framework/components/analysis/my_analyzer/__init__.py
touch src/forest_change_framework/components/analysis/my_analyzer/component.py
```

### 2. Implement Component

```python
from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

@register_component(
    category="analysis",
    name="my_analyzer",
    version="1.0.0",
    description="Detects forest changes using custom algorithm"
)
class MyAnalyzer(BaseComponent):
    @property
    def name(self) -> str:
        return "my_analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict) -> None:
        self.threshold = config.get("threshold", 0.5)

    def execute(self, data, *args, **kwargs):
        results = self._analyze(data)
        self.publish_event("my_analyzer.complete", {
            "changes_detected": len(results)
        })
        return results

    def cleanup(self) -> None:
        pass

    def _analyze(self, data):
        # Your analysis logic here
        return []
```

### 3. Use Your Component

```python
from forest_change_framework import BaseFramework

framework = BaseFramework()
result = framework.execute_component("analysis", "my_analyzer", data)
```

For detailed component development guide, see [Component Development Guide](docs/component-guide.md).

## Configuration

Components are configured via JSON or YAML files:

### JSON Configuration

```json
{
  "data_source": {
    "type": "csv",
    "path": "data/forest_metrics.csv",
    "encoding": "utf-8"
  },
  "processing": {
    "threshold": 0.7,
    "skip_validation": false
  },
  "output": {
    "format": "geojson",
    "path": "output/changes.geojson"
  }
}
```

### YAML Configuration

```yaml
data_source:
  type: csv
  path: data/forest_metrics.csv
  encoding: utf-8

processing:
  threshold: 0.7
  skip_validation: false

output:
  format: geojson
  path: output/changes.geojson
```

## CLI Commands

### Project Management

```bash
# Initialize a new project
forest-change-framework init --name my_project

# List available components
forest-change-framework list-components
forest-change-framework list-components --category analysis

# Get component information
forest-change-framework info analysis my_analyzer
```

### Component Execution

```bash
# Run a component
forest-change-framework run data_ingestion sample_component

# Run with custom configuration
forest-change-framework run analysis my_analyzer --config config.json

# Validate configuration
forest-change-framework validate config.json
```

## Documentation

- [Getting Started Guide](docs/getting-started.md) - Step-by-step tutorial
- [Architecture Documentation](docs/architecture.md) - Design principles and system overview
- [Component Categories](docs/component-categories.md) - Detailed category information
- [API Documentation](docs/api/) - Complete API reference
- [Examples](examples/) - Sample code and templates

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make format

# Run linters
make lint

# Build documentation
make docs

# Clean build artifacts
make clean
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_core/test_registry.py

# With coverage
pytest --cov=src/forest_change_framework --cov-report=html

# Only integration tests
pytest -m integration
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- Follow PEP 8 and PEP 257
- Use type hints throughout
- Include comprehensive docstrings
- Write unit tests for new code
- Maintain >80% code coverage

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{forest_change_framework2024,
  title={Forest Change Framework: A Modular Framework for Forest Change Detection},
  author={Cordari, Flavio},
  year={2024},
  url={https://github.com/bitwiseops/forest-change-framework}
}
```

## Support

- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
- **Issues**: [GitHub Issues](https://github.com/bitwiseops/forest-change-framework/issues)

## Roadmap

- [ ] Web UI for workflow design
- [ ] Distributed processing support
- [ ] Advanced visualization plugins
- [ ] Cloud deployment templates
- [ ] Pre-built analysis pipelines
- [ ] Integration with QGIS
- [ ] Machine learning components

## Acknowledgments

Built with modern Python best practices, inspired by Apache Airflow, Django, and plugin architecture patterns.
