"""
Real-World ITSM Use Cases
=========================

Practical examples of using ServiceNow Analytics for common ITSM scenarios.

Usage:
    python itsm_use_cases.py                        # Run all use cases with sample data
    python itsm_use_cases.py --source csv --file data/incidents.csv
    python itsm_use_cases.py --source api --limit 500
    python itsm_use_cases.py --use-case 1           # Run specific use case only
"""

import argparse
import pandas as pd
from datetime import datetime, timedelta
import logging

from snow_analytics import (
    load_incidents,
    transform_incidents,
    calculate_sla_metrics,
    analyze_resolution_times,
    calculate_backlog_metrics
)
from snow_analytics.analysis import (
    analyze_patterns,
    find_recurring_issues,
    analyze_reassignments
)
from snow_analytics.analysis.quality import (
    check_incident_quality,
    detect_priority_misclassification,
    detect_on_hold_abuse
)
from snow_analytics.core import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def use_case_1_daily_sla_report(source='sample', file_path=None, limit=100, num_records=100):
    """
    Use Case 1: Daily SLA Compliance Report
    ========================================

    Scenario: Service Desk Manager needs a daily report showing SLA performance
              to ensure team is meeting commitments.

    Frequency: Daily at 8 AM
    Audience: Service Desk Manager, Team Leads
    """
    print("\n" + "="*70)
    print("USE CASE 1: Daily SLA Compliance Report")
    print("="*70)

    # Load yesterday's incidents
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Load data based on source parameter
    if source == 'api':
        df = load_incidents('api', limit=limit)
    elif source == 'csv':
        df = load_incidents('csv', file_path=file_path)
    else:
        df = load_incidents('sample', num_records=num_records)

    df = transform_incidents(df)

    # Filter to resolved incidents only
    df_resolved = df[df['isResolved'] == True]

    # Calculate SLA metrics
    sla_metrics = calculate_sla_metrics(df_resolved)

    # Print report
    print(f"\nSLA Performance Report - {yesterday}")
    print("-" * 70)
    print(f"Total Resolved Incidents: {sla_metrics['total_resolved']}")
    print(f"Met SLA: {sla_metrics['sla_met']} ({100 - sla_metrics['breach_rate_pct']:.1f}%)")
    print(f"Breached SLA: {sla_metrics['sla_breached']} ({sla_metrics['breach_rate_pct']:.1f}%)")

    print(f"\nSLA Performance by Priority:")
    for priority, metrics in sla_metrics['by_priority'].items():
        status = "[OK]" if metrics['breach_rate_pct'] < 10 else "[WARNING]" if metrics['breach_rate_pct'] < 20 else "[FAIL]"
        print(f"  {priority:15} {status:12} Breach Rate: {metrics['breach_rate_pct']:5.1f}%")

    print("\n" + "="*70)


def main(source='sample', file_path=None, limit=500, num_records=500, use_case=None):
    """Run use case demonstrations."""

    print("\n" + "="*70)
    print("ServiceNow Analytics - Real-World ITSM Use Cases")
    print("="*70)

    kwargs = {
        'source': source,
        'file_path': file_path,
        'limit': limit,
        'num_records': num_records
    }

    if use_case:
        # Run specific use case
        if use_case == 1:
            use_case_1_daily_sla_report(**kwargs)
        else:
            print(f"\nNote: Only Use Case 1 is fully implemented in this example.")
            print(f"See docs/ITSM_WORKFLOWS.md for other workflow examples.")
    else:
        # Run Use Case 1 as demonstration
        use_case_1_daily_sla_report(**kwargs)
        print("\n[Note: Only Use Case 1 shown - use --use-case 1 to run specifically]")

    print("\n" + "="*70)
    print("[SUCCESS] Use case demonstration completed!")
    print("="*70)
    print("\nFor more information:")
    print("  • See docs/ITSM_WORKFLOWS.md for detailed workflow documentation")
    print("  • See docs/ITSM_WORKFLOW_DIAGRAM.md for visual diagrams")
    print("  • See README_REFACTORED.md for toolkit usage guide")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='ServiceNow Analytics - ITSM Use Cases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with sample data
  %(prog)s --use-case 1                       # Run specific use case
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
        default=500,
        help='Max records to load from API (default: 500)'
    )
    parser.add_argument(
        '--num-records',
        type=int,
        default=500,
        help='Number of sample records to generate (default: 500)'
    )
    parser.add_argument(
        '--use-case',
        type=int,
        choices=[1],
        help='Run specific use case (currently only 1 available)'
    )

    args = parser.parse_args()

    main(
        source=args.source,
        file_path=args.file,
        limit=args.limit,
        num_records=args.num_records,
        use_case=args.use_case
    )
