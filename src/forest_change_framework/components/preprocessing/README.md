# Preprocessing Components

Preprocessing components handle data cleaning, transformation, and preparation for analysis.

## Purpose

Preprocessing components are responsible for:
- Data validation and quality checks
- Handling missing or invalid values
- Data normalization and standardization
- Format conversion and schema alignment
- Data filtering and subsetting
- Feature engineering and enrichment

## Creating a New Component

### Naming Conventions

- **Directory name**: `snake_case_name` (e.g., `missing_value_handler`, `data_normalizer`, `geospatial_aligner`)
- **Component name**: Matches directory name
- **Class name**: `PascalCase` (e.g., `MissingValueHandler`, `DataNormalizer`)

### Event Naming Conventions

- `{component_name}.start`: When starting preprocessing
- `{component_name}.progress`: During processing
- `{component_name}.complete`: When successfully completed
- `{component_name}.error`: When an error occurs

Example:
```python
self.publish_event("data_normalizer.complete", {
    "records_processed": 1000,
    "records_dropped": 5,
    "records_valid": 995,
})
```

### Configuration Example

```python
def initialize(self, config: Dict[str, Any]) -> None:
    self.method = config.get("method", "linear")
    self.target_columns = config.get("target_columns", [])
    self.handle_missing = config.get("handle_missing", "drop")
```

## Minimal Template

```python
from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

@register_component(
    category="preprocessing",
    name="my_processor",
    version="1.0.0",
    description="Preprocesses data for analysis",
)
class MyProcessor(BaseComponent):
    @property
    def name(self) -> str:
        return "my_processor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict) -> None:
        self._config = config

    def execute(self, data: Any, *args, **kwargs) -> Any:
        # Process data
        processed = self._preprocess(data)
        self.publish_event("my_processor.complete", {
            "input_size": len(data),
            "output_size": len(processed),
        })
        return processed

    def cleanup(self) -> None:
        pass

    def _preprocess(self, data):
        # TODO: Implement preprocessing logic
        return data
```

## Best Practices

1. **Preserve Data**: Make copies to avoid modifying input data
2. **Document Changes**: Log what transformations are applied
3. **Report Statistics**: Emit events with before/after metrics
4. **Handle Edge Cases**: Deal with empty, null, or malformed data
5. **Configuration Validation**: Validate all configuration parameters early

## See Also

- [Framework Architecture](../../docs/architecture.md)
- [Data Ingestion Components](../data_ingestion/README.md)
- [Analysis Components](../analysis/README.md)
