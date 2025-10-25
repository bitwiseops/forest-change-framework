"""
Complete template for creating a custom component.

This is a heavily-commented example showing all best practices for component
development. Use this as a starting template for your own components.
"""

import logging
from typing import Any, Dict, List, Optional

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

logger = logging.getLogger(__name__)


@register_component(
    category="preprocessing",  # Change to your component's category
    name="example_processor",  # Change to your component's name
    version="1.0.0",  # Semantic versioning
    description="Example component demonstrating best practices",
    metadata={
        "author": "Flavio Cordari",
        "tags": ["example", "template"],
        "supported_inputs": ["list", "dict"],
    }
)
class ExampleProcessor(BaseComponent):
    """
    Example component for processing data.

    This component demonstrates all the patterns and best practices for
    developing Forest Change Framework components.

    Configuration Options:
        - threshold (float): Processing threshold (default: 0.5)
        - method (str): Processing method - 'basic' or 'advanced' (default: 'basic')
        - verbose (bool): Enable verbose logging (default: False)

    Events Published:
        - example_processor.start: When processing begins
        - example_processor.progress: During processing
        - example_processor.complete: When processing succeeds
        - example_processor.error: When an error occurs

    Example Usage:
        >>> from forest_change_framework import BaseFramework
        >>> framework = BaseFramework()
        >>> component = framework.instantiate_component(
        ...     "preprocessing", "example_processor",
        ...     {"threshold": 0.7, "method": "advanced"}
        ... )
        >>> result = component.execute([1, 2, 3, 4, 5])
    """

    def __init__(
        self,
        event_bus: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the component.

        Args:
            event_bus: Reference to the central event bus.
            config: Component configuration dictionary.
        """
        # Always call parent constructor first
        super().__init__(event_bus, config)

        # Initialize component-specific attributes
        self._threshold = 0.5
        self._method = "basic"
        self._verbose = False
        self._statistics = {}

        logger.debug(f"{self.name} component initialized")

    @property
    def name(self) -> str:
        """
        Get the component name.

        This must match the name in the @register_component decorator.

        Returns:
            The component identifier string.
        """
        return "example_processor"

    @property
    def version(self) -> str:
        """
        Get the component version.

        Uses semantic versioning (MAJOR.MINOR.PATCH).

        Returns:
            Version string.
        """
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the component with configuration.

        This method is called once before execute(). It should:
        1. Validate and store configuration
        2. Prepare any required resources
        3. Raise exceptions for invalid configuration

        Args:
            config: Configuration dictionary.

        Raises:
            ValueError: If configuration is invalid.

        Example:
            >>> config = {"threshold": 0.7, "method": "advanced"}
            >>> component.initialize(config)
        """
        # Store configuration
        self._config = config

        # Extract and validate configuration values
        self._threshold = config.get("threshold", 0.5)
        self._method = config.get("method", "basic")
        self._verbose = config.get("verbose", False)

        # Validate threshold range
        if not 0 <= self._threshold <= 1:
            raise ValueError(
                f"threshold must be between 0 and 1, got {self._threshold}"
            )

        # Validate method choice
        valid_methods = ["basic", "advanced"]
        if self._method not in valid_methods:
            raise ValueError(
                f"method must be one of {valid_methods}, got {self._method}"
            )

        # Log configuration (respecting verbose setting)
        if self._verbose:
            logger.info(f"Component initialized with config: {config}")
        else:
            logger.info(
                f"Component initialized: threshold={self._threshold}, "
                f"method={self._method}"
            )

    def execute(self, data: List[Any], *args: Any, **kwargs: Any) -> List[Any]:
        """
        Execute the component's core functionality.

        This method performs the actual work. It should:
        1. Validate inputs
        2. Process data
        3. Publish events
        4. Return results

        Args:
            data: Input data to process (list of values).
            *args: Additional positional arguments (unused in this example).
            **kwargs: Additional keyword arguments (unused in this example).

        Returns:
            List of processed values.

        Raises:
            TypeError: If input data is invalid type.
            ValueError: If processing fails.

        Example:
            >>> data = [0.2, 0.6, 0.8, 0.4]
            >>> result = component.execute(data)
            >>> print(result)  # [0.6, 0.8]
        """
        # Validate input
        if not isinstance(data, list):
            raise TypeError(
                f"Expected list input, got {type(data).__name__}"
            )

        if not data:
            logger.warning("Received empty data list")
            return []

        # Publish start event
        self.publish_event(
            f"{self.name}.start",
            {
                "input_count": len(data),
                "threshold": self._threshold,
                "method": self._method,
            }
        )

        try:
            # Process data based on selected method
            if self._method == "basic":
                processed = self._process_basic(data)
            else:  # advanced
                processed = self._process_advanced(data)

            # Compute statistics
            self._compute_statistics(data, processed)

            # Publish success event
            self.publish_event(
                f"{self.name}.complete",
                {
                    "input_count": len(data),
                    "output_count": len(processed),
                    "filtered_count": len(data) - len(processed),
                    "statistics": self._statistics,
                }
            )

            if self._verbose:
                logger.info(
                    f"Processing complete: "
                    f"{len(data)} → {len(processed)} items"
                )

            return processed

        except Exception as e:
            # Log and publish error event
            logger.error(f"Processing failed: {str(e)}", exc_info=True)
            self.publish_event(
                f"{self.name}.error",
                {
                    "error": str(e),
                    "input_count": len(data),
                }
            )
            raise

    def cleanup(self) -> None:
        """
        Clean up component resources.

        This method is called after execute() completes, regardless of
        success or failure. It should clean up any resources like:
        - File handles
        - Database connections
        - Temporary files
        - Memory buffers

        It's safe to call this even if initialize() was never called.
        """
        # Clear cached statistics
        self._statistics.clear()

        if self._verbose:
            logger.debug("Component cleanup completed")

    # ========== PRIVATE HELPER METHODS ==========
    # These are the actual implementation details

    def _process_basic(self, data: List[Any]) -> List[Any]:
        """
        Process data using the basic method.

        Basic method: filter values above threshold.

        Args:
            data: Input data list.

        Returns:
            Filtered data.
        """
        return [x for x in data if float(x) >= self._threshold]

    def _process_advanced(self, data: List[Any]) -> List[Any]:
        """
        Process data using the advanced method.

        Advanced method: filter and normalize values above threshold.

        Args:
            data: Input data list.

        Returns:
            Filtered and normalized data.
        """
        # Filter above threshold
        filtered = [x for x in data if float(x) >= self._threshold]

        if not filtered:
            return []

        # Normalize to 0-1 range
        min_val = min(filtered)
        max_val = max(filtered)
        range_val = max_val - min_val

        if range_val == 0:
            normalized = [0.5] * len(filtered)
        else:
            normalized = [
                (x - min_val) / range_val
                for x in filtered
            ]

        return normalized

    def _compute_statistics(
        self,
        input_data: List[Any],
        output_data: List[Any]
    ) -> None:
        """
        Compute and store processing statistics.

        Args:
            input_data: Original input data.
            output_data: Processed output data.
        """
        input_vals = [float(x) for x in input_data]
        output_vals = [float(x) for x in output_data]

        self._statistics = {
            "input_min": min(input_vals) if input_vals else None,
            "input_max": max(input_vals) if input_vals else None,
            "input_mean": sum(input_vals) / len(input_vals) if input_vals else None,
            "output_min": min(output_vals) if output_vals else None,
            "output_max": max(output_vals) if output_vals else None,
            "output_mean": sum(output_vals) / len(output_vals) if output_vals else None,
            "pass_rate": len(output_vals) / len(input_vals) if input_vals else 0,
        }


# ========== USAGE EXAMPLES ==========

if __name__ == "__main__":
    """
    Example usage when running this file directly.
    """
    from forest_change_framework import BaseFramework

    # Initialize framework
    framework = BaseFramework()

    # Test data
    test_data = [0.1, 0.3, 0.5, 0.7, 0.9]

    print("Example 1: Basic Processing")
    print("-" * 40)

    result1 = framework.execute_component(
        "preprocessing",
        "example_processor",
        test_data,
        threshold=0.5,
        method="basic",
        verbose=True
    )

    print(f"Input:  {test_data}")
    print(f"Output: {result1}")
    print()

    print("Example 2: Advanced Processing")
    print("-" * 40)

    result2 = framework.execute_component(
        "preprocessing",
        "example_processor",
        test_data,
        threshold=0.4,
        method="advanced",
        verbose=True
    )

    print(f"Input:  {test_data}")
    print(f"Output: {result2}")
