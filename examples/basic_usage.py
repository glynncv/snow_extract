"""
Basic Usage Example
==================

Demonstrates basic usage of the ServiceNow Analytics toolkit.

Usage:
    python basic_usage.py                           # Use sample data (default)
    python basic_usage.py --source sample           # Generate sample data
    python basic_usage.py --source csv --file data/incidents.csv
    python basic_usage.py --source api --limit 100
"""

import argparse
from snow_analytics import (
    load_incidents,
    transform_incidents,
    calculate_sla_metrics,
    analyze_resolution_times
)
from snow_analytics.core import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(source='sample', file_path=None, limit=100, num_records=50):
    """Run basic extraction and analysis pipeline."""

    print("="*70)
    print("ServiceNow Analytics - Basic Usage Example")
    print("="*70)

    # Load configuration
    config = Config()

    # Step 1: Load incidents
    print(f"\n1. Loading incident data from '{source}'...")

    if source == 'api':
        df = load_incidents('api', limit=limit)
    elif source == 'csv':
        if not file_path:
            raise ValueError("--file required when using --source csv")
        df = load_incidents('csv', file_path=file_path)
    else:  # sample
        df = load_incidents('sample', num_records=num_records)

    print(f"   Loaded {len(df)} incidents")

    # Step 2: Transform data
    print("\n2. Transforming incident data...")
    df_transformed = transform_incidents(df)

    print(f"   Added {len(df_transformed.columns) - len(df.columns)} new columns")
    print(f"   New columns: {[col for col in df_transformed.columns if col not in df.columns]}")

    # Step 3: Calculate metrics
    print("\n3. Calculating SLA metrics...")
    sla_metrics = calculate_sla_metrics(df_transformed)

    print(f"   Total resolved: {sla_metrics['total_resolved']}")
    print(f"   SLA breached: {sla_metrics['sla_breached']}")
    print(f"   Breach rate: {sla_metrics['breach_rate_pct']}%")

    # Step 4: Analyze resolution times
    print("\n4. Analyzing resolution times...")
    resolution_analysis = analyze_resolution_times(df_transformed)

    print(f"   Average resolution time: {resolution_analysis['overall']['mean_hrs']:.1f} hours")
    print(f"   Median resolution time: {resolution_analysis['overall']['median_hrs']:.1f} hours")

    # Step 5: Save results
    print("\n5. Saving results...")

    output_dir = "output"
    import os
    os.makedirs(output_dir, exist_ok=True)

    df_transformed.to_csv(f"{output_dir}/incidents_processed_example.csv", index=False)

    print(f"   Saved to {output_dir}/")

    # Note: For PII redaction when sharing data externally,
    # use the separate redaction utility (src/redact5.py)

    print("\n" + "="*70)
    print("[SUCCESS] Pipeline complete!")
    print("="*70)

    # Display summary statistics
    print("\nSummary Statistics:")
    print(f"   Total incidents: {len(df_transformed)}")
    print(f"   Active incidents: {df_transformed['isActive'].sum()}")
    print(f"   Resolved incidents: {df_transformed['isResolved'].sum()}")
    print(f"   High impact incidents: {df_transformed['isHighImpact'].sum()}")

    if 'patternCategory' in df_transformed.columns:
        print("\nIncident Categories:")
        for category, count in df_transformed['patternCategory'].value_counts().head().items():
            pct = (count / len(df_transformed)) * 100
            print(f"   {category}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='ServiceNow Analytics - Basic Usage Example',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use sample data (default)
  %(prog)s --source sample --num-records 100  # Generate 100 sample records
  %(prog)s --source csv --file data/incidents.csv
  %(prog)s --source api --limit 500
        """
    )
    parser.add_argument(
        '--source',
        choices=['sample', 'csv', 'api'],
        default='sample',
        help='Data source (default: sample)'
    )
    parser.add_argument(
        '--file',
        help='CSV file path (required for --source csv)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Max records to load from API (default: 100)'
    )
    parser.add_argument(
        '--num-records',
        type=int,
        default=50,
        help='Number of sample records to generate (default: 50)'
    )

    args = parser.parse_args()

    main(
        source=args.source,
        file_path=args.file,
        limit=args.limit,
        num_records=args.num_records
    )
