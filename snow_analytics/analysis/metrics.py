"""
Metrics and KPI Calculations
============================

Calculate SLA, resolution times, backlog, and other key performance indicators.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_sla_metrics(
    df: pd.DataFrame,
    sla_rules: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Calculate SLA performance metrics.

    Args:
        df: DataFrame with resolved incidents (must have 'slaBreach' column)
        sla_rules: SLA thresholds by priority (hours)

    Returns:
        Dictionary with SLA metrics

    Examples:
        >>> metrics = calculate_sla_metrics(df)
        >>> print(f"SLA breach rate: {metrics['breach_rate_pct']}%")
    """
    logger.info("Calculating SLA metrics")

    metrics = {
        'total_resolved': 0,
        'sla_breached': 0,
        'sla_met': 0,
        'breach_rate_pct': 0.0,
        'by_priority': {}
    }

    # Filter to resolved incidents
    if 'resolutionTimeHrs' not in df.columns:
        logger.warning("resolutionTimeHrs column not found. Run transform_incidents() first.")
        return metrics

    resolved_df = df[df['resolutionTimeHrs'].notna()].copy()

    if resolved_df.empty:
        logger.warning("No resolved incidents found")
        return metrics

    metrics['total_resolved'] = len(resolved_df)

    # Overall SLA metrics
    if 'slaBreach' in resolved_df.columns:
        metrics['sla_breached'] = int(resolved_df['slaBreach'].sum())
        metrics['sla_met'] = int((~resolved_df['slaBreach']).sum())
        metrics['breach_rate_pct'] = round(
            (metrics['sla_breached'] / metrics['total_resolved']) * 100, 2
        )

    # SLA metrics by priority
    if 'priority' in resolved_df.columns:
        for priority in resolved_df['priority'].unique():
            if pd.isna(priority):
                continue

            priority_df = resolved_df[resolved_df['priority'] == priority]

            if 'slaBreach' in priority_df.columns:
                breached = int(priority_df['slaBreach'].sum())
                total = len(priority_df)
                breach_rate = round((breached / total) * 100, 2) if total > 0 else 0.0

                metrics['by_priority'][str(priority)] = {
                    'total': total,
                    'breached': breached,
                    'met': total - breached,
                    'breach_rate_pct': breach_rate
                }

    logger.info(f"SLA breach rate: {metrics['breach_rate_pct']}% ({metrics['sla_breached']}/{metrics['total_resolved']})")

    return metrics


def analyze_resolution_times(
    df: pd.DataFrame,
    by_priority: bool = True,
    by_category: bool = True
) -> Dict[str, Any]:
    """
    Analyze resolution time statistics.

    Args:
        df: DataFrame with incident data
        by_priority: Include breakdown by priority
        by_category: Include breakdown by category

    Returns:
        Dictionary with resolution time statistics
    """
    logger.info("Analyzing resolution times")

    analysis = {
        'overall': {},
        'by_priority': {},
        'by_category': {}
    }

    # Filter to resolved incidents
    if 'resolutionTimeHrs' not in df.columns:
        logger.warning("resolutionTimeHrs column not found")
        return analysis

    resolved_df = df[df['resolutionTimeHrs'].notna()].copy()

    if resolved_df.empty:
        logger.warning("No resolved incidents found")
        return analysis

    # Overall statistics
    resolution_times = resolved_df['resolutionTimeHrs']

    analysis['overall'] = {
        'count': len(resolution_times),
        'mean_hrs': round(resolution_times.mean(), 2),
        'median_hrs': round(resolution_times.median(), 2),
        'min_hrs': round(resolution_times.min(), 2),
        'max_hrs': round(resolution_times.max(), 2),
        'std_dev_hrs': round(resolution_times.std(), 2),
        'percentile_90_hrs': round(resolution_times.quantile(0.9), 2),
        'percentile_95_hrs': round(resolution_times.quantile(0.95), 2)
    }

    # By priority
    if by_priority and 'priority' in resolved_df.columns:
        for priority in resolved_df['priority'].unique():
            if pd.isna(priority):
                continue

            priority_times = resolved_df[resolved_df['priority'] == priority]['resolutionTimeHrs']

            if len(priority_times) > 0:
                analysis['by_priority'][str(priority)] = {
                    'count': len(priority_times),
                    'mean_hrs': round(priority_times.mean(), 2),
                    'median_hrs': round(priority_times.median(), 2)
                }

    # By category
    if by_category and 'patternCategory' in resolved_df.columns:
        for category in resolved_df['patternCategory'].unique():
            if pd.isna(category):
                continue

            category_times = resolved_df[resolved_df['patternCategory'] == category]['resolutionTimeHrs']

            if len(category_times) > 0:
                analysis['by_category'][str(category)] = {
                    'count': len(category_times),
                    'mean_hrs': round(category_times.mean(), 2),
                    'median_hrs': round(category_times.median(), 2)
                }

    logger.info(f"Average resolution time: {analysis['overall']['mean_hrs']} hours")

    return analysis


def calculate_backlog_metrics(
    df: pd.DataFrame,
    snapshot_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Calculate backlog metrics for active incidents.

    Args:
        df: DataFrame with incident data
        snapshot_date: Date for snapshot (defaults to now)

    Returns:
        Dictionary with backlog metrics
    """
    logger.info("Calculating backlog metrics")

    if snapshot_date is None:
        snapshot_date = datetime.now()

    metrics = {
        'snapshot_date': snapshot_date.isoformat(),
        'total_backlog': 0,
        'by_priority': {},
        'by_age': {
            'less_than_24h': 0,
            '24h_to_3days': 0,
            '3days_to_1week': 0,
            '1week_to_1month': 0,
            'more_than_1month': 0
        },
        'avg_age_days': 0.0
    }

    # Filter to active incidents
    if 'isActive' not in df.columns:
        logger.warning("isActive column not found. Run transform_incidents() first.")
        return metrics

    active_df = df[df['isActive']].copy()

    if active_df.empty:
        logger.info("No active incidents in backlog")
        return metrics

    metrics['total_backlog'] = len(active_df)

    # Calculate age for each active incident
    if 'openedDate' in active_df.columns:
        active_df['current_age_days'] = (
            pd.Timestamp(snapshot_date) - active_df['openedDate']
        ).dt.total_seconds() / (3600 * 24)

        metrics['avg_age_days'] = round(active_df['current_age_days'].mean(), 2)

        # Age distribution
        metrics['by_age']['less_than_24h'] = int((active_df['current_age_days'] < 1).sum())
        metrics['by_age']['24h_to_3days'] = int(
            ((active_df['current_age_days'] >= 1) & (active_df['current_age_days'] < 3)).sum()
        )
        metrics['by_age']['3days_to_1week'] = int(
            ((active_df['current_age_days'] >= 3) & (active_df['current_age_days'] < 7)).sum()
        )
        metrics['by_age']['1week_to_1month'] = int(
            ((active_df['current_age_days'] >= 7) & (active_df['current_age_days'] < 30)).sum()
        )
        metrics['by_age']['more_than_1month'] = int((active_df['current_age_days'] >= 30).sum())

    # By priority
    if 'priority' in active_df.columns:
        for priority in active_df['priority'].unique():
            if pd.isna(priority):
                continue

            priority_count = len(active_df[active_df['priority'] == priority])
            metrics['by_priority'][str(priority)] = priority_count

    logger.info(f"Total backlog: {metrics['total_backlog']} incidents (avg age: {metrics['avg_age_days']} days)")

    return metrics


def analyze_reassignments(
    df: pd.DataFrame,
    threshold: int = 2
) -> pd.DataFrame:
    """
    Analyze incidents with excessive reassignments.

    Args:
        df: DataFrame with incident data
        threshold: Minimum reassignment count to flag

    Returns:
        DataFrame with flagged incidents and statistics
    """
    logger.info(f"Analyzing reassignments (threshold={threshold})")

    if 'reassignment_count' not in df.columns:
        logger.warning("reassignment_count column not found")
        return pd.DataFrame()

    # Flag incidents with excessive reassignments
    excessive_reassignments = df[df['reassignment_count'] > threshold].copy()

    if excessive_reassignments.empty:
        logger.info(f"No incidents found with > {threshold} reassignments")
        return pd.DataFrame()

    # Add reassignment severity flag
    def classify_reassignment_severity(count):
        if count > 5:
            return 'Critical'
        elif count > 3:
            return 'High'
        else:
            return 'Moderate'

    excessive_reassignments['reassignment_severity'] = excessive_reassignments['reassignment_count'].apply(
        classify_reassignment_severity
    )

    logger.info(f"Found {len(excessive_reassignments)} incidents with > {threshold} reassignments")

    return excessive_reassignments[['number', 'short_description', 'priority', 'assignment_group',
                                     'reassignment_count', 'reassignment_severity']]
