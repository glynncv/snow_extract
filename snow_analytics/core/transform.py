"""
Data Transformation Module
==========================

ETL transformations for ServiceNow incident data.
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from snow_analytics.core.config import Config

logger = logging.getLogger(__name__)


def transform_incidents(
    df: pd.DataFrame,
    transformations: List[str] = None,
    config: Optional[Config] = None
) -> pd.DataFrame:
    """
    Apply ETL transformations to incident data.

    Args:
        df: Raw incident DataFrame
        transformations: List of transformations to apply.
                        If None or contains 'all', applies all transformations.
                        Options: 'normalize', 'dates', 'status', 'categorization', 'durations', 'sla'
        config: Configuration object

    Returns:
        Transformed DataFrame

    Examples:
        >>> # Apply all transformations
        >>> df_transformed = transform_incidents(df_raw)

        >>> # Apply specific transformations
        >>> df_transformed = transform_incidents(df_raw, transformations=['dates', 'status', 'durations'])
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for transformation")
        return df

    if config is None:
        config = Config()

    if transformations is None or 'all' in transformations:
        transformations = ['normalize', 'dates', 'status', 'categorization', 'durations', 'sla', 'impact']

    logger.info(f"Starting transformations: {transformations}")

    df_transformed = df.copy()

    if 'normalize' in transformations:
        df_transformed = normalize_columns(df_transformed)

    if 'dates' in transformations:
        df_transformed = parse_dates(df_transformed)

    if 'status' in transformations:
        df_transformed = add_status_fields(df_transformed)

    if 'categorization' in transformations:
        categorization_rules = config.get('categorization.rules')
        df_transformed = add_categorization(df_transformed, rules=categorization_rules)

    if 'durations' in transformations:
        df_transformed = calculate_durations(df_transformed)

    if 'sla' in transformations:
        sla_rules = config.get('sla.rules')
        df_transformed = calculate_sla_breach(df_transformed, sla_rules=sla_rules)

    if 'impact' in transformations:
        df_transformed = estimate_user_impact(df_transformed)

    if 'temporal' in transformations:
        df_transformed = add_temporal_fields(df_transformed)

    logger.info(f"Transformation complete. Added {len(df_transformed.columns) - len(df.columns)} new columns")

    return df_transformed


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to standard format.

    Args:
        df: DataFrame with raw column names

    Returns:
        DataFrame with normalized column names
    """
    logger.debug("Normalizing column names")

    column_mapping = {
        'incident_state': 'state',
        'opened': 'openedDate',
        'opened_at': 'openedDate',
        'resolved': 'resolvedDate',
        'resolved_at': 'resolvedDate',
        'u_resolved': 'resolvedDate',
        'u_ci_type': 'ci_type',
    }

    # Only rename columns that exist
    existing_mappings = {k: v for k, v in column_mapping.items() if k in df.columns}

    if existing_mappings:
        df = df.rename(columns=existing_mappings)
        logger.debug(f"Renamed columns: {list(existing_mappings.keys())}")

    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse date columns to datetime format.

    Args:
        df: DataFrame with date columns as strings

    Returns:
        DataFrame with parsed datetime columns
    """
    logger.debug("Parsing date columns")

    date_columns = ['openedDate', 'resolvedDate', 'closedDate', 'sys_created_on', 'sys_updated_on']

    for col in date_columns:
        if col in df.columns:
            # Handle multiple date formats
            df[col] = pd.to_datetime(df[col], errors='coerce')
            null_count = df[col].isna().sum()
            if null_count > 0:
                logger.debug(f"Column {col}: {null_count} invalid dates set to NaT")

    return df


def add_status_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived status fields (isActive, isResolved, etc.).

    Args:
        df: DataFrame with state/status columns

    Returns:
        DataFrame with added status fields
    """
    logger.debug("Adding status fields")

    # Active incidents (not resolved or closed)
    active_states = ['New', 'In Progress', 'Awaiting User Info', 'On Hold', 'Pending']
    if 'state' in df.columns:
        df['isActive'] = df['state'].isin(active_states)
        df['isResolved'] = df['state'].isin(['Resolved', 'Closed'])
    else:
        df['isActive'] = False
        df['isResolved'] = False

    # High impact based on priority
    if 'priority' in df.columns:
        df['isHighImpact'] = df['priority'].astype(str).str.contains('1 - Critical|2 - High', case=False, na=False)
    else:
        df['isHighImpact'] = False

    # Critical priority
    if 'priority' in df.columns:
        df['isCritical'] = df['priority'].astype(str).str.contains('1 - Critical', case=False, na=False)
    else:
        df['isCritical'] = False

    return df


def add_categorization(
    df: pd.DataFrame,
    rules: Optional[Dict[str, List[str]]] = None
) -> pd.DataFrame:
    """
    Categorize incidents based on description patterns.

    Args:
        df: DataFrame with description columns
        rules: Dictionary mapping categories to keyword lists.
              If None, uses default network incident categories.

    Returns:
        DataFrame with patternCategory column
    """
    logger.debug("Adding incident categorization")

    if rules is None:
        # Default network incident categorization rules
        rules = {
            'WiFi/Wireless': ['wifi', 'wireless', 'access point', 'wap', 'ssid'],
            'VPN/Remote Access': ['vpn', 'remote', 'zscaler', 'remote access', 'remote desktop'],
            'Network Printing': ['printer', 'print', 'printing', 'print queue'],
            'Server/Performance': ['server', 'performance', 'slow', 'clearcase', 'application'],
            'DNS/Resolution': ['dns', 'resolution', 'name resolution', 'nslookup'],
            'Firewall/Security': ['firewall', 'blocked', 'security', 'access denied'],
            'Connectivity': ['connectivity', 'connection', 'network', 'ping', 'unreachable'],
            'Hardware': ['hardware', 'device', 'router', 'switch', 'equipment failure'],
        }

    def categorize_incident(row: pd.Series) -> str:
        """Categorize a single incident."""
        # Combine short_description and description for better matching
        text = ' '.join([
            str(row.get('short_description', '')),
            str(row.get('description', ''))
        ]).lower()

        # Check each category's keywords
        for category, keywords in rules.items():
            if any(keyword in text for keyword in keywords):
                return category

        return 'Other'

    df['patternCategory'] = df.apply(categorize_incident, axis=1)

    # Log category distribution
    category_counts = df['patternCategory'].value_counts()
    logger.debug(f"Category distribution: {category_counts.to_dict()}")

    return df


def calculate_durations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate time durations (resolution time, age, etc.).

    Args:
        df: DataFrame with date columns

    Returns:
        DataFrame with duration columns
    """
    logger.debug("Calculating durations")

    # Resolution time for resolved incidents
    if 'resolvedDate' in df.columns and 'openedDate' in df.columns:
        resolved_mask = df['resolvedDate'].notna() & df['openedDate'].notna()

        df.loc[resolved_mask, 'resolutionTimeHrs'] = (
            df.loc[resolved_mask, 'resolvedDate'] - df.loc[resolved_mask, 'openedDate']
        ).dt.total_seconds() / 3600

        # Resolution time in days (for reporting)
        df.loc[resolved_mask, 'resolutionTimeDays'] = df.loc[resolved_mask, 'resolutionTimeHrs'] / 24

        resolved_count = resolved_mask.sum()
        if resolved_count > 0:
            avg_resolution = df.loc[resolved_mask, 'resolutionTimeHrs'].mean()
            logger.debug(f"Average resolution time: {avg_resolution:.1f} hours ({resolved_count} incidents)")

    else:
        df['resolutionTimeHrs'] = np.nan
        df['resolutionTimeDays'] = np.nan

    # Age for active incidents
    if 'openedDate' in df.columns:
        current_time = pd.Timestamp.now()
        active_mask = df.get('isActive', pd.Series([False] * len(df)))

        df.loc[active_mask, 'ageHrs'] = (
            current_time - df.loc[active_mask, 'openedDate']
        ).dt.total_seconds() / 3600

        df.loc[active_mask, 'ageDays'] = df.loc[active_mask, 'ageHrs'] / 24
    else:
        df['ageHrs'] = np.nan
        df['ageDays'] = np.nan

    return df


def calculate_sla_breach(
    df: pd.DataFrame,
    sla_rules: Optional[Dict[str, int]] = None
) -> pd.DataFrame:
    """
    Calculate SLA breach status.

    Args:
        df: DataFrame with duration columns
        sla_rules: Dictionary mapping priority levels to SLA hours.
                  If None, uses defaults: Critical=4h, High=24h, Moderate=72h, Low=120h

    Returns:
        DataFrame with slaBreach column
    """
    logger.debug("Calculating SLA breach status")

    if sla_rules is None:
        # Default SLA rules (in hours)
        sla_rules = {
            '1 - Critical': 4,
            '2 - High': 24,
            '3 - Moderate': 72,
            '4 - Low': 120,
        }

    def check_sla_breach(row: pd.Series) -> bool:
        """Check if incident breached SLA."""
        resolution_time = row.get('resolutionTimeHrs', np.nan)

        if pd.isna(resolution_time):
            return False

        priority = row.get('priority', '4 - Low')

        # Get SLA threshold for this priority
        sla_threshold = sla_rules.get(priority, 72)  # Default to 72h if priority not found

        return resolution_time > sla_threshold

    df['slaBreach'] = df.apply(check_sla_breach, axis=1)

    # Calculate SLA margin (positive = within SLA, negative = breach)
    def calculate_sla_margin(row: pd.Series) -> float:
        """Calculate how many hours within/over SLA."""
        resolution_time = row.get('resolutionTimeHrs', np.nan)

        if pd.isna(resolution_time):
            return np.nan

        priority = row.get('priority', '4 - Low')
        sla_threshold = sla_rules.get(priority, 72)

        return sla_threshold - resolution_time

    df['slaMarginHrs'] = df.apply(calculate_sla_margin, axis=1)

    # Log SLA breach statistics
    resolved_count = df['resolutionTimeHrs'].notna().sum()
    if resolved_count > 0:
        breach_count = df['slaBreach'].sum()
        breach_rate = (breach_count / resolved_count) * 100
        logger.debug(f"SLA breach rate: {breach_rate:.1f}% ({breach_count}/{resolved_count})")

    return df


def estimate_user_impact(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimate number of users affected by incident.

    This is a deterministic estimation based on CI type and priority.
    In production, this should be replaced with actual user impact data.

    Args:
        df: DataFrame with ci_type and priority columns

    Returns:
        DataFrame with userImpactEstimate column
    """
    logger.debug("Estimating user impact")

    def estimate_impact(row: pd.Series) -> int:
        """Estimate user impact for a single incident."""
        ci_type = str(row.get('ci_type', '')).lower()
        priority = str(row.get('priority', ''))

        # Base estimate by CI type
        if 'server' in ci_type or 'firewall' in ci_type:
            base_impact = 100  # Servers/firewalls affect many users
        elif 'access point' in ci_type or 'wifi' in ci_type or 'wireless' in ci_type:
            base_impact = 50   # WiFi affects area users
        elif 'router' in ci_type or 'switch' in ci_type:
            base_impact = 75   # Network devices affect multiple users
        elif 'printer' in ci_type:
            base_impact = 15   # Printers affect fewer users
        else:
            base_impact = 25   # Default for other types

        # Adjust by priority
        if '1 - Critical' in priority or '1' in priority:
            multiplier = 2.0   # Critical issues typically affect more users
        elif '2 - High' in priority:
            multiplier = 1.5
        elif '4 - Low' in priority:
            multiplier = 0.5
        else:
            multiplier = 1.0

        return int(base_impact * multiplier)

    df['userImpactEstimate'] = df.apply(estimate_impact, axis=1)

    return df


def add_temporal_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add temporal analysis fields (week, month, quarter, hour of day, etc.).

    Args:
        df: DataFrame with openedDate column

    Returns:
        DataFrame with temporal fields
    """
    logger.debug("Adding temporal fields")

    if 'openedDate' not in df.columns:
        logger.warning("openedDate column not found, skipping temporal fields")
        return df

    # Week number
    df['week'] = df['openedDate'].dt.isocalendar().week

    # Month
    df['month'] = df['openedDate'].dt.month
    df['monthName'] = df['openedDate'].dt.month_name()

    # Quarter
    df['quarter'] = df['openedDate'].dt.quarter

    # Year
    df['year'] = df['openedDate'].dt.year

    # Day of week
    df['dayOfWeek'] = df['openedDate'].dt.dayofweek  # 0=Monday, 6=Sunday
    df['dayOfWeekName'] = df['openedDate'].dt.day_name()

    # Hour of day (for identifying peak times)
    df['hourOfDay'] = df['openedDate'].dt.hour

    # Business hours flag (assuming 9-17 Mon-Fri)
    df['isBusinessHours'] = (
        (df['dayOfWeek'] < 5) &  # Monday-Friday
        (df['hourOfDay'] >= 9) &
        (df['hourOfDay'] < 17)
    )

    return df
