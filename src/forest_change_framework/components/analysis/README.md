# Analysis Components

Analysis components perform the core forest change detection and analysis logic.

## Purpose

Analysis components are responsible for:
- Forest change detection algorithms
- Change metrics calculation
- Trend analysis and forecasting
- Spatial analysis and statistics
- Pattern detection and classification
- Impact assessment

## Creating a New Component

### Naming Conventions

- **Directory name**: `snake_case_name` (e.g., `ndvi_change_detector`, `forest_classifier`, `loss_calculator`)
- **Component name**: Matches directory name
- **Class name**: `PascalCase` (e.g., `NDVIChangeDetector`, `ForestClassifier`, `LossCalculator`)

### Event Naming Conventions

- `{component_name}.start`: When starting analysis
- `{component_name}.progress`: During analysis with progress data
- `{component_name}.complete`: When successfully completed
- `{component_name}.error`: When an error occurs

Example:
```python
self.publish_event("ndvi_change_detector.complete", {
    "changes_detected": 1205,
    "total_area": 50000.5,
    "confidence_score": 0.92,
})
```

### Configuration Example

```python
def initialize(self, config: Dict[str, Any]) -> None:
    self.threshold = config.get("threshold", 0.5)
    self.method = config.get("method", "pixel-based")
    self.temporal_window = config.get("temporal_window", 1)
```

## Minimal Template

```python
from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

@register_component(
    category="analysis",
    name="my_analyzer",
    version="1.0.0",
    description="Analyzes forest change data",
)
class MyAnalyzer(BaseComponent):
    @property
    def name(self) -> str:
        return "my_analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict) -> None:
        self._config = config
        self.threshold = config.get("threshold", 0.5)

    def execute(self, data: Any, *args, **kwargs) -> Any:
        # Perform analysis
        results = self._analyze(data)
        self.publish_event("my_analyzer.complete", {
            "features_detected": len(results),
        })
        return results

    def cleanup(self) -> None:
        pass

    def _analyze(self, data):
        # TODO: Implement analysis logic
        return []
```

## Best Practices

1. **Document Algorithms**: Explain the analysis methodology
2. **Report Confidence**: Include confidence scores or uncertainty measures
3. **Handle Large Datasets**: Use efficient algorithms for large data
4. **Validate Results**: Check output data integrity
5. **Emit Progress**: Publish progress events for long-running analyses
6. **Configuration Flexibility**: Allow tuning algorithm parameters

## See Also

- [Framework Architecture](../../docs/architecture.md)
- [Preprocessing Components](../preprocessing/README.md)
- [Visualization Components](../visualization/README.md)
