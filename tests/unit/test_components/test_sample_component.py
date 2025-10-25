"""
Unit tests for the SampleComponent.

Tests the built-in sample component functionality.
"""

import pytest
import tempfile
from pathlib import Path

from forest_change_framework import BaseFramework
from forest_change_framework.components.data_ingestion.sample_component import SampleComponent


@pytest.mark.unit
class TestSampleComponent:
    """Test SampleComponent functionality."""

    @pytest.fixture
    def sample_csv_file(self):
        """Create a temporary CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name,value\n")
            f.write("1,item_a,100\n")
            f.write("2,item_b,200\n")
            f.write("3,item_c,300\n")
            f.flush()
            yield f.name

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    def test_sample_component_registered(self):
        """Test that SampleComponent is registered."""
        from forest_change_framework.core import get_registry

        registry = get_registry()
        categories = registry.list_categories()
        assert "data_ingestion" in categories

        components = registry.list_components("data_ingestion")
        assert "sample_component" in components["data_ingestion"]

    def test_sample_component_instantiation(self, framework):
        """Test instantiating the sample component."""
        component = framework.instantiate_component(
            "data_ingestion",
            "sample_component",
            {"input_path": "/tmp/test.csv"}
        )

        assert component is not None
        assert component.name == "sample_component"
        assert component.version == "1.0.0"

    def test_sample_component_loads_csv(self, framework, sample_csv_file):
        """Test loading CSV data."""
        result = framework.execute_component(
            "data_ingestion",
            "sample_component",
            input_path=sample_csv_file,
            delimiter=","
        )

        assert len(result) == 3
        assert result[0]["id"] == "1"
        assert result[0]["name"] == "item_a"
        assert result[0]["value"] == "100"

    def test_sample_component_with_encoding(self, framework, sample_csv_file):
        """Test component with encoding parameter."""
        result = framework.execute_component(
            "data_ingestion",
            "sample_component",
            input_path=sample_csv_file,
            encoding="utf-8"
        )

        assert len(result) == 3

    def test_sample_component_skip_errors(self, framework):
        """Test component with skip_errors flag."""
        # Create CSV with malformed line
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name\n")
            f.write("1,valid\n")
            f.write("2\n")  # Missing field
            f.write("3,also_valid\n")
            f.flush()

            # Should skip error with skip_errors=True
            result = framework.execute_component(
                "data_ingestion",
                "sample_component",
                input_path=f.name,
                skip_errors=True
            )

            assert len(result) == 2

            Path(f.name).unlink()

    def test_sample_component_missing_file(self, framework):
        """Test component with missing file raises error."""
        with pytest.raises(IOError):
            framework.execute_component(
                "data_ingestion",
                "sample_component",
                input_path="/nonexistent/file.csv"
            )

    def test_sample_component_publishes_event(self, framework, sample_csv_file, event_collector):
        """Test that component publishes completion event."""
        framework.subscribe_event("sample.complete", event_collector.collect)

        framework.execute_component(
            "data_ingestion",
            "sample_component",
            input_path=sample_csv_file
        )

        assert event_collector.has_event("sample.complete")

        event = event_collector.get_events("sample.complete")[0]
        assert event["data"]["status"] == "success"
        assert event["data"]["record_count"] == 3

    def test_sample_component_cleanup(self, framework, sample_csv_file):
        """Test component cleanup method."""
        component = framework.instantiate_component(
            "data_ingestion",
            "sample_component",
            {"input_path": sample_csv_file}
        )

        component.execute()
        assert len(component._data) > 0

        component.cleanup()
        assert len(component._data) == 0


@pytest.mark.unit
class TestSampleComponentIntegration:
    """Integration-style tests with the sample component."""

    def test_sample_component_with_framework(self, sample_csv_data, event_collector):
        """Test full workflow with sample component."""
        framework = BaseFramework()
        framework.subscribe_event("sample.complete", event_collector.collect)
        framework.subscribe_event("sample.error", event_collector.collect)

        result = framework.execute_component(
            "data_ingestion",
            "sample_component",
            input_path=sample_csv_data
        )

        assert len(result) == 5
        assert event_collector.has_event("sample.complete")
        assert not event_collector.has_event("sample.error")
