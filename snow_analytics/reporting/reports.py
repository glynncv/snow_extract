"""
Report Generation Templates
===========================

Pre-built report templates for common ServiceNow analytics workflows.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from snow_analytics.analysis.metrics import (
    calculate_sla_metrics,
    analyze_resolution_times,
    calculate_backlog_metrics
)
from snow_analytics.analysis.quality import check_incident_quality
from snow_analytics.analysis.patterns import analyze_patterns
from snow_analytics.reporting.exporters import export_to_excel, export_to_json

logger = logging.getLogger(__name__)


def generate_sla_report(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    format: str = 'excel',
    sla_rules: Optional[Dict] = None
) -> Path:
    """
    Generate comprehensive SLA compliance report.

    Creates a multi-sheet Excel report or JSON with:
    - Overall SLA metrics
    - SLA compliance by priority
    - SLA breaches (detailed incidents)
    - Resolution time analysis

    Args:
        df: Transformed incident DataFrame
        output_path: Output file path
        format: 'excel' or 'json'
        sla_rules: Optional custom SLA rules

    Returns:
        Path: Path to generated report

    Examples:
        >>> df = load_incidents('api', limit=500)
        >>> df = transform_incidents(df)
        >>> generate_sla_report(df, 'reports/sla_report.xlsx')
    """
    logger.info("Generating SLA compliance report...")

    # Calculate metrics
    sla_metrics = calculate_sla_metrics(df, sla_rules=sla_rules)
    resolution_analysis = analyze_resolution_times(df, by_priority=True)

    # Identify breaches
    breaches_df = df[df.get('slaBreached', False) == True].copy() if 'slaBreached' in df.columns else pd.DataFrame()

    if format.lower() == 'excel':
        # Multi-sheet Excel report
        sheets = {}

        # Sheet 1: Summary metrics
        summary_data = {
            'Metric': [
                'Total Resolved Incidents',
                'SLA Breached',
                'SLA Met',
                'Breach Rate (%)',
                'Average Resolution Time (hrs)',
                'Median Resolution Time (hrs)',
                'Report Generated'
            ],
            'Value': [
                sla_metrics.get('total_resolved', 0),
                sla_metrics.get('sla_breached', 0),
                sla_metrics.get('sla_met', 0),
                f"{sla_metrics.get('breach_rate_pct', 0):.2f}",
                f"{resolution_analysis['overall']['mean_hrs']:.2f}",
                f"{resolution_analysis['overall']['median_hrs']:.2f}",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        sheets['Summary'] = pd.DataFrame(summary_data)

        # Sheet 2: By Priority
        if 'by_priority' in sla_metrics:
            priority_data = []
            for priority, stats in sla_metrics['by_priority'].items():
                priority_data.append({
                    'Priority': priority,
                    'Total': stats.get('total', 0),
                    'Breached': stats.get('breached', 0),
                    'Met': stats.get('met', 0),
                    'Breach Rate (%)': f"{stats.get('breach_rate_pct', 0):.2f}"
                })
            sheets['By Priority'] = pd.DataFrame(priority_data)

        # Sheet 3: SLA Breaches (detailed)
        if not breaches_df.empty:
            breach_columns = ['number', 'priority', 'state', 'openedDate', 'resolvedDate',
                            'resolutionTimeHrs', 'slaTarget', 'short_description']
            available_cols = [col for col in breach_columns if col in breaches_df.columns]
            sheets['SLA Breaches'] = breaches_df[available_cols]

        # Sheet 4: Resolution Times by Priority
        if 'by_priority' in resolution_analysis:
            resolution_data = []
            for priority, stats in resolution_analysis['by_priority'].items():
                resolution_data.append({
                    'Priority': priority,
                    'Count': stats.get('count', 0),
                    'Mean (hrs)': f"{stats.get('mean_hrs', 0):.2f}",
                    'Median (hrs)': f"{stats.get('median_hrs', 0):.2f}",
                    'Min (hrs)': f"{stats.get('min_hrs', 0):.2f}",
                    'Max (hrs)': f"{stats.get('max_hrs', 0):.2f}"
                })
            sheets['Resolution Times'] = pd.DataFrame(resolution_data)

        return export_to_excel(sheets, output_path)

    elif format.lower() == 'json':
        # JSON report
        report = {
            'report_type': 'SLA Compliance Report',
            'generated_at': datetime.now().isoformat(),
            'summary': sla_metrics,
            'resolution_analysis': resolution_analysis,
            'breach_count': len(breaches_df)
        }
        return export_to_json(report, output_path)

    else:
        raise ValueError(f"Unsupported format: {format}. Use 'excel' or 'json'")


def generate_backlog_report(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    format: str = 'excel',
    snapshot_date: Optional[datetime] = None
) -> Path:
    """
    Generate incident backlog analysis report.

    Args:
        df: Transformed incident DataFrame
        output_path: Output file path
        format: 'excel' or 'json'
        snapshot_date: Date for backlog calculation (default: now)

    Returns:
        Path: Path to generated report

    Examples:
        >>> generate_backlog_report(df, 'reports/backlog.xlsx')
    """
    logger.info("Generating backlog report...")

    backlog_metrics = calculate_backlog_metrics(df, snapshot_date=snapshot_date)

    # Get active incidents
    active_df = df[df.get('isActive', False) == True].copy() if 'isActive' in df.columns else pd.DataFrame()

    if format.lower() == 'excel':
        sheets = {}

        # Summary
        summary_data = {
            'Metric': [
                'Total Active Incidents',
                'Average Age (days)',
                'Oldest Incident (days)',
                'High Priority Count',
                'Critical Priority Count',
                'Report Generated'
            ],
            'Value': [
                backlog_metrics.get('total_active', 0),
                f"{backlog_metrics.get('avg_age_days', 0):.2f}",
                f"{backlog_metrics.get('oldest_age_days', 0):.2f}",
                backlog_metrics.get('high_priority_count', 0),
                backlog_metrics.get('critical_priority_count', 0),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        sheets['Summary'] = pd.DataFrame(summary_data)

        # Active incidents detail
        if not active_df.empty:
            detail_columns = ['number', 'priority', 'state', 'openedDate',
                            'ageDays', 'assigned_to', 'short_description']
            available_cols = [col for col in detail_columns if col in active_df.columns]
            sheets['Active Incidents'] = active_df[available_cols].sort_values(
                by='ageDays' if 'ageDays' in active_df.columns else 'openedDate',
                ascending=False
            )

        # By Priority
        if 'by_priority' in backlog_metrics:
            priority_data = []
            for priority, count in backlog_metrics['by_priority'].items():
                priority_data.append({'Priority': priority, 'Count': count})
            sheets['By Priority'] = pd.DataFrame(priority_data)

        return export_to_excel(sheets, output_path)

    elif format.lower() == 'json':
        report = {
            'report_type': 'Backlog Report',
            'generated_at': datetime.now().isoformat(),
            'snapshot_date': snapshot_date.isoformat() if snapshot_date else datetime.now().isoformat(),
            'metrics': backlog_metrics
        }
        return export_to_json(report, output_path)

    else:
        raise ValueError(f"Unsupported format: {format}")


def generate_quality_report(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    format: str = 'excel',
    quality_rules: Optional[Dict] = None
) -> Path:
    """
    Generate data quality and process compliance report.

    Args:
        df: Transformed incident DataFrame
        output_path: Output file path
        format: 'excel' or 'json'
        quality_rules: Optional custom quality rules

    Returns:
        Path: Path to generated report

    Examples:
        >>> generate_quality_report(df, 'reports/quality.xlsx')
    """
    logger.info("Generating quality report...")

    df_quality = check_incident_quality(df, quality_rules=quality_rules)

    # Get incidents with quality issues
    issues_df = df_quality[df_quality.get('quality_issues_count', 0) > 0].copy()

    if format.lower() == 'excel':
        sheets = {}

        # Summary
        total_incidents = len(df_quality)
        issues_count = len(issues_df)
        quality_score = ((total_incidents - issues_count) / total_incidents * 100) if total_incidents > 0 else 0

        summary_data = {
            'Metric': [
                'Total Incidents Checked',
                'Incidents with Issues',
                'Quality Score (%)',
                'Report Generated'
            ],
            'Value': [
                total_incidents,
                issues_count,
                f"{quality_score:.2f}",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        sheets['Summary'] = pd.DataFrame(summary_data)

        # Quality issues detail
        if not issues_df.empty:
            issue_columns = ['number', 'priority', 'state', 'quality_issues_count',
                           'quality_issues', 'short_description']
            available_cols = [col for col in issue_columns if col in issues_df.columns]
            sheets['Quality Issues'] = issues_df[available_cols]

        return export_to_excel(sheets, output_path)

    elif format.lower() == 'json':
        report = {
            'report_type': 'Quality Report',
            'generated_at': datetime.now().isoformat(),
            'total_incidents': len(df_quality),
            'incidents_with_issues': len(issues_df),
            'quality_issues': issues_df.to_dict('records') if not issues_df.empty else []
        }
        return export_to_json(report, output_path)

    else:
        raise ValueError(f"Unsupported format: {format}")


def generate_executive_summary(
    df: pd.DataFrame,
    output_path: Union[str, Path],
    format: str = 'excel'
) -> Path:
    """
    Generate executive dashboard summary report.

    Combines SLA, backlog, quality, and pattern analysis into a single report.

    Args:
        df: Transformed incident DataFrame
        output_path: Output file path
        format: 'excel' or 'json'

    Returns:
        Path: Path to generated report

    Examples:
        >>> generate_executive_summary(df, 'reports/executive_summary.xlsx')
    """
    logger.info("Generating executive summary...")

    # Calculate all metrics
    sla_metrics = calculate_sla_metrics(df)
    backlog_metrics = calculate_backlog_metrics(df)
    resolution_analysis = analyze_resolution_times(df)
    patterns = analyze_patterns(df)

    if format.lower() == 'excel':
        sheets = {}

        # Executive Summary Sheet
        summary_data = {
            'Category': [
                'SLA COMPLIANCE',
                '  Total Resolved',
                '  SLA Breach Rate (%)',
                '',
                'BACKLOG',
                '  Active Incidents',
                '  Average Age (days)',
                '',
                'RESOLUTION TIMES',
                '  Average (hours)',
                '  Median (hours)',
                '',
                'PATTERNS',
                '  Recurring Issues',
                '',
                'Report Generated'
            ],
            'Value': [
                '',
                sla_metrics.get('total_resolved', 0),
                f"{sla_metrics.get('breach_rate_pct', 0):.2f}",
                '',
                '',
                backlog_metrics.get('total_active', 0),
                f"{backlog_metrics.get('avg_age_days', 0):.2f}",
                '',
                '',
                f"{resolution_analysis['overall']['mean_hrs']:.2f}",
                f"{resolution_analysis['overall']['median_hrs']:.2f}",
                '',
                '',
                len(patterns.get('recurring_issues', [])),
                '',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        sheets['Executive Summary'] = pd.DataFrame(summary_data)

        # Top Issues by Category
        if 'patternCategory' in df.columns:
            category_counts = df['patternCategory'].value_counts().head(10)
            sheets['Top Categories'] = pd.DataFrame({
                'Category': category_counts.index,
                'Count': category_counts.values
            })

        # SLA by Priority
        if 'by_priority' in sla_metrics:
            priority_data = []
            for priority, stats in sla_metrics['by_priority'].items():
                priority_data.append({
                    'Priority': priority,
                    'Total': stats.get('total', 0),
                    'Breach Rate (%)': f"{stats.get('breach_rate_pct', 0):.2f}"
                })
            sheets['SLA by Priority'] = pd.DataFrame(priority_data)

        return export_to_excel(sheets, output_path)

    elif format.lower() == 'json':
        report = {
            'report_type': 'Executive Summary',
            'generated_at': datetime.now().isoformat(),
            'sla_compliance': sla_metrics,
            'backlog': backlog_metrics,
            'resolution_times': resolution_analysis,
            'patterns': {
                'recurring_issues_count': len(patterns.get('recurring_issues', []))
            }
        }
        return export_to_json(report, output_path)

    else:
        raise ValueError(f"Unsupported format: {format}")
