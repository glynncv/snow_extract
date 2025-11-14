"""
Pattern Analysis
===============

Detect patterns and recurring issues in ServiceNow incidents.
"""

import pandas as pd
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def analyze_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze incident patterns and trends.

    Args:
        df: DataFrame with incident data

    Returns:
        Dictionary with pattern analysis results
    """
    logger.info("Analyzing incident patterns")

    analysis = {
        'category_distribution': {},
        'priority_distribution': {},
        'temporal_patterns': {},
        'recurring_issues': []
    }

    # Category distribution
    if 'patternCategory' in df.columns:
        analysis['category_distribution'] = df['patternCategory'].value_counts().to_dict()

    # Priority distribution
    if 'priority' in df.columns:
        analysis['priority_distribution'] = df['priority'].value_counts().to_dict()

    # Temporal patterns
    if 'dayOfWeek' in df.columns:
        analysis['temporal_patterns']['by_day_of_week'] = df['dayOfWeek'].value_counts().sort_index().to_dict()

    if 'hourOfDay' in df.columns:
        analysis['temporal_patterns']['by_hour'] = df['hourOfDay'].value_counts().sort_index().to_dict()

    # Find recurring issues
    analysis['recurring_issues'] = find_recurring_issues(df)

    return analysis


def find_recurring_issues(df: pd.DataFrame, min_occurrences: int = 3) -> List[Dict[str, Any]]:
    """
    Identify recurring incident patterns.

    Args:
        df: DataFrame with incident data
        min_occurrences: Minimum occurrences to consider as recurring

    Returns:
        List of recurring issue patterns
    """
    recurring = []

    if 'patternCategory' not in df.columns or 'cmdb_ci' not in df.columns:
        return recurring

    # Group by category and CI
    grouped = df.groupby(['patternCategory', 'cmdb_ci']).size().reset_index(name='count')
    recurring_df = grouped[grouped['count'] >= min_occurrences].sort_values('count', ascending=False)

    for _, row in recurring_df.iterrows():
        recurring.append({
            'category': row['patternCategory'],
            'ci': row['cmdb_ci'],
            'occurrences': int(row['count'])
        })

    logger.info(f"Found {len(recurring)} recurring issue patterns")

    return recurring
