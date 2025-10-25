# Visualization Components

Visualization components render analysis results and forest change data.

## Purpose

Visualization components are responsible for:
- Creating maps and cartographic visualizations
- Generating charts and graphs
- Creating dashboards and reports
- Exporting visualizations to various formats
- Interactive data exploration interfaces

## Creating a New Component

### Naming Conventions

- **Directory name**: `snake_case_name` (e.g., `change_map_renderer`, `change_timeline_chart`, `web_dashboard`)
- **Component name**: Matches directory name
- **Class name**: `PascalCase` (e.g., `ChangeMapRenderer`, `ChangeTimelineChart`, `WebDashboard`)

### Event Naming Conventions

- `{component_name}.start`: When starting visualization
- `{component_name}.progress`: During rendering
- `{component_name}.complete`: When successfully rendered
- `{component_name}.error`: When an error occurs

Example:
```python
self.publish_event("change_map_renderer.complete", {
    "output_path": "/output/change_map.png",
    "dimensions": "3000x2000",
})
```

### Configuration Example

```python
def initialize(self, config: Dict[str, Any]) -> None:
    self.output_format = config.get("format", "png")
    self.resolution = config.get("resolution", "high")
    self.colors = config.get("colors", {})
```

## Minimal Template

```python
from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

@register_component(
    category="visualization",
    name="my_visualizer",
    version="1.0.0",
    description="Visualizes analysis results",
)
class MyVisualizer(BaseComponent):
    @property
    def name(self) -> str:
        return "my_visualizer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict) -> None:
        self._config = config
        self.output_path = config.get("output_path")

    def execute(self, data: Any, *args, **kwargs) -> str:
        # Create visualization
        output_file = self._render(data)
        self.publish_event("my_visualizer.complete", {
            "output": output_file,
        })
        return output_file

    def cleanup(self) -> None:
        pass

    def _render(self, data):
        # TODO: Implement visualization logic
        return "output.png"
```

## Best Practices

1. **Specify Output Format**: Always specify output file format and path
2. **Quality Configuration**: Allow users to configure output quality
3. **Color Schemes**: Support customizable color schemes
4. **Geospatial Awareness**: Include coordinate systems and projections
5. **Accessible Output**: Consider colorblind-friendly palettes
6. **Report Rendering Time**: Emit timing information in events

## See Also

- [Framework Architecture](../../docs/architecture.md)
- [Analysis Components](../analysis/README.md)
- [Export Components](../export/README.md)
