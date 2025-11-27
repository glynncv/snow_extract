"""
Workflow 1: Morning Quality & Escalation Report
================================================

Automated daily quality check and escalation report.

Saves ~45 minutes/day by automating backlog analysis and escalation drafting.

Usage:
    python workflow_morning_quality.py                    # Sample data
    python workflow_morning_quality.py --source csv --file downloads/daily_incidents.csv
    python workflow_morning_quality.py --source api --limit 1000

Output:
    - output/morning_quality_report_YYYY-MM-DD.xlsx (Excel report)
    - output/escalation_drafts_YYYY-MM-DD.txt (Ready-to-send text)
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import logging

from snow_analytics import (
    load_incidents,
    transform_incidents,
    export_to_excel
)
from snow_analytics.analysis.quality import (
    detect_priority_misclassification,
    detect_on_hold_abuse,
    check_incident_quality
)
from snow_analytics.analysis import analyze_reassignments

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def detect_misrouted_tickets(df, threshold=3):
    """
    Detect tickets with excessive reassignments (mis-routing).

    Args:
        df: Incident DataFrame
        threshold: Number of reassignments to flag (default: 3)

    Returns:
        DataFrame with mis-routed tickets
    """
    logger.info(f"Detecting mis-routed tickets (>{threshold} reassignments)...")

    # Use reassignment analysis
    reassignment_analysis = analyze_reassignments(df)

    # Create detailed dataframe
    misrouted = []
    for ticket_num, info in reassignment_analysis.get('by_incident', {}).items():
        if info['reassignment_count'] > threshold:
            ticket_data = df[df['number'] == ticket_num].iloc[0] if ticket_num in df['number'].values else None
            if ticket_data is not None:
                misrouted.append({
                    'number': ticket_num,
                    'priority': ticket_data.get('priority', 'Unknown'),
                    'state': ticket_data.get('state', 'Unknown'),
                    'reassignment_count': info['reassignment_count'],
                    'current_assignee': info.get('current_assignee', 'Unassigned'),
                    'reassignment_history': ' → '.join(info.get('path', [])),
                    'short_description': ticket_data.get('short_description', '')[:100]
                })

    df_misrouted = pd.DataFrame(misrouted)
    logger.info(f"Found {len(df_misrouted)} mis-routed tickets")

    return df_misrouted


def detect_pre_backlog_warnings(df, warning_days_min=7, warning_days_max=9, backlog_threshold=10):
    """
    Identify tickets approaching backlog status (prevention).

    Args:
        df: Incident DataFrame
        warning_days_min: Start warning at this age (default: 7 days)
        warning_days_max: Stop warning at this age (default: 9 days)
        backlog_threshold: Backlog definition (default: 10 days)

    Returns:
        DataFrame with pre-backlog tickets
    """
    logger.info(f"Detecting pre-backlog warnings ({warning_days_min}-{warning_days_max} days old)...")

    if 'isActive' not in df.columns or 'ageDays' not in df.columns:
        logger.warning("Missing required columns for pre-backlog detection")
        return pd.DataFrame()

    # Active tickets in the warning zone
    pre_backlog = df[
        (df['isActive'] == True) &
        (df['ageDays'] >= warning_days_min) &
        (df['ageDays'] < backlog_threshold)
    ].copy()

    # Calculate days until backlog
    pre_backlog['days_until_backlog'] = backlog_threshold - pre_backlog['ageDays']

    # Sort by urgency
    pre_backlog = pre_backlog.sort_values('days_until_backlog')

    logger.info(f"Found {len(pre_backlog)} tickets approaching backlog")

    return pre_backlog


def detect_sla_breach_risk(df, warning_hours=4):
    """
    Identify tickets at risk of SLA breach (prevention).

    Args:
        df: Incident DataFrame
        warning_hours: Alert when this many hours remain (default: 4)

    Returns:
        DataFrame with at-risk tickets
    """
    logger.info(f"Detecting SLA breach risk (<{warning_hours} hours remaining)...")

    if 'isActive' not in df.columns or 'slaMarginHrs' not in df.columns:
        logger.warning("Missing required columns for SLA breach detection")
        return pd.DataFrame()

    # Active tickets with SLA margin below threshold
    at_risk = df[
        (df['isActive'] == True) &
        (df['slaMarginHrs'] < warning_hours) &
        (df['slaMarginHrs'] > 0)  # Not already breached
    ].copy()

    # Sort by urgency (least time remaining first)
    at_risk = at_risk.sort_values('slaMarginHrs')

    logger.info(f"Found {len(at_risk)} tickets at SLA breach risk")

    return at_risk


def generate_escalation_text(summary_stats, df_priority, df_misrouted, df_onhold, df_prebacklog, df_slarisk):
    """
    Generate ready-to-send escalation text for Teams/Email.

    Returns:
        String containing formatted escalation messages
    """
    today = datetime.now().strftime('%Y-%m-%d')

    escalation = []
    escalation.append("=" * 70)
    escalation.append(f"DAILY QUALITY & ESCALATION REPORT - {today}")
    escalation.append("=" * 70)
    escalation.append("")

    # Summary
    escalation.append("📊 SUMMARY")
    escalation.append("-" * 70)
    escalation.append(f"Total Incidents Analyzed: {summary_stats['total']}")
    escalation.append(f"Active Incidents: {summary_stats['active']}")
    escalation.append(f"Issues Found: {summary_stats['total_issues']}")
    escalation.append("")

    # Critical - SLA Breach Risk
    if len(df_slarisk) > 0:
        escalation.append("🚨 CRITICAL - SLA BREACH RISK")
        escalation.append("-" * 70)
        escalation.append(f"Tickets at risk: {len(df_slarisk)}")
        escalation.append("")
        escalation.append("Top 5 most urgent:")
        for idx, row in df_slarisk.head(5).iterrows():
            hours_left = row.get('slaMarginHrs', 0)
            escalation.append(f"  • {row['number']} [{row['priority']}] - {hours_left:.1f}h remaining - {row.get('assigned_to', 'UNASSIGNED')}")
        escalation.append("")
        escalation.append("⚡ ACTION REQUIRED: Immediate intervention needed")
        escalation.append("")

    # High Priority - Pre-Backlog Warnings
    if len(df_prebacklog) > 0:
        escalation.append("⚠️  HIGH PRIORITY - PRE-BACKLOG WARNINGS")
        escalation.append("-" * 70)
        escalation.append(f"Tickets approaching backlog (7-9 days old): {len(df_prebacklog)}")
        escalation.append("")
        escalation.append("Top 5 by urgency:")
        for idx, row in df_prebacklog.head(5).iterrows():
            days_left = row.get('days_until_backlog', 0)
            escalation.append(f"  • {row['number']} [{row['priority']}] - {days_left:.1f} days until backlog - {row.get('assigned_to', 'UNASSIGNED')}")
        escalation.append("")
        escalation.append("⚡ ACTION REQUIRED: Prevent these from hitting backlog")
        escalation.append("")

    # Priority Misclassification
    if len(df_priority) > 0:
        escalation.append("🔴 PRIORITY MISCLASSIFICATION")
        escalation.append("-" * 70)
        escalation.append(f"Tickets with priority issues: {len(df_priority)}")
        escalation.append("")
        p1_p2 = df_priority[df_priority['priority'].isin(['1 - Critical', '2 - High'])]
        if len(p1_p2) > 0:
            escalation.append(f"P1/P2 tickets with misclassification: {len(p1_p2)}")
            for idx, row in p1_p2.head(5).iterrows():
                escalation.append(f"  • {row['number']} [{row['priority']}] - {row.get('short_description', '')[:60]}")
        escalation.append("")
        escalation.append("📝 ACTION: Review and reclassify if needed")
        escalation.append("")

    # Mis-routed Tickets
    if len(df_misrouted) > 0:
        escalation.append("🔄 MIS-ROUTED TICKETS (>3 Reassignments)")
        escalation.append("-" * 70)
        escalation.append(f"Tickets bouncing between teams: {len(df_misrouted)}")
        escalation.append("")
        escalation.append("Top 5 by reassignment count:")
        for idx, row in df_misrouted.head(5).iterrows():
            count = row.get('reassignment_count', 0)
            escalation.append(f"  • {row['number']} - {count} reassignments")
            escalation.append(f"    Path: {row.get('reassignment_history', 'Unknown')[:80]}")
        escalation.append("")
        escalation.append("📝 ACTION: Review routing and assignment rules")
        escalation.append("")

    # On-Hold Abuse
    if len(df_onhold) > 0:
        escalation.append("⏸️  ON-HOLD ISSUES")
        escalation.append("-" * 70)
        escalation.append(f"Tickets on-hold >72 hours: {len(df_onhold)}")
        escalation.append("")
        escalation.append("Top 5 by hold duration:")
        for idx, row in df_onhold.head(5).iterrows():
            hold_days = row.get('on_hold_duration_hrs', 0) / 24
            escalation.append(f"  • {row['number']} - {hold_days:.1f} days on hold - {row.get('assigned_to', 'UNASSIGNED')}")
        escalation.append("")
        escalation.append("📝 ACTION: Follow up or resolve")
        escalation.append("")

    # Summary Actions
    escalation.append("=" * 70)
    escalation.append("RECOMMENDED ACTIONS")
    escalation.append("=" * 70)
    escalation.append("1. Address SLA breach risks immediately (assign/escalate)")
    escalation.append("2. Prevent pre-backlog tickets from aging to 10+ days")
    escalation.append("3. Review and correct priority misclassifications")
    escalation.append("4. Investigate routing issues causing reassignment loops")
    escalation.append("5. Follow up on stale on-hold tickets")
    escalation.append("")
    escalation.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    escalation.append("=" * 70)

    return "\n".join(escalation)


def main(source='sample', file_path=None, limit=1000, num_records=200,
         reassignment_threshold=3, onhold_threshold_hrs=72,
         prebacklog_min_days=7, prebacklog_max_days=9,
         sla_warning_hours=4):
    """
    Generate morning quality and escalation report.

    Args:
        source: Data source ('sample', 'csv', 'api')
        file_path: Path to CSV file (if source='csv')
        limit: API query limit (if source='api')
        num_records: Number of sample records (if source='sample')
        reassignment_threshold: Flag tickets with >N reassignments
        onhold_threshold_hrs: Flag on-hold tickets >N hours
        prebacklog_min_days: Start pre-backlog warning at N days
        prebacklog_max_days: Stop pre-backlog warning at N days
        sla_warning_hours: Flag tickets with <N hours to SLA breach
    """

    print("=" * 70)
    print("WORKFLOW 1: Morning Quality & Escalation Report")
    print("=" * 70)
    print()

    # Step 1: Load incidents
    print(f"📥 Loading incidents from '{source}'...")

    if source == 'api':
        # Load recent incidents (last 48 hours + all active)
        df = load_incidents('api', limit=limit)
    elif source == 'csv':
        if not file_path:
            raise ValueError("--file required when using --source csv")
        df = load_incidents('csv', file_path=file_path)
    else:  # sample
        df = load_incidents('sample', num_records=num_records)

    print(f"   Loaded {len(df)} incidents")
    print()

    # Step 2: Transform
    print("🔄 Transforming incident data...")
    df = transform_incidents(df)
    print(f"   Transformation complete")
    print()

    # Step 3: Run quality checks
    print("🔍 Running quality checks...")
    print()

    # 3.1 Priority Misclassification
    df_priority = detect_priority_misclassification(df)
    priority_issues = df_priority[df_priority.get('quality_priority_mismatch', False) == True]

    # 3.2 Mis-routed Tickets
    df_misrouted = detect_misrouted_tickets(df, threshold=reassignment_threshold)

    # 3.3 On-Hold Abuse
    df_onhold = detect_on_hold_abuse(df, threshold_hours=onhold_threshold_hrs)

    # 3.4 Pre-Backlog Warnings (PREVENTION)
    df_prebacklog = detect_pre_backlog_warnings(
        df,
        warning_days_min=prebacklog_min_days,
        warning_days_max=prebacklog_max_days
    )

    # 3.5 SLA Breach Risk (PREVENTION)
    df_slarisk = detect_sla_breach_risk(df, warning_hours=sla_warning_hours)

    print()

    # Summary statistics
    summary_stats = {
        'total': len(df),
        'active': df['isActive'].sum() if 'isActive' in df.columns else 0,
        'priority_issues': len(priority_issues),
        'misrouted': len(df_misrouted),
        'onhold_abuse': len(df_onhold),
        'prebacklog': len(df_prebacklog),
        'sla_risk': len(df_slarisk),
        'total_issues': len(priority_issues) + len(df_misrouted) + len(df_onhold) + len(df_prebacklog) + len(df_slarisk)
    }

    # Step 4: Generate Excel Report
    print("📊 Generating Excel report...")

    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    excel_path = output_dir / f'morning_quality_report_{today}.xlsx'

    sheets = {}

    # Sheet 1: Summary Dashboard
    summary_data = {
        'Metric': [
            'Total Incidents Analyzed',
            'Active Incidents',
            '',
            'PREVENTION ALERTS',
            'SLA Breach Risk (<4 hrs)',
            'Pre-Backlog Warnings (7-9 days)',
            '',
            'QUALITY ISSUES',
            'Priority Misclassification',
            'Mis-routed (>3 reassignments)',
            'On-Hold Abuse (>72 hrs)',
            '',
            'Total Issues Flagged',
            'Report Generated'
        ],
        'Count': [
            summary_stats['total'],
            summary_stats['active'],
            '',
            '',
            summary_stats['sla_risk'],
            summary_stats['prebacklog'],
            '',
            '',
            summary_stats['priority_issues'],
            summary_stats['misrouted'],
            summary_stats['onhold_abuse'],
            '',
            summary_stats['total_issues'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
    }
    sheets['Summary'] = pd.DataFrame(summary_data)

    # Sheet 2: SLA Breach Risk (CRITICAL)
    if len(df_slarisk) > 0:
        sla_risk_cols = ['number', 'priority', 'state', 'slaMarginHrs', 'assigned_to',
                        'openedDate', 'ageDays', 'short_description']
        available_cols = [col for col in sla_risk_cols if col in df_slarisk.columns]
        sheets['SLA Breach Risk'] = df_slarisk[available_cols]

    # Sheet 3: Pre-Backlog Warnings
    if len(df_prebacklog) > 0:
        prebacklog_cols = ['number', 'priority', 'state', 'days_until_backlog', 'ageDays',
                          'assigned_to', 'openedDate', 'short_description']
        available_cols = [col for col in prebacklog_cols if col in df_prebacklog.columns]
        sheets['Pre-Backlog Warnings'] = df_prebacklog[available_cols]

    # Sheet 4: Priority Issues
    if len(priority_issues) > 0:
        priority_cols = ['number', 'priority', 'state', 'resolutionTimeHrs',
                        'assigned_to', 'short_description']
        available_cols = [col for col in priority_cols if col in priority_issues.columns]
        sheets['Priority Issues'] = priority_issues[available_cols]

    # Sheet 5: Routing Issues
    if len(df_misrouted) > 0:
        sheets['Routing Issues'] = df_misrouted

    # Sheet 6: On-Hold Abuse
    if len(df_onhold) > 0:
        onhold_cols = ['number', 'priority', 'state', 'on_hold_duration_hrs',
                      'assigned_to', 'short_description']
        available_cols = [col for col in onhold_cols if col in df_onhold.columns]
        sheets['On-Hold Abuse'] = df_onhold[available_cols]

    export_to_excel(sheets, excel_path)
    print(f"   ✅ Excel report saved: {excel_path}")
    print()

    # Step 5: Generate Escalation Text
    print("📝 Generating escalation text...")

    escalation_text = generate_escalation_text(
        summary_stats, priority_issues, df_misrouted, df_onhold, df_prebacklog, df_slarisk
    )

    text_path = output_dir / f'escalation_drafts_{today}.txt'
    with open(text_path, 'w') as f:
        f.write(escalation_text)

    print(f"   ✅ Escalation text saved: {text_path}")
    print()

    # Display summary to console
    print("=" * 70)
    print("📊 RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Incidents Analyzed: {summary_stats['total']}")
    print(f"Active Incidents: {summary_stats['active']}")
    print()
    print("Issues Found:")
    print(f"  🚨 SLA Breach Risk: {summary_stats['sla_risk']} tickets")
    print(f"  ⚠️  Pre-Backlog Warnings: {summary_stats['prebacklog']} tickets")
    print(f"  🔴 Priority Issues: {summary_stats['priority_issues']} tickets")
    print(f"  🔄 Mis-routed: {summary_stats['misrouted']} tickets")
    print(f"  ⏸️  On-Hold Abuse: {summary_stats['onhold_abuse']} tickets")
    print()
    print(f"Total Issues: {summary_stats['total_issues']}")
    print()
    print("=" * 70)
    print("[SUCCESS] Morning quality report complete!")
    print("=" * 70)
    print()
    print("📂 Output Files:")
    print(f"   - {excel_path}")
    print(f"   - {text_path}")
    print()
    print("💡 Next Steps:")
    print("   1. Review Excel report for details")
    print("   2. Copy escalation text for Teams/Email")
    print("   3. Take action on flagged items")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Workflow 1: Morning Quality & Escalation Report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use sample data
  %(prog)s --source csv --file downloads/daily_incidents.csv
  %(prog)s --source api --limit 1000
  %(prog)s --reassignment-threshold 4         # Flag >4 reassignments
  %(prog)s --sla-warning-hours 2              # Flag <2 hours to breach
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
        default=1000,
        help='Max records to load from API (default: 1000)'
    )
    parser.add_argument(
        '--num-records',
        type=int,
        default=200,
        help='Number of sample records to generate (default: 200)'
    )
    parser.add_argument(
        '--reassignment-threshold',
        type=int,
        default=3,
        help='Flag tickets with more than N reassignments (default: 3)'
    )
    parser.add_argument(
        '--onhold-threshold-hrs',
        type=int,
        default=72,
        help='Flag on-hold tickets older than N hours (default: 72)'
    )
    parser.add_argument(
        '--prebacklog-min-days',
        type=int,
        default=7,
        help='Start pre-backlog warning at N days (default: 7)'
    )
    parser.add_argument(
        '--prebacklog-max-days',
        type=int,
        default=9,
        help='Stop pre-backlog warning at N days (default: 9)'
    )
    parser.add_argument(
        '--sla-warning-hours',
        type=int,
        default=4,
        help='Flag tickets with less than N hours to SLA breach (default: 4)'
    )

    args = parser.parse_args()

    main(
        source=args.source,
        file_path=args.file,
        limit=args.limit,
        num_records=args.num_records,
        reassignment_threshold=args.reassignment_threshold,
        onhold_threshold_hrs=args.onhold_threshold_hrs,
        prebacklog_min_days=args.prebacklog_min_days,
        prebacklog_max_days=args.prebacklog_max_days,
        sla_warning_hours=args.sla_warning_hours
    )
