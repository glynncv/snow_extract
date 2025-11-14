"""
Data Validation Module
======================

Schema and data validation for ServiceNow incidents.
"""

import pandas as pd
import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


def validate_incident_schema(
    df: pd.DataFrame,
    required_columns: List[str] = None,
    warn_only: bool = True
) -> Tuple[bool, List[str]]:
    """
    Validate that DataFrame has expected incident schema.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names.
                         If None, uses minimal required set.
        warn_only: If True, only log warnings instead of failing validation

    Returns:
        Tuple of (is_valid, list_of_issues)

    Examples:
        >>> is_valid, issues = validate_incident_schema(df)
        >>> if not is_valid:
        >>>     print(f"Validation failed: {issues}")
    """
    if required_columns is None:
        # Minimal required columns for incident processing
        required_columns = [
            'number',
            'short_description',
            'priority',
            'state'
        ]

    issues = []

    # Check for empty DataFrame
    if df.empty:
        issues.append("DataFrame is empty")
        return False, issues

    # Check for required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        issue = f"Missing required columns: {missing_columns}"
        issues.append(issue)

        if not warn_only:
            logger.error(issue)
            return False, issues
        else:
            logger.warning(issue)

    # Check for completely null columns
    null_columns = [col for col in df.columns if df[col].isna().all()]
    if null_columns:
        issue = f"Columns with all null values: {null_columns}"
        issues.append(issue)
        logger.warning(issue)

    # Check for duplicate incident numbers
    if 'number' in df.columns:
        duplicate_count = df['number'].duplicated().sum()
        if duplicate_count > 0:
            issue = f"Found {duplicate_count} duplicate incident numbers"
            issues.append(issue)
            logger.warning(issue)

    # Data type checks
    date_columns = ['openedDate', 'resolvedDate', 'closedDate', 'opened_at', 'resolved_at']
    for col in date_columns:
        if col in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                issue = f"Column {col} is not datetime type. Consider using parse_dates()"
                issues.append(issue)
                logger.debug(issue)

    # Summary
    if issues:
        logger.info(f"Schema validation found {len(issues)} issues")
    else:
        logger.debug("Schema validation passed")

    is_valid = len(issues) == 0 or warn_only

    return is_valid, issues


def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate data quality and return quality metrics.

    Args:
        df: DataFrame to validate

    Returns:
        Dictionary with quality metrics and issues
    """
    logger.info("Validating data quality")

    quality_report = {
        'total_records': len(df),
        'issues': [],
        'warnings': [],
        'null_percentages': {},
        'data_quality_score': 100.0
    }

    if df.empty:
        quality_report['issues'].append("DataFrame is empty")
        quality_report['data_quality_score'] = 0.0
        return quality_report

    # Calculate null percentages for all columns
    for col in df.columns:
        null_pct = (df[col].isna().sum() / len(df)) * 100
        quality_report['null_percentages'][col] = round(null_pct, 2)

        if null_pct > 50:
            quality_report['warnings'].append(
                f"Column '{col}' has {null_pct:.1f}% null values"
            )

    # Check for missing critical data
    critical_columns = ['number', 'short_description', 'priority', 'opened_at', 'state']
    for col in critical_columns:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                quality_report['issues'].append(
                    f"Critical column '{col}' has {null_count} null values"
                )

    # Check short description quality
    if 'short_description' in df.columns:
        short_desc_lengths = df['short_description'].astype(str).str.len()
        very_short = (short_desc_lengths < 10).sum()

        if very_short > 0:
            quality_report['warnings'].append(
                f"{very_short} incidents have very short descriptions (< 10 chars)"
            )

    # Check for invalid priority values
    if 'priority' in df.columns:
        valid_priorities = ['1 - Critical', '2 - High', '3 - Moderate', '4 - Low', '1', '2', '3', '4']
        invalid_priorities = ~df['priority'].astype(str).isin(valid_priorities + ['nan', 'None', ''])
        invalid_count = invalid_priorities.sum()

        if invalid_count > 0:
            quality_report['warnings'].append(
                f"{invalid_count} incidents have invalid priority values"
            )

    # Calculate overall quality score
    # Deduct points for issues and warnings
    quality_score = 100.0
    quality_score -= len(quality_report['issues']) * 10  # -10 points per issue
    quality_score -= len(quality_report['warnings']) * 3  # -3 points per warning

    # Deduct for high null percentages in critical columns
    for col in critical_columns:
        if col in quality_report['null_percentages']:
            null_pct = quality_report['null_percentages'][col]
            if null_pct > 0:
                quality_score -= null_pct * 0.5

    quality_report['data_quality_score'] = max(0.0, round(quality_score, 2))

    logger.info(f"Data quality score: {quality_report['data_quality_score']}/100")

    return quality_report
