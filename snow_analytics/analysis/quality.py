"""
Incident Quality Checks
=======================

Quality analysis for ServiceNow incidents.
"""

import pandas as pd
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def check_incident_quality(
    df: pd.DataFrame,
    quality_rules: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Perform comprehensive quality checks on incidents.

    Args:
        df: DataFrame with incident data
        quality_rules: Custom quality rules (optional)

    Returns:
        DataFrame with quality flags added
    """
    logger.info("Performing incident quality checks")

    df_quality = df.copy()

    # Apply individual quality checks
    df_quality = detect_priority_misclassification(df_quality)
    df_quality = detect_on_hold_abuse(df_quality)
    df_quality = check_description_quality(df_quality)
    df_quality = flag_excessive_reassignments(df_quality)

    # Count total quality issues per incident
    quality_columns = [col for col in df_quality.columns if col.startswith('quality_')]
    if quality_columns:
        df_quality['quality_issues_count'] = df_quality[quality_columns].sum(axis=1)

    logger.info(f"Quality checks complete. Found issues in {(df_quality['quality_issues_count'] > 0).sum()} incidents")

    return df_quality


def detect_priority_misclassification(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect potential priority misclassification.

    Flags incidents where priority doesn't match resolution time or impact.
    """
    df_check = df.copy()
    df_check['quality_priority_mismatch'] = False

    if 'priority' in df_check.columns and 'resolutionTimeHrs' in df_check.columns:
        # Critical priority but slow resolution
        critical_mask = df_check['priority'].astype(str).str.contains('1 - Critical', na=False)
        slow_resolution = df_check['resolutionTimeHrs'] > 24

        df_check.loc[critical_mask & slow_resolution, 'quality_priority_mismatch'] = True

    return df_check


def detect_on_hold_abuse(df: pd.DataFrame, threshold_hours: int = 72) -> pd.DataFrame:
    """
    Detect incidents with excessive On Hold time.
    """
    df_check = df.copy()
    df_check['quality_on_hold_abuse'] = False

    if 'state' in df_check.columns and 'ageHrs' in df_check.columns:
        on_hold_mask = df_check['state'] == 'On Hold'
        excessive_age = df_check['ageHrs'] > threshold_hours

        df_check.loc[on_hold_mask & excessive_age, 'quality_on_hold_abuse'] = True

    return df_check


def check_description_quality(df: pd.DataFrame, min_length: int = 20) -> pd.DataFrame:
    """
    Check quality of incident descriptions.
    """
    df_check = df.copy()
    df_check['quality_poor_description'] = False

    if 'short_description' in df_check.columns:
        desc_length = df_check['short_description'].astype(str).str.len()
        df_check.loc[desc_length < min_length, 'quality_poor_description'] = True

    return df_check


def flag_excessive_reassignments(df: pd.DataFrame, threshold: int = 3) -> pd.DataFrame:
    """
    Flag incidents with excessive reassignments.
    """
    df_check = df.copy()
    df_check['quality_excessive_reassignments'] = False

    if 'reassignment_count' in df_check.columns:
        df_check.loc[df_check['reassignment_count'] > threshold, 'quality_excessive_reassignments'] = True

    return df_check
