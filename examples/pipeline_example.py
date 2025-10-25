"""
Pipeline example demonstrating component chaining and event-driven communication.

This example shows:
1. Chaining multiple components
2. Passing data between components
3. Event-driven communication
4. Error handling in pipelines
"""

from forest_change_framework import BaseFramework, setup_logging
import logging


def main():
    """Run a multi-component pipeline example."""
    logger = setup_logging("pipeline_example", level="INFO")

    print("=" * 70)
    print("Forest Change Framework - Pipeline Example")
    print("=" * 70)
    print()

    # Initialize framework
    framework = BaseFramework()

    # Setup event tracking
    events_received = []

    def on_event(event_name, data):
        events_received.append({
            "name": event_name,
            "data": data
        })
        status = data.get("status", "unknown")
        if status == "success":
            print(f"  ✓ {event_name}")
        elif status == "error":
            print(f"  ✗ {event_name}: {data.get('error')}")
        else:
            print(f"  → {event_name}")

    # Subscribe to sample component events
    framework.subscribe_event("sample.start", on_event)
    framework.subscribe_event("sample.complete", on_event)
    framework.subscribe_event("sample.error", on_event)

    # Create sample data
    print("Creating sample data...")
    sample_csv = """timestamp,location,ndvi,forest_cover,elevation
2020-01-15,Site_A,0.78,95,1200
2020-02-20,Site_A,0.72,92,1200
2020-03-18,Site_A,0.81,96,1200
2020-04-22,Site_A,0.75,88,1200
2020-05-19,Site_A,0.85,98,1200
2020-01-15,Site_B,0.65,75,800
2020-02-20,Site_B,0.68,78,800
2020-03-18,Site_B,0.70,80,800
2020-04-22,Site_B,0.62,72,800
2020-05-19,Site_B,0.58,68,800"""

    data_file = "/tmp/pipeline_data.csv"
    with open(data_file, "w") as f:
        f.write(sample_csv)
    print(f"✓ Sample data created: {data_file}\n")

    # Pipeline execution
    print("=" * 70)
    print("STAGE 1: Data Ingestion")
    print("=" * 70)
    print("Loading data from CSV file...")

    try:
        # Stage 1: Load data
        raw_data = framework.execute_component(
            category="data_ingestion",
            name="sample_component",
            input_path=data_file,
            delimiter=",",
            skip_errors=False
        )

        print(f"✓ Loaded {len(raw_data)} records\n")

        # Display loaded data
        print("Sample of loaded data:")
        for i, record in enumerate(raw_data[:3]):
            print(f"  Record {i+1}: {record}")
        if len(raw_data) > 3:
            print(f"  ... and {len(raw_data) - 3} more records")
        print()

    except Exception as e:
        print(f"✗ Data loading failed: {e}")
        return 1

    # Stage 2: Data Filtering (simulated)
    print("=" * 70)
    print("STAGE 2: Data Filtering/Preprocessing")
    print("=" * 70)
    print("Filtering records with NDVI > 0.7...")

    high_ndvi_records = [
        record for record in raw_data
        if float(record.get("ndvi", 0)) > 0.7
    ]

    print(f"✓ Filtered {len(raw_data)} → {len(high_ndvi_records)} records")
    print(f"  Removed: {len(raw_data) - len(high_ndvi_records)} low-NDVI records\n")

    # Stage 3: Analysis (simulated)
    print("=" * 70)
    print("STAGE 3: Analysis")
    print("=" * 70)
    print("Computing forest cover statistics...")

    forest_cover_values = [
        float(record.get("forest_cover", 0))
        for record in high_ndvi_records
    ]

    if forest_cover_values:
        stats = {
            "count": len(forest_cover_values),
            "min": min(forest_cover_values),
            "max": max(forest_cover_values),
            "avg": sum(forest_cover_values) / len(forest_cover_values),
        }

        print(f"✓ Analysis complete:")
        print(f"  Records analyzed: {stats['count']}")
        print(f"  Forest cover range: {stats['min']}% - {stats['max']}%")
        print(f"  Average cover: {stats['avg']:.1f}%\n")
    else:
        print("✗ No records to analyze")
        return 1

    # Stage 4: Results
    print("=" * 70)
    print("STAGE 4: Summary")
    print("=" * 70)

    print(f"Pipeline completed successfully!")
    print(f"\nSummary:")
    print(f"  Input records: {len(raw_data)}")
    print(f"  Output records (NDVI > 0.7): {len(high_ndvi_records)}")
    print(f"  Average forest cover: {stats['avg']:.1f}%")
    print(f"  Events emitted: {len(events_received)}")
    print()

    print("Events received during pipeline:")
    for event in events_received:
        print(f"  • {event['name']}")

    print("\n" + "=" * 70)
    print("Pipeline example completed successfully!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
