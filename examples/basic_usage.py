"""
Basic Usage Example
==================

Demonstrates basic usage of the ServiceNow Analytics toolkit.
"""

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


def main():
    """Run basic extraction and analysis pipeline."""

    print("="*70)
    print("ServiceNow Analytics - Basic Usage Example")
    print("="*70)

    # Load configuration
    config = Config()

    # Step 1: Load incidents
    print("\n1. Loading incident data...")

    # Option A: Load from API (requires credentials in .env or config)
    # df = load_incidents('api', limit=100)

    # Option B: Load from CSV
    # df = load_incidents('csv', file_path='data/incidents.csv')

    # Option C: Generate sample data (for demonstration)
    df = load_incidents('sample', num_records=50)

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
    print("✅ Pipeline complete!")
    print("="*70)

    # Display summary statistics
    print("\n📊 Summary Statistics:")
    print(f"   Total incidents: {len(df_transformed)}")
    print(f"   Active incidents: {df_transformed['isActive'].sum()}")
    print(f"   Resolved incidents: {df_transformed['isResolved'].sum()}")
    print(f"   High impact incidents: {df_transformed['isHighImpact'].sum()}")

    if 'patternCategory' in df_transformed.columns:
        print("\n📋 Incident Categories:")
        for category, count in df_transformed['patternCategory'].value_counts().head().items():
            pct = (count / len(df_transformed)) * 100
            print(f"   {category}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
