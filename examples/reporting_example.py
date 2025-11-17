"""
Reporting Example
=================

Demonstrates the reporting module for exporting data and generating reports.
"""

from snow_analytics import (
    load_incidents,
    transform_incidents,
    export_to_csv,
    export_to_excel,
    export_to_json,
    generate_sla_report,
    generate_backlog_report,
    generate_executive_summary,
    generate_quality_report
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Demonstrate reporting functionality."""

    print("="*70)
    print("ServiceNow Analytics - Reporting Example")
    print("="*70)

    # Load and transform data
    print("\n1. Loading and transforming data...")
    df = load_incidents('sample', num_records=200)
    df = transform_incidents(df)
    print(f"   Loaded and transformed {len(df)} incidents")

    # ========================================================================
    # BASIC EXPORTS
    # ========================================================================

    print("\n2. Basic Exports")
    print("-" * 70)

    # Export to CSV
    print("\n   a) Exporting to CSV...")
    export_to_csv(df, 'output/incidents.csv')
    print("      [OK] CSV export complete")

    # Export to Excel (single sheet)
    print("\n   b) Exporting to Excel (single sheet)...")
    export_to_excel(df, 'output/incidents.xlsx', sheet_name='All Incidents')
    print("      [OK] Excel export complete")

    # Export to Excel (multiple sheets)
    print("\n   c) Exporting to Excel (multiple sheets)...")
    sheets = {
        'Active': df[df['isActive'] == True],
        'Resolved': df[df['isResolved'] == True],
        'High Priority': df[df['priority'].isin(['1 - Critical', '2 - High'])]
    }
    export_to_excel(sheets, 'output/incidents_multi_sheet.xlsx')
    print("      [OK] Multi-sheet Excel export complete")

    # Export to JSON
    print("\n   d) Exporting to JSON...")
    export_to_json(df, 'output/incidents.json', orient='records')
    print("      [OK] JSON export complete")

    # ========================================================================
    # PRE-BUILT REPORTS
    # ========================================================================

    print("\n3. Pre-built Report Templates")
    print("-" * 70)

    # SLA Report
    print("\n   a) Generating SLA Compliance Report...")
    generate_sla_report(df, 'output/sla_report.xlsx')
    print("      [OK] SLA report generated (multi-sheet Excel)")

    # Backlog Report
    print("\n   b) Generating Backlog Report...")
    generate_backlog_report(df, 'output/backlog_report.xlsx')
    print("      [OK] Backlog report generated")

    # Quality Report
    print("\n   c) Generating Quality Report...")
    generate_quality_report(df, 'output/quality_report.xlsx')
    print("      [OK] Quality report generated")

    # Executive Summary
    print("\n   d) Generating Executive Summary...")
    generate_executive_summary(df, 'output/executive_summary.xlsx')
    print("      [OK] Executive summary generated")

    # ========================================================================
    # JSON REPORTS (for API integration)
    # ========================================================================

    print("\n4. JSON Reports (for API/automation)")
    print("-" * 70)

    print("\n   a) Generating SLA Report (JSON)...")
    generate_sla_report(df, 'output/sla_report.json', format='json')
    print("      [OK] JSON SLA report generated")

    print("\n   b) Generating Executive Summary (JSON)...")
    generate_executive_summary(df, 'output/executive_summary.json', format='json')
    print("      [OK] JSON executive summary generated")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("\n" + "="*70)
    print("[SUCCESS] All reports generated successfully!")
    print("="*70)

    print("\nOutput Files:")
    print("   CSV:")
    print("     - output/incidents.csv")
    print("\n   Excel:")
    print("     - output/incidents.xlsx")
    print("     - output/incidents_multi_sheet.xlsx")
    print("     - output/sla_report.xlsx")
    print("     - output/backlog_report.xlsx")
    print("     - output/quality_report.xlsx")
    print("     - output/executive_summary.xlsx")
    print("\n   JSON:")
    print("     - output/incidents.json")
    print("     - output/sla_report.json")
    print("     - output/executive_summary.json")

    print("\nTips:")
    print("   - Use Excel reports for manual analysis and stakeholder sharing")
    print("   - Use JSON reports for API integration and automation")
    print("   - CSV exports are ideal for importing into other tools")
    print()


if __name__ == "__main__":
    main()
