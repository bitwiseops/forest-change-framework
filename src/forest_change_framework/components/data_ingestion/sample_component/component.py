"""
Sample data ingestion component.

This is a complete, production-ready sample component that demonstrates:
- Proper component structure and inheritance
- Configuration handling
- Event publishing
- Error handling and logging
- Type hints and documentation
"""

import logging
from typing import Any, Dict, List, Optional

from forest_change_framework.core import register_component
from forest_change_framework.interfaces import BaseComponent

logger = logging.getLogger(__name__)


@register_component(
    category="data_ingestion",
    name="sample_component",
    version="1.0.0",
    description="Sample component that loads data from a CSV-like file",
    metadata={
        "author": "Flavio Cordari",
        "tags": ["sample", "ingestion"],
    },
)
class SampleComponent(BaseComponent):
    """
    Sample data ingestion component.

    This component demonstrates loading data from a file and publishing events.
    It serves as a template for creating new components in the framework.

    Configuration:
        - input_path (str): Path to the input data file
        - delimiter (str): Delimiter character (default: ",")
        - encoding (str): File encoding (default: "utf-8")
        - skip_errors (bool): Skip malformed lines (default: False)

    Raises:
        ValueError: If input_path is not configured
        IOError: If file cannot be read
        ValueError: If file format is invalid

    Example:
        >>> from forest_change_framework.core import BaseFramework
        >>> framework = BaseFramework()
        >>> component = framework.instantiate_component("data_ingestion", "sample_component")
        >>> result = component.execute()
    """

    def __init__(
        self,
        event_bus: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the sample component.

        Args:
            event_bus: Reference to the central event bus.
            config: Component configuration dictionary.
        """
        super().__init__(event_bus, config)
        self._data: List[Dict[str, Any]] = []
        self._loaded = False
        logger.debug("SampleComponent initialized")

    @property
    def name(self) -> str:
        """Get the component name."""
        return "sample_component"

    @property
    def version(self) -> str:
        """Get the component version."""
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the component with configuration.

        Validates that required configuration keys are present and
        prepares the component for execution.

        Args:
            config: Configuration dictionary.

        Raises:
            ValueError: If required configuration is missing.

        Example:
            >>> config = {"input_path": "/data/sample.csv"}
            >>> component.initialize(config)
        """
        self._config = config

        # Validate required configuration
        if not self.get_config("input_path"):
            raise ValueError(
                "Component configuration missing required key: input_path"
            )

        logger.info(f"Component initialized with config: {config}")

    def execute(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Execute the component's core functionality.

        Loads data from the configured input file and publishes an event
        when complete.

        Args:
            *args: Positional arguments (unused for this component).
            **kwargs: Keyword arguments (unused for this component).

        Returns:
            List of dictionaries representing the loaded data.

        Raises:
            IOError: If file cannot be read.
            ValueError: If file format is invalid.

        Example:
            >>> data = component.execute()
            >>> len(data)
            100
        """
        try:
            input_path = self.get_config("input_path")
            delimiter = self.get_config("delimiter", ",")
            encoding = self.get_config("encoding", "utf-8")
            skip_errors = self.get_config("skip_errors", False)

            logger.debug(f"Loading data from: {input_path}")

            # Load and parse the file
            self._data = self._load_data(
                input_path,
                delimiter=delimiter,
                encoding=encoding,
                skip_errors=skip_errors,
            )

            self._loaded = True
            num_records = len(self._data)

            # Publish event to notify other components
            event_data = {
                "component": self.name,
                "status": "success",
                "record_count": num_records,
                "input_path": input_path,
            }
            self.publish_event("sample.complete", event_data)

            logger.info(f"Component executed successfully, loaded {num_records} records")
            return self._data

        except Exception as e:
            logger.error(f"Component execution failed: {str(e)}", exc_info=True)
            # Publish error event
            self.publish_event(
                "sample.error",
                {
                    "component": self.name,
                    "status": "error",
                    "error": str(e),
                },
            )
            raise

    def cleanup(self) -> None:
        """
        Clean up component resources.

        Clears loaded data and resets component state.
        """
        self._data.clear()
        self._loaded = False
        logger.debug("Component cleaned up")

    def _load_data(
        self,
        filepath: str,
        delimiter: str = ",",
        encoding: str = "utf-8",
        skip_errors: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Load data from a delimited file.

        Internal method that handles file parsing and data loading.

        Args:
            filepath: Path to the data file.
            delimiter: Field delimiter character.
            encoding: File encoding.
            skip_errors: If True, skip lines that cannot be parsed.

        Returns:
            List of dictionaries representing parsed data.

        Raises:
            IOError: If file cannot be opened or read.
            ValueError: If file format is invalid (unless skip_errors=True).
        """
        data: List[Dict[str, Any]] = []

        try:
            with open(filepath, "r", encoding=encoding) as f:
                lines = f.readlines()

                if not lines:
                    logger.warning(f"File is empty: {filepath}")
                    return data

                # First line is header
                headers = lines[0].strip().split(delimiter)
                headers = [h.strip() for h in headers]

                # Parse data rows
                for line_num, line in enumerate(lines[1:], start=2):
                    try:
                        values = line.strip().split(delimiter)
                        values = [v.strip() for v in values]

                        if len(values) != len(headers):
                            if not skip_errors:
                                raise ValueError(
                                    f"Line {line_num}: Field count mismatch "
                                    f"(expected {len(headers)}, got {len(values)})"
                                )
                            logger.warning(
                                f"Skipping line {line_num}: Field count mismatch"
                            )
                            continue

                        # Create record dictionary
                        record = dict(zip(headers, values))
                        data.append(record)

                    except Exception as e:
                        if not skip_errors:
                            raise
                        logger.warning(f"Skipping line {line_num}: {str(e)}")
                        continue

            logger.debug(f"Loaded {len(data)} records from {filepath}")
            return data

        except IOError as e:
            logger.error(f"Failed to read file {filepath}: {str(e)}")
            raise
