"""
Real-World ITSM Use Cases
=========================

Practical examples of using ServiceNow Analytics for common ITSM scenarios.
"""

import pandas as pd
from datetime import datetime, timedelta
import logging

from snow_analytics import (
    load_incidents,
    transform_incidents,
    calculate_sla_metrics,
    analyze_resolution_times,
    calculate_backlog_metrics,
    redact_dataframe
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


def use_case_1_daily_sla_report():
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

    # For demo, use sample data
    df = load_incidents('sample', num_records=100)
    df = transform_incidents(df)

    # Filter to resolved incidents only
    df_resolved = df[df['isResolved'] == True]

    # Calculate SLA metrics
    sla_metrics = calculate_sla_metrics(df_resolved)

    # Print report
    print(f"\n📊 SLA Performance Report - {yesterday}")
    print("-" * 70)
    print(f"Total Resolved Incidents: {sla_metrics['total_resolved']}")
    print(f"Met SLA: {sla_metrics['sla_met']} ({100 - sla_metrics['breach_rate_pct']:.1f}%)")
    print(f"Breached SLA: {sla_metrics['sla_breached']} ({sla_metrics['breach_rate_pct']:.1f}%)")

    print(f"\n📈 SLA Performance by Priority:")
    for priority, metrics in sla_metrics['by_priority'].items():
        status = "✅" if metrics['breach_rate_pct'] < 10 else "⚠️" if metrics['breach_rate_pct'] < 20 else "❌"
        print(f"  {status} {priority}: {metrics['breach_rate_pct']:.1f}% breach rate "
              f"({metrics['breached']}/{metrics['total']})")

    # Recommendations
    print(f"\n💡 Recommendations:")
    if sla_metrics['breach_rate_pct'] > 15:
        print("  • SLA breach rate is above 15% - consider additional resources")
    if sla_metrics['by_priority'].get('1 - Critical', {}).get('breach_rate_pct', 0) > 5:
        print("  • P1 incidents breaching SLA - review escalation process")

    print("\n" + "="*70)


def use_case_2_backlog_management():
    """
    Use Case 2: Incident Backlog Analysis
    ======================================

    Scenario: Incident Manager needs to understand current backlog and
              prioritize team workload.

    Frequency: Real-time / On-demand
    Audience: Incident Manager, Team Leads, Service Desk
    """
    print("\n" + "="*70)
    print("USE CASE 2: Incident Backlog Analysis")
    print("="*70)

    # Load active incidents
    df = load_incidents('sample', num_records=100)
    df = transform_incidents(df)

    # Calculate backlog metrics
    backlog = calculate_backlog_metrics(df)

    # Print backlog summary
    print(f"\n📋 Current Backlog Summary")
    print("-" * 70)
    print(f"Total Active Incidents: {backlog['total_backlog']}")
    print(f"Average Age: {backlog['avg_age_days']:.1f} days")

    print(f"\n⏰ Age Distribution:")
    for age_range, count in backlog['by_age'].items():
        if count > 0:
            pct = (count / backlog['total_backlog']) * 100 if backlog['total_backlog'] > 0 else 0
            status = "🟢" if "24h" in age_range else "🟡" if "3days" in age_range else "🔴"
            print(f"  {status} {age_range}: {count} incidents ({pct:.1f}%)")

    print(f"\n🎯 Priority Breakdown:")
    for priority, count in sorted(backlog['by_priority'].items()):
        pct = (count / backlog['total_backlog']) * 100 if backlog['total_backlog'] > 0 else 0
        print(f"  {priority}: {count} incidents ({pct:.1f}%)")

    # Action items
    print(f"\n✅ Action Items:")
    old_incidents = backlog['by_age'].get('more_than_1month', 0)
    if old_incidents > 0:
        print(f"  • Review {old_incidents} incidents over 1 month old for closure/escalation")

    p1_p2_backlog = backlog['by_priority'].get('1 - Critical', 0) + backlog['by_priority'].get('2 - High', 0)
    if p1_p2_backlog > 10:
        print(f"  • {p1_p2_backlog} high-priority incidents in backlog - consider resource reallocation")

    print("\n" + "="*70)


def use_case_3_problem_candidate_identification():
    """
    Use Case 3: Problem Candidate Identification
    ============================================

    Scenario: Problem Manager needs to identify recurring issues that should
              be investigated as problems.

    Frequency: Weekly
    Audience: Problem Manager, Service Improvement Team
    """
    print("\n" + "="*70)
    print("USE CASE 3: Problem Candidate Identification")
    print("="*70)

    # Load historical incidents (last 30 days)
    df = load_incidents('sample', num_records=200)
    df = transform_incidents(df)

    # Find recurring issues
    recurring = find_recurring_issues(df, min_occurrences=5)

    print(f"\n🔍 Found {len(recurring)} recurring issue patterns")
    print("-" * 70)

    if recurring:
        print(f"\nTop Recurring Issues (candidates for Problem Records):\n")
        for i, issue in enumerate(recurring[:10], 1):
            print(f"{i}. Category: {issue['category']}")
            print(f"   CI: {issue['ci']}")
            print(f"   Occurrences: {issue['occurrences']}")
            print(f"   → Recommendation: Create PRB record for investigation")
            print()

    # Analyze patterns
    patterns = analyze_patterns(df)

    print(f"📊 Overall Incident Distribution:")
    for category, count in sorted(patterns['category_distribution'].items(),
                                  key=lambda x: x[1], reverse=True)[:5]:
        pct = (count / len(df)) * 100
        print(f"  {category}: {count} incidents ({pct:.1f}%)")

    print("\n" + "="*70)


def use_case_4_quality_assurance():
    """
    Use Case 4: Incident Quality Assurance
    =======================================

    Scenario: Quality team needs to identify incidents with data quality issues
              for training and process improvement.

    Frequency: Weekly
    Audience: Quality Manager, Training Team, Service Desk Manager
    """
    print("\n" + "="*70)
    print("USE CASE 4: Incident Quality Assurance")
    print("="*70)

    # Load incidents
    df = load_incidents('sample', num_records=100)
    df = transform_incidents(df)

    # Run quality checks
    df_quality = check_incident_quality(df)

    # Calculate quality score
    total = len(df_quality)
    with_issues = (df_quality['quality_issues_count'] > 0).sum()
    quality_score = ((total - with_issues) / total) * 100

    print(f"\n📊 Quality Assessment Summary")
    print("-" * 70)
    print(f"Total Incidents Analyzed: {total}")
    print(f"Incidents with Quality Issues: {with_issues} ({(with_issues/total)*100:.1f}%)")
    print(f"Overall Quality Score: {quality_score:.1f}%")

    # Breakdown by issue type
    print(f"\n🔍 Quality Issues Breakdown:")

    quality_issues = {
        'Priority Misclassification': df_quality['quality_priority_mismatch'].sum(),
        'On Hold Abuse (>72h)': df_quality['quality_on_hold_abuse'].sum(),
        'Poor Short Descriptions': df_quality['quality_poor_description'].sum(),
        'Excessive Reassignments': df_quality['quality_excessive_reassignments'].sum()
    }

    for issue_type, count in quality_issues.items():
        if count > 0:
            pct = (count / total) * 100
            status = "🔴" if pct > 10 else "🟡" if pct > 5 else "🟢"
            print(f"  {status} {issue_type}: {count} ({pct:.1f}%)")

    # Training recommendations
    print(f"\n📚 Training Recommendations:")
    if quality_issues['Poor Short Descriptions'] > total * 0.1:
        print("  • Conduct training on writing effective incident descriptions")
    if quality_issues['Priority Misclassification'] > total * 0.05:
        print("  • Review priority classification guidelines with team")
    if quality_issues['Excessive Reassignments'] > 0:
        print("  • Improve assignment routing and categorization training")

    print("\n" + "="*70)


def use_case_5_routing_optimization():
    """
    Use Case 5: Assignment Routing Optimization
    ==========================================

    Scenario: Service Desk Manager wants to improve first-time assignment accuracy
              and reduce incident bouncing.

    Frequency: Monthly
    Audience: Service Desk Manager, Assignment Group Leads
    """
    print("\n" + "="*70)
    print("USE CASE 5: Assignment Routing Optimization")
    print("="*70)

    # Load incidents
    df = load_incidents('sample', num_records=150)
    df = transform_incidents(df)

    # Analyze reassignments
    reassignment_analysis = analyze_reassignments(df, threshold=1)

    # Calculate routing efficiency
    first_time_success = (df['reassignment_count'] == 0).sum()
    total = len(df)
    efficiency = (first_time_success / total) * 100

    print(f"\n📊 Routing Efficiency Metrics")
    print("-" * 70)
    print(f"Total Incidents: {total}")
    print(f"First-Time Assignment Success: {first_time_success} ({efficiency:.1f}%)")
    print(f"Required Reassignment: {total - first_time_success} ({100 - efficiency:.1f}%)")

    # Analyze by category
    print(f"\n📈 Routing Success by Category:")

    routing_by_category = df.groupby('patternCategory').agg({
        'reassignment_count': lambda x: (x == 0).sum() / len(x) * 100,
        'number': 'count'
    }).sort_values('reassignment_count', ascending=True)

    for category, row in routing_by_category.head(10).iterrows():
        success_rate = row['reassignment_count']
        count = int(row['number'])
        status = "✅" if success_rate > 80 else "⚠️" if success_rate > 60 else "❌"
        print(f"  {status} {category}: {success_rate:.1f}% first-time success ({count} incidents)")

    # Incidents with excessive reassignments
    if not reassignment_analysis.empty:
        print(f"\n⚠️  Top Incidents with Excessive Reassignments:")
        for _, inc in reassignment_analysis.head(5).iterrows():
            print(f"  {inc['number']}: {inc['reassignment_count']} reassignments")
            print(f"    Category: {inc.get('patternCategory', 'Unknown')}")
            print(f"    Current Group: {inc.get('assignment_group', 'Unknown')}")

    # Recommendations
    print(f"\n💡 Routing Improvement Recommendations:")
    worst_category = routing_by_category.index[0] if not routing_by_category.empty else None
    if worst_category and routing_by_category.loc[worst_category, 'reassignment_count'] < 60:
        print(f"  • Review routing rules for '{worst_category}' category ({routing_by_category.loc[worst_category, 'reassignment_count']:.1f}% success)")
    if efficiency < 75:
        print(f"  • Overall routing efficiency is low ({efficiency:.1f}%) - review assignment logic")

    print("\n" + "="*70)


def use_case_6_executive_dashboard():
    """
    Use Case 6: Executive Dashboard / Monthly Report
    ================================================

    Scenario: IT Director needs monthly executive summary for leadership review.

    Frequency: Monthly
    Audience: IT Director, C-Suite, Business Leaders
    """
    print("\n" + "="*70)
    print("USE CASE 6: Executive Dashboard - Monthly Summary")
    print("="*70)

    # Load last month's incidents
    df = load_incidents('sample', num_records=500)
    df = transform_incidents(df)

    # Redact PII for business stakeholders
    df_redacted = redact_dataframe(df)

    # Calculate key metrics
    sla_metrics = calculate_sla_metrics(df)
    resolution_analysis = analyze_resolution_times(df)
    backlog = calculate_backlog_metrics(df)
    patterns = analyze_patterns(df)

    # Executive Summary
    print(f"\n📊 EXECUTIVE SUMMARY - {datetime.now().strftime('%B %Y')}")
    print("=" * 70)

    print(f"\n🎯 Key Performance Indicators:")
    print(f"  Total Incidents: {len(df)}")
    print(f"  Active/Open: {backlog['total_backlog']}")
    print(f"  Resolved: {sla_metrics['total_resolved']}")
    print(f"  SLA Compliance: {100 - sla_metrics['breach_rate_pct']:.1f}%")
    print(f"  Avg Resolution Time: {resolution_analysis['overall']['mean_hrs']:.1f} hours")

    print(f"\n📈 Service Quality:")
    quality_score = 100 - (sla_metrics['breach_rate_pct'] * 0.5)  # Simplified scoring
    status = "🟢 Excellent" if quality_score > 90 else "🟡 Good" if quality_score > 75 else "🔴 Needs Improvement"
    print(f"  Overall Score: {quality_score:.1f}% {status}")

    print(f"\n📋 Top Service Issues:")
    for category, count in list(patterns['category_distribution'].items())[:5]:
        pct = (count / len(df)) * 100
        print(f"  • {category}: {count} incidents ({pct:.1f}%)")

    print(f"\n🔍 Areas Requiring Attention:")
    if sla_metrics['breach_rate_pct'] > 15:
        print(f"  ⚠️  SLA breach rate ({sla_metrics['breach_rate_pct']:.1f}%) exceeds target (15%)")
    if backlog['by_age'].get('more_than_1month', 0) > 10:
        print(f"  ⚠️  {backlog['by_age']['more_than_1month']} incidents over 1 month old in backlog")
    if resolution_analysis['overall']['mean_hrs'] > 48:
        print(f"  ⚠️  Average resolution time ({resolution_analysis['overall']['mean_hrs']:.1f}h) exceeds target (48h)")

    print(f"\n✅ Successes:")
    if sla_metrics['breach_rate_pct'] < 10:
        print(f"  • Excellent SLA compliance ({100 - sla_metrics['breach_rate_pct']:.1f}%)")
    if backlog['avg_age_days'] < 3:
        print(f"  • Low average backlog age ({backlog['avg_age_days']:.1f} days)")

    print("\n" + "="*70)

    # Save redacted data for distribution
    print(f"\n💾 Saving redacted data for business stakeholders...")
    df_redacted[['number', 'priority', 'patternCategory', 'state', 'resolutionTimeHrs']].head(20).to_csv(
        'output/executive_summary_data.csv',
        index=False
    )
    print(f"   ✅ Saved to output/executive_summary_data.csv")


def main():
    """Run all use case demonstrations."""

    print("\n" + "="*70)
    print("ServiceNow Analytics - Real-World ITSM Use Cases")
    print("="*70)
    print("\nDemonstrating 6 common ITSM scenarios:\n")
    print("1. Daily SLA Compliance Report")
    print("2. Incident Backlog Management")
    print("3. Problem Candidate Identification")
    print("4. Incident Quality Assurance")
    print("5. Assignment Routing Optimization")
    print("6. Executive Dashboard / Monthly Report")

    input("\nPress Enter to continue...")

    # Run each use case
    use_case_1_daily_sla_report()
    input("\nPress Enter for next use case...")

    use_case_2_backlog_management()
    input("\nPress Enter for next use case...")

    use_case_3_problem_candidate_identification()
    input("\nPress Enter for next use case...")

    use_case_4_quality_assurance()
    input("\nPress Enter for next use case...")

    use_case_5_routing_optimization()
    input("\nPress Enter for next use case...")

    use_case_6_executive_dashboard()

    print("\n" + "="*70)
    print("✅ All use cases completed!")
    print("="*70)
    print("\nFor more information:")
    print("  • See docs/ITSM_WORKFLOWS.md for detailed workflow documentation")
    print("  • See docs/ITSM_WORKFLOW_DIAGRAM.md for visual diagrams")
    print("  • See README_REFACTORED.md for toolkit usage guide")


if __name__ == "__main__":
    main()
