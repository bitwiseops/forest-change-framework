"""
Example plugin implementation.

This example demonstrates how to create and use plugins with the
Forest Change Framework.
"""

import logging
from typing import Any, Dict, Optional

from forest_change_framework.interfaces import BasePlugin

logger = logging.getLogger(__name__)


class MetricsCollectorPlugin(BasePlugin):
    """
    Example plugin that collects framework metrics.

    This plugin demonstrates:
    - Plugin loading and unloading
    - State management
    - Hooks for enable/disable
    - Integration with the framework

    Configuration:
        - enable_detailed_stats (bool): Enable detailed statistics
        - export_format (str): Format for exporting metrics ('json' or 'csv')
    """

    def __init__(self, name: str = "metrics_collector", version: str = "1.0.0") -> None:
        """
        Initialize the plugin.

        Args:
            name: Plugin name.
            version: Plugin version.
        """
        super().__init__(name, version)
        self._metrics = {}
        self._enabled = False
        self._detailed_stats = False
        logger.debug(f"Plugin {name} created")

    def load(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Load and initialize the plugin.

        Called when the plugin is being loaded into the framework.

        Args:
            config: Plugin configuration dictionary.

        Example:
            >>> plugin = MetricsCollectorPlugin()
            >>> plugin.load({"enable_detailed_stats": True})
        """
        config = config or {}

        # Extract configuration
        self._detailed_stats = config.get("enable_detailed_stats", False)
        export_format = config.get("export_format", "json")

        # Initialize metrics
        self._metrics = {
            "components_executed": 0,
            "components_failed": 0,
            "events_published": 0,
            "total_execution_time": 0.0,
            "execution_times": {},
        }

        logger.info(
            f"Metrics Collector Plugin loaded "
            f"(detailed_stats={self._detailed_stats}, format={export_format})"
        )

    def unload(self) -> None:
        """
        Unload and clean up the plugin.

        Called when the plugin is being removed from the framework.

        Example:
            >>> plugin = MetricsCollectorPlugin()
            >>> plugin.load()
            >>> plugin.unload()
        """
        # Export final metrics if needed
        if self._enabled:
            self.on_disable()

        # Clear metrics
        self._metrics.clear()

        logger.info("Metrics Collector Plugin unloaded")

    def on_enable(self) -> None:
        """
        Hook called when the plugin is enabled.

        Activate plugin monitoring.
        """
        self._enabled = True
        logger.info("Metrics collection enabled")

    def on_disable(self) -> None:
        """
        Hook called when the plugin is disabled.

        Deactivate plugin monitoring and export results.
        """
        self._enabled = False
        logger.info("Metrics collection disabled")

        # Print collected metrics
        self._print_metrics()

    # ========== METRICS METHODS ==========

    def record_component_execution(
        self,
        component_name: str,
        execution_time: float,
        success: bool = True
    ) -> None:
        """
        Record a component execution.

        Args:
            component_name: Name of executed component.
            execution_time: Time taken in seconds.
            success: Whether execution succeeded.
        """
        if not self._enabled:
            return

        if success:
            self._metrics["components_executed"] += 1
        else:
            self._metrics["components_failed"] += 1

        self._metrics["total_execution_time"] += execution_time

        # Track individual component timings
        if component_name not in self._metrics["execution_times"]:
            self._metrics["execution_times"][component_name] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
            }

        comp_stats = self._metrics["execution_times"][component_name]
        comp_stats["count"] += 1
        comp_stats["total_time"] += execution_time
        comp_stats["min_time"] = min(comp_stats["min_time"], execution_time)
        comp_stats["max_time"] = max(comp_stats["max_time"], execution_time)

    def record_event_published(self, event_name: str) -> None:
        """
        Record an event publication.

        Args:
            event_name: Name of published event.
        """
        if not self._enabled:
            return

        self._metrics["events_published"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get collected metrics.

        Returns:
            Dictionary of metrics.

        Example:
            >>> plugin = MetricsCollectorPlugin()
            >>> plugin.load()
            >>> plugin.on_enable()
            >>> metrics = plugin.get_metrics()
            >>> print(metrics["components_executed"])
            0
        """
        return self._metrics.copy()

    def _print_metrics(self) -> None:
        """Print collected metrics in a formatted way."""
        print("\n" + "=" * 60)
        print("Metrics Collector - Summary")
        print("=" * 60)

        print(f"\nOverall Statistics:")
        print(f"  Components Executed: {self._metrics['components_executed']}")
        print(f"  Components Failed: {self._metrics['components_failed']}")
        print(f"  Events Published: {self._metrics['events_published']}")
        print(f"  Total Execution Time: {self._metrics['total_execution_time']:.2f}s")

        if self._metrics["execution_times"]:
            print(f"\nPer-Component Statistics:")
            for comp_name, stats in self._metrics["execution_times"].items():
                avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
                print(f"\n  {comp_name}:")
                print(f"    Executions: {stats['count']}")
                print(f"    Total Time: {stats['total_time']:.2f}s")
                print(f"    Avg Time: {avg_time:.2f}s")
                print(f"    Min Time: {stats['min_time']:.2f}s")
                print(f"    Max Time: {stats['max_time']:.2f}s")

        print("\n" + "=" * 60 + "\n")


class LoggingPlugin(BasePlugin):
    """
    Example plugin that provides structured logging.

    This simpler plugin demonstrates:
    - Minimal plugin implementation
    - State tracking
    - Integration with logging
    """

    def __init__(self, name: str = "logging", version: str = "1.0.0") -> None:
        """Initialize logging plugin."""
        super().__init__(name, version)
        self._log_file = None
        self._file_handler = None

    def load(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Load logging configuration."""
        config = config or {}
        self._log_file = config.get("log_file", "framework.log")

        logger.info(f"Logging Plugin loaded (output: {self._log_file})")

    def unload(self) -> None:
        """Unload logging plugin."""
        if self._file_handler:
            self._file_handler.close()

        logger.info("Logging Plugin unloaded")

    def on_enable(self) -> None:
        """Enable structured logging."""
        logger.info("Structured logging enabled")

    def on_disable(self) -> None:
        """Disable structured logging."""
        logger.info("Structured logging disabled")


# ========== USAGE EXAMPLES ==========

if __name__ == "__main__":
    """
    Example of using plugins.
    """
    import time

    print("=" * 60)
    print("Forest Change Framework - Plugin Example")
    print("=" * 60)
    print()

    # Create plugin instance
    print("Step 1: Creating MetricsCollectorPlugin...")
    metrics_plugin = MetricsCollectorPlugin()
    print(f"  ✓ Plugin created: {metrics_plugin.name} v{metrics_plugin.version}")
    print()

    # Load plugin
    print("Step 2: Loading plugin...")
    metrics_plugin.load({"enable_detailed_stats": True})
    print("  ✓ Plugin loaded")
    print()

    # Enable plugin
    print("Step 3: Enabling plugin...")
    metrics_plugin.on_enable()
    print("  ✓ Plugin enabled")
    print()

    # Simulate component executions
    print("Step 4: Simulating component executions...")
    metrics_plugin.record_component_execution("data_loader", 0.5, success=True)
    metrics_plugin.record_component_execution("preprocessor", 0.2, success=True)
    metrics_plugin.record_component_execution("analyzer", 1.2, success=True)
    metrics_plugin.record_component_execution("visualizer", 0.8, success=True)

    # Simulate events
    metrics_plugin.record_event_published("loader.complete")
    metrics_plugin.record_event_published("preprocessor.complete")
    metrics_plugin.record_event_published("analyzer.complete")

    print("  ✓ Simulated 4 component executions and 3 events")
    print()

    # Get metrics
    print("Step 5: Retrieving metrics...")
    metrics = metrics_plugin.get_metrics()
    print(f"  Components executed: {metrics['components_executed']}")
    print(f"  Events published: {metrics['events_published']}")
    print(f"  Total time: {metrics['total_execution_time']:.1f}s")
    print()

    # Disable and unload
    print("Step 6: Disabling and unloading plugin...")
    metrics_plugin.on_disable()
    metrics_plugin.unload()
    print("  ✓ Plugin unloaded")

    print()
    print("=" * 60)
    print("Plugin example completed!")
    print("=" * 60)
