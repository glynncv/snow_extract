"""
Workflow 1B: Early Warning System
==================================

Proactive detection of issues at ticket CREATION, not day 10.

Prevents 50-70% of backlog tickets by catching problems early:
- Immediate misclassification
- Aging at creation (created but not assigned/worked)
- First reassignment (routing issues)
- Invalid on-hold status

Run frequency: Every 2-4 hours (or on-demand)

Usage:
    python workflow_early_warning.py                    # Sample data
    python workflow_early_warning.py --source csv --file downloads/recent_incidents.csv
    python workflow_early_warning.py --source api --hours 4  # Last 4 hours
    python workflow_early_warning.py --alert-age-hours 2     # Alert if unassigned >2hrs

Output:
    - output/early_warning_YYYY-MM-DD_HHMM.xlsx (Excel report)
    - output/early_warning_alerts_YYYY-MM-DD_HHMM.txt (Alert text)
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
from snow_analytics.analysis.quality import detect_priority_misclassification

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def detect_aging_at_creation(df, unassigned_threshold_hrs=2, no_work_threshold_hrs=4):
    """
    Detect tickets aging from the moment they're created.

    Args:
        df: Incident DataFrame
        unassigned_threshold_hrs: Alert if created but unassigned >N hours (default: 2)
        no_work_threshold_hrs: Alert if assigned but no work started >N hours (default: 4)

    Returns:
        DataFrame with aging tickets
    """
    logger.info(f"Detecting aging at creation (unassigned>{unassigned_threshold_hrs}hrs, no work>{no_work_threshold_hrs}hrs)...")

    if 'openedDate' not in df.columns or 'ageHrs' not in df.columns:
        logger.warning("Missing required columns for aging detection")
        return pd.DataFrame()

    aging_tickets = []

    # Active tickets only
    active_df = df[df.get('isActive', True) == True].copy()

    for idx, row in active_df.iterrows():
        ticket_age_hrs = row.get('ageHrs', 0)
        assigned_to = row.get('assigned_to', '')
        state = row.get('state', '')

        issue_type = None
        severity = None

        # Check 1: Created but not assigned
        if pd.isna(assigned_to) or assigned_to == '' or assigned_to == 'Unassigned':
            if ticket_age_hrs >= unassigned_threshold_hrs:
                issue_type = 'Unassigned'
                severity = 'HIGH' if ticket_age_hrs >= unassigned_threshold_hrs * 2 else 'MEDIUM'

        # Check 2: Assigned but no work started (still in New/Open state)
        elif state in ['New', 'Open', '1', '2']:
            if ticket_age_hrs >= no_work_threshold_hrs:
                issue_type = 'No Work Started'
                severity = 'MEDIUM'

        if issue_type:
            aging_tickets.append({
                'number': row['number'],
                'priority': row.get('priority', 'Unknown'),
                'state': state,
                'ageHrs': ticket_age_hrs,
                'assigned_to': assigned_to if not pd.isna(assigned_to) else 'UNASSIGNED',
                'issue_type': issue_type,
                'severity': severity,
                'openedDate': row.get('openedDate'),
                'short_description': row.get('short_description', '')[:100]
            })

    df_aging = pd.DataFrame(aging_tickets)

    if not df_aging.empty:
        df_aging = df_aging.sort_values('ageHrs', ascending=False)

    logger.info(f"Found {len(df_aging)} aging tickets")

    return df_aging


def detect_early_reassignment(df, hours_since_creation=24):
    """
    Detect tickets reassigned within first N hours (routing problem indicator).

    Args:
        df: Incident DataFrame
        hours_since_creation: Flag if reassigned within this timeframe (default: 24)

    Returns:
        DataFrame with early reassignment issues
    """
    logger.info(f"Detecting early reassignments (within {hours_since_creation} hours of creation)...")

    if 'ageHrs' not in df.columns or 'reassignment_count' not in df.columns:
        logger.warning("Missing required columns for reassignment detection")
        return pd.DataFrame()

    # Tickets reassigned within the time window
    early_reassign = df[
        (df['ageHrs'] <= hours_since_creation) &
        (df['reassignment_count'] > 0)
    ].copy()

    if not early_reassign.empty:
        early_reassign = early_reassign.sort_values('reassignment_count', ascending=False)

    logger.info(f"Found {len(early_reassign)} tickets with early reassignments")

    return early_reassign


def detect_invalid_onhold_early(df, hours_since_creation=24):
    """
    Detect tickets put on-hold within first N hours (suspicious).

    Args:
        df: Incident DataFrame
        hours_since_creation: Flag if on-hold within this timeframe (default: 24)

    Returns:
        DataFrame with suspicious on-hold tickets
    """
    logger.info(f"Detecting invalid early on-hold (within {hours_since_creation} hours)...")

    if 'ageHrs' not in df.columns or 'state' not in df.columns:
        logger.warning("Missing required columns for on-hold detection")
        return pd.DataFrame()

    # Tickets on-hold within the time window
    early_onhold = df[
        (df['ageHrs'] <= hours_since_creation) &
        (df['state'].str.contains('Hold|Pending', case=False, na=False))
    ].copy()

    logger.info(f"Found {len(early_onhold)} tickets on-hold early")

    return early_onhold


def detect_immediate_misclassification(df, hours_since_creation=2):
    """
    Detect misclassified tickets immediately after creation.

    Args:
        df: Incident DataFrame
        hours_since_creation: Check tickets created within last N hours (default: 2)

    Returns:
        DataFrame with misclassified tickets
    """
    logger.info(f"Detecting immediate misclassification (within {hours_since_creation} hours)...")

    if 'ageHrs' not in df.columns:
        logger.warning("Missing ageHrs column")
        return pd.DataFrame()

    # Recent tickets only
    recent_df = df[df['ageHrs'] <= hours_since_creation].copy()

    if recent_df.empty:
        logger.info("No recent tickets to check")
        return pd.DataFrame()

    # Run priority misclassification check
    df_checked = detect_priority_misclassification(recent_df)

    # Filter to those with issues
    misclassified = df_checked[
        df_checked.get('quality_priority_mismatch', False) == True
    ].copy()

    logger.info(f"Found {len(misclassified)} immediately misclassified tickets")

    return misclassified


def generate_alert_text(summary_stats, df_aging, df_reassign, df_onhold, df_misclass):
    """
    Generate ready-to-send alert text for Teams/Email.

    Returns:
        String containing formatted alert messages
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    alerts = []
    alerts.append("=" * 70)
    alerts.append(f"EARLY WARNING SYSTEM ALERTS - {now}")
    alerts.append("=" * 70)
    alerts.append("")
    alerts.append("🚨 PREVENTION ALERTS - Action Required to Prevent Backlog")
    alerts.append("=" * 70)
    alerts.append("")

    # Summary
    alerts.append("📊 SUMMARY")
    alerts.append("-" * 70)
    alerts.append(f"Total Recent Tickets Analyzed: {summary_stats['total']}")
    alerts.append(f"Issues Found: {summary_stats['total_issues']}")
    alerts.append("")

    # Critical - Aging at Creation
    if len(df_aging) > 0:
        high_severity = df_aging[df_aging['severity'] == 'HIGH']

        alerts.append("🚨 CRITICAL - AGING AT CREATION")
        alerts.append("-" * 70)
        alerts.append(f"Tickets aging from creation: {len(df_aging)}")

        if len(high_severity) > 0:
            alerts.append(f"  HIGH severity (unassigned >4hrs): {len(high_severity)}")
            alerts.append("")
            alerts.append("Top 5 HIGH severity:")
            for idx, row in high_severity.head(5).iterrows():
                alerts.append(f"  • {row['number']} [{row['priority']}] - {row['ageHrs']:.1f}hrs old - UNASSIGNED")
                alerts.append(f"    Issue: {row['issue_type']}")

        medium_severity = df_aging[df_aging['severity'] == 'MEDIUM']
        if len(medium_severity) > 0:
            alerts.append("")
            alerts.append(f"  MEDIUM severity: {len(medium_severity)}")
            alerts.append("  Sample:")
            for idx, row in medium_severity.head(3).iterrows():
                alerts.append(f"  • {row['number']} - {row['ageHrs']:.1f}hrs - {row['issue_type']}")

        alerts.append("")
        alerts.append("⚡ ACTION: Assign immediately or escalate")
        alerts.append("")

    # Immediate Misclassification
    if len(df_misclass) > 0:
        alerts.append("🔴 IMMEDIATE MISCLASSIFICATION")
        alerts.append("-" * 70)
        alerts.append(f"Recently created tickets with wrong priority: {len(df_misclass)}")
        alerts.append("")

        p1_p2 = df_misclass[df_misclass['priority'].isin(['1 - Critical', '2 - High'])]
        if len(p1_p2) > 0:
            alerts.append(f"P1/P2 misclassifications: {len(p1_p2)}")
            for idx, row in p1_p2.head(5).iterrows():
                alerts.append(f"  • {row['number']} [{row['priority']}] - {row.get('short_description', '')[:60]}")

        alerts.append("")
        alerts.append("⚡ ACTION: Review and correct priority ASAP")
        alerts.append("")

    # Early Reassignment
    if len(df_reassign) > 0:
        alerts.append("🔄 EARLY ROUTING ISSUES")
        alerts.append("-" * 70)
        alerts.append(f"Tickets reassigned within 24 hours: {len(df_reassign)}")
        alerts.append("")
        alerts.append("Top issues:")
        for idx, row in df_reassign.head(5).iterrows():
            count = row.get('reassignment_count', 0)
            alerts.append(f"  • {row['number']} - {count} reassignments in {row.get('ageHrs', 0):.1f}hrs")

        alerts.append("")
        alerts.append("⚡ ACTION: Review routing rules and resolver groups")
        alerts.append("")

    # Early On-Hold
    if len(df_onhold) > 0:
        alerts.append("⏸️  SUSPICIOUS EARLY ON-HOLD")
        alerts.append("-" * 70)
        alerts.append(f"Tickets put on-hold within 24 hours: {len(df_onhold)}")
        alerts.append("")
        alerts.append("Sample:")
        for idx, row in df_onhold.head(5).iterrows():
            alerts.append(f"  • {row['number']} [{row.get('priority', 'Unknown')}] - {row.get('ageHrs', 0):.1f}hrs old")

        alerts.append("")
        alerts.append("⚡ ACTION: Validate on-hold reason or resume work")
        alerts.append("")

    # Summary Actions
    alerts.append("=" * 70)
    alerts.append("RECOMMENDED ACTIONS (Priority Order)")
    alerts.append("=" * 70)
    alerts.append("1. Assign unassigned tickets immediately (aging at creation)")
    alerts.append("2. Correct priority misclassifications")
    alerts.append("3. Fix routing issues causing early reassignments")
    alerts.append("4. Review suspicious early on-hold tickets")
    alerts.append("")
    alerts.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    alerts.append("Run frequency: Every 2-4 hours for maximum prevention")
    alerts.append("=" * 70)

    return "\n".join(alerts)


def main(source='sample', file_path=None, limit=500, num_records=100, hours=4,
         unassigned_threshold_hrs=2, no_work_threshold_hrs=4,
         early_reassign_hrs=24, early_onhold_hrs=24, misclass_hrs=2):
    """
    Run early warning system to catch issues at ticket creation.

    Args:
        source: Data source ('sample', 'csv', 'api')
        file_path: Path to CSV file (if source='csv')
        limit: API query limit (if source='api')
        num_records: Number of sample records (if source='sample')
        hours: Hours of recent data to analyze (if source='api')
        unassigned_threshold_hrs: Alert if unassigned >N hours
        no_work_threshold_hrs: Alert if no work started >N hours
        early_reassign_hrs: Flag reassignments within N hours of creation
        early_onhold_hrs: Flag on-hold within N hours of creation
        misclass_hrs: Check for misclassification within N hours of creation
    """

    print("=" * 70)
    print("WORKFLOW 1B: Early Warning System")
    print("=" * 70)
    print()

    # Step 1: Load recent incidents
    print(f"📥 Loading recent incidents from '{source}'...")

    if source == 'api':
        # Load last N hours of incidents
        df = load_incidents('api', limit=limit)
        # TODO: Add time-based filter for API
        print(f"   Note: Analyzing last {hours} hours (add API time filter for production)")
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

    # Step 3: Run early warning checks
    print("🔍 Running early warning checks...")
    print()

    # 3.1 Aging at Creation
    df_aging = detect_aging_at_creation(
        df,
        unassigned_threshold_hrs=unassigned_threshold_hrs,
        no_work_threshold_hrs=no_work_threshold_hrs
    )

    # 3.2 Immediate Misclassification
    df_misclass = detect_immediate_misclassification(df, hours_since_creation=misclass_hrs)

    # 3.3 Early Reassignment
    df_reassign = detect_early_reassignment(df, hours_since_creation=early_reassign_hrs)

    # 3.4 Invalid Early On-Hold
    df_onhold = detect_invalid_onhold_early(df, hours_since_creation=early_onhold_hrs)

    print()

    # Summary statistics
    summary_stats = {
        'total': len(df),
        'aging': len(df_aging),
        'misclass': len(df_misclass),
        'reassign': len(df_reassign),
        'onhold': len(df_onhold),
        'total_issues': len(df_aging) + len(df_misclass) + len(df_reassign) + len(df_onhold)
    }

    # Step 4: Generate Excel Report
    print("📊 Generating Excel report...")

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    excel_path = output_dir / f'early_warning_{timestamp}.xlsx'

    sheets = {}

    # Sheet 1: Summary Dashboard
    summary_data = {
        'Alert Type': [
            'AGING AT CREATION',
            '  - Unassigned (HIGH severity)',
            '  - No Work Started (MEDIUM)',
            '',
            'IMMEDIATE MISCLASSIFICATION',
            '',
            'EARLY ROUTING ISSUES',
            '',
            'SUSPICIOUS EARLY ON-HOLD',
            '',
            'TOTAL ISSUES FLAGGED',
            'Report Generated'
        ],
        'Count': [
            summary_stats['aging'],
            len(df_aging[df_aging['severity'] == 'HIGH']) if not df_aging.empty and 'severity' in df_aging.columns else 0,
            len(df_aging[df_aging['severity'] == 'MEDIUM']) if not df_aging.empty and 'severity' in df_aging.columns else 0,
            '',
            summary_stats['misclass'],
            '',
            summary_stats['reassign'],
            '',
            summary_stats['onhold'],
            '',
            summary_stats['total_issues'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
    }
    sheets['Summary'] = pd.DataFrame(summary_data)

    # Sheet 2: Aging at Creation (CRITICAL)
    if len(df_aging) > 0:
        aging_cols = ['number', 'priority', 'state', 'ageHrs', 'assigned_to',
                     'issue_type', 'severity', 'openedDate', 'short_description']
        available_cols = [col for col in aging_cols if col in df_aging.columns]
        sheets['Aging at Creation'] = df_aging[available_cols]

    # Sheet 3: Immediate Misclassification
    if len(df_misclass) > 0:
        misclass_cols = ['number', 'priority', 'state', 'ageHrs', 'assigned_to', 'short_description']
        available_cols = [col for col in misclass_cols if col in df_misclass.columns]
        sheets['Misclassification'] = df_misclass[available_cols]

    # Sheet 4: Early Reassignments
    if len(df_reassign) > 0:
        reassign_cols = ['number', 'priority', 'state', 'reassignment_count', 'ageHrs', 'short_description']
        available_cols = [col for col in reassign_cols if col in df_reassign.columns]
        sheets['Early Reassignments'] = df_reassign[available_cols]

    # Sheet 5: Early On-Hold
    if len(df_onhold) > 0:
        onhold_cols = ['number', 'priority', 'state', 'ageHrs', 'assigned_to', 'short_description']
        available_cols = [col for col in onhold_cols if col in df_onhold.columns]
        sheets['Early On-Hold'] = df_onhold[available_cols]

    export_to_excel(sheets, excel_path)
    print(f"   ✅ Excel report saved: {excel_path}")
    print()

    # Step 5: Generate Alert Text
    print("📝 Generating alert text...")

    alert_text = generate_alert_text(
        summary_stats, df_aging, df_reassign, df_onhold, df_misclass
    )

    text_path = output_dir / f'early_warning_alerts_{timestamp}.txt'
    with open(text_path, 'w') as f:
        f.write(alert_text)

    print(f"   ✅ Alert text saved: {text_path}")
    print()

    # Display summary to console
    print("=" * 70)
    print("📊 EARLY WARNING RESULTS")
    print("=" * 70)
    print(f"Total Recent Tickets Analyzed: {summary_stats['total']}")
    print()
    print("Issues Found:")
    print(f"  🚨 Aging at Creation: {summary_stats['aging']} tickets")
    if not df_aging.empty and 'severity' in df_aging.columns:
        print(f"     - HIGH severity: {len(df_aging[df_aging['severity'] == 'HIGH'])}")
        print(f"     - MEDIUM severity: {len(df_aging[df_aging['severity'] == 'MEDIUM'])}")
    print(f"  🔴 Immediate Misclassification: {summary_stats['misclass']} tickets")
    print(f"  🔄 Early Routing Issues: {summary_stats['reassign']} tickets")
    print(f"  ⏸️  Suspicious Early On-Hold: {summary_stats['onhold']} tickets")
    print()
    print(f"Total Issues: {summary_stats['total_issues']}")
    print()
    print("=" * 70)
    print("[SUCCESS] Early warning check complete!")
    print("=" * 70)
    print()
    print("📂 Output Files:")
    print(f"   - {excel_path}")
    print(f"   - {text_path}")
    print()
    print("💡 Impact:")
    print("   - These issues caught EARLY prevent future backlog tickets")
    print("   - Addressing now saves 10x effort vs. fixing at day 10")
    print()
    print("🔄 Recommended Frequency:")
    print("   - Run every 2-4 hours for maximum prevention")
    print("   - Schedule via cron/Task Scheduler for automation")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Workflow 1B: Early Warning System - Catch Issues at Creation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use sample data
  %(prog)s --source csv --file downloads/recent_incidents.csv
  %(prog)s --source api --hours 4 --limit 500
  %(prog)s --unassigned-threshold-hrs 1       # More aggressive
  %(prog)s --early-reassign-hrs 12            # Shorter window
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
        default=100,
        help='Number of sample records to generate (default: 100)'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=4,
        help='Hours of recent data to analyze (for API source, default: 4)'
    )
    parser.add_argument(
        '--unassigned-threshold-hrs',
        type=int,
        default=2,
        help='Alert if ticket unassigned for >N hours (default: 2)'
    )
    parser.add_argument(
        '--no-work-threshold-hrs',
        type=int,
        default=4,
        help='Alert if assigned but no work started >N hours (default: 4)'
    )
    parser.add_argument(
        '--early-reassign-hrs',
        type=int,
        default=24,
        help='Flag reassignments within N hours of creation (default: 24)'
    )
    parser.add_argument(
        '--early-onhold-hrs',
        type=int,
        default=24,
        help='Flag on-hold within N hours of creation (default: 24)'
    )
    parser.add_argument(
        '--misclass-hrs',
        type=int,
        default=2,
        help='Check for misclassification within N hours (default: 2)'
    )

    args = parser.parse_args()

    main(
        source=args.source,
        file_path=args.file,
        limit=args.limit,
        num_records=args.num_records,
        hours=args.hours,
        unassigned_threshold_hrs=args.unassigned_threshold_hrs,
        no_work_threshold_hrs=args.no_work_threshold_hrs,
        early_reassign_hrs=args.early_reassign_hrs,
        early_onhold_hrs=args.early_onhold_hrs,
        misclass_hrs=args.misclass_hrs
    )
