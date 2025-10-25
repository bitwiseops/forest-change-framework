"""
Basic usage example of the Forest Change Framework.

This example demonstrates:
1. Initializing the framework
2. Listing available components
3. Executing a component
4. Subscribing to events
"""

from forest_change_framework import BaseFramework, setup_logging


def main():
    """Run basic usage example."""
    # Setup logging
    logger = setup_logging("example", level="INFO")

    print("=" * 60)
    print("Forest Change Framework - Basic Usage Example")
    print("=" * 60)
    print()

    # Step 1: Initialize framework
    print("Step 1: Initializing framework...")
    framework = BaseFramework()
    print("✓ Framework initialized\n")

    # Step 2: List available components
    print("Step 2: Listing registered components...")
    components = framework.list_components()
    for category, comp_list in components.items():
        print(f"  {category}:")
        for comp_name in comp_list:
            info = framework.get_component_info(category, comp_name)
            print(f"    • {comp_name} v{info['version']} - {info['description']}")
    print()

    # Step 3: Subscribe to events
    print("Step 3: Setting up event subscriptions...")

    def on_component_start(event_name, data):
        print(f"  📍 Event: {event_name}")
        print(f"     Data: {data}")

    def on_component_complete(event_name, data):
        print(f"  ✓ Event: {event_name}")
        print(f"    Record count: {data.get('record_count')}")

    def on_component_error(event_name, data):
        print(f"  ✗ Event: {event_name}")
        print(f"    Error: {data.get('error')}")

    framework.subscribe_event("sample.start", on_component_start)
    framework.subscribe_event("sample.complete", on_component_complete)
    framework.subscribe_event("sample.error", on_component_error)
    print("✓ Event subscriptions configured\n")

    # Step 4: Create sample data file
    print("Step 4: Creating sample data...")
    sample_data = """id,date,value
1,2020-01-15,0.75
2,2020-02-20,0.82
3,2020-03-18,0.71
4,2020-04-22,0.88
5,2020-05-19,0.79"""

    with open("/tmp/sample_data.csv", "w") as f:
        f.write(sample_data)
    print("✓ Sample data created at /tmp/sample_data.csv\n")

    # Step 5: Execute component
    print("Step 5: Executing sample_component...")
    try:
        result = framework.execute_component(
            category="data_ingestion",
            name="sample_component",
            input_path="/tmp/sample_data.csv",
            delimiter=","
        )

        print(f"\n✓ Component execution successful!")
        print(f"  Loaded {len(result)} records")
        print(f"\n  Sample records:")
        for record in result[:3]:
            print(f"    {record}")

    except Exception as e:
        print(f"\n✗ Component execution failed: {e}")
        return 1

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
