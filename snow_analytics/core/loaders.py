"""
Data Loading Module
==================

Provides unified interface for loading ServiceNow incident data from multiple sources.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import os

from snow_analytics.core.config import Config
from snow_analytics.core.validators import validate_incident_schema
from snow_analytics.connectors.api import ServiceNowAPI

logger = logging.getLogger(__name__)


def load_incidents(
    source: str,
    config: Optional[Config] = None,
    validate: bool = True,
    **kwargs
) -> pd.DataFrame:
    """
    Load ServiceNow incident data from specified source.

    Args:
        source: Data source ('api', 'csv', 'sample')
        config: Configuration object
        validate: Whether to validate schema after loading
        **kwargs: Additional arguments passed to specific loader

    Returns:
        DataFrame containing incident data

    Examples:
        >>> # Load from API
        >>> df = load_incidents('api', limit=1000)

        >>> # Load from CSV
        >>> df = load_incidents('csv', file_path='data/incidents.csv')

        >>> # Generate sample data
        >>> df = load_incidents('sample', num_records=50)
    """
    if config is None:
        config = Config()

    source = source.lower()

    logger.info(f"Loading incidents from source: {source}")

    if source == 'api':
        df = load_from_api(config=config, **kwargs)
    elif source == 'csv':
        df = load_from_csv(**kwargs)
    elif source == 'sample':
        df = generate_sample_data(**kwargs)
    else:
        raise ValueError(f"Unknown source: {source}. Must be 'api', 'csv', or 'sample'")

    if df.empty:
        logger.warning("Loaded empty DataFrame")
        return df

    logger.info(f"Loaded {len(df)} incidents with {len(df.columns)} columns")

    # Validate schema if requested
    if validate:
        is_valid, issues = validate_incident_schema(df)
        if not is_valid:
            logger.warning(f"Schema validation issues: {issues}")

    return df


def load_from_api(
    instance_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    query_filter: Optional[str] = None,
    limit: int = 1000,
    config: Optional[Config] = None,
    verify_ssl: bool = True,
    **kwargs
) -> pd.DataFrame:
    """
    Load incidents from ServiceNow REST API.

    Args:
        instance_url: ServiceNow instance URL (or from config/env)
        username: ServiceNow username (or from config/env)
        password: ServiceNow password (or from config/env)
        query_filter: ServiceNow query filter (e.g., 'assignment_groupLIKEnetwork')
        limit: Maximum number of records to fetch
        config: Configuration object
        verify_ssl: Whether to verify SSL certificates
        **kwargs: Additional API parameters

    Returns:
        DataFrame with incident data
    """
    if config is None:
        config = Config()

    # Get credentials from args, config, or environment
    instance_url = instance_url or config.get('servicenow.instance_url') or os.getenv('SNOW_INSTANCE_URL')
    username = username or config.get('servicenow.username') or os.getenv('SNOW_USERNAME')
    password = password or config.get('servicenow.password') or os.getenv('SNOW_PASSWORD')

    if not all([instance_url, username, password]):
        raise ValueError(
            "ServiceNow credentials not configured. Provide via arguments, config file, "
            "or environment variables (SNOW_INSTANCE_URL, SNOW_USERNAME, SNOW_PASSWORD)"
        )

    # Get query filter from args or config
    if query_filter is None:
        query_filter = config.get('extraction.query_filter', '')

    # Create API client
    api = ServiceNowAPI(
        instance_url=instance_url,
        username=username,
        password=password,
        verify_ssl=verify_ssl
    )

    # Connect and fetch data
    if not api.connect():
        raise ConnectionError("Failed to connect to ServiceNow API")

    logger.info(f"Extracting up to {limit} incidents from ServiceNow API")
    if query_filter:
        logger.info(f"Using query filter: {query_filter}")

    incidents = api.get_incidents(query=query_filter, limit=limit)

    if not incidents:
        logger.warning("No incidents returned from API")
        return pd.DataFrame()

    df = pd.DataFrame(incidents)

    # Normalize column names from API response
    df = _normalize_api_columns(df)

    return df


def load_from_csv(
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    validate: bool = False,
    **read_csv_kwargs
) -> pd.DataFrame:
    """
    Load incidents from CSV file.

    Args:
        file_path: Path to CSV file
        encoding: File encoding
        validate: Whether to validate schema
        **read_csv_kwargs: Additional arguments for pd.read_csv()

    Returns:
        DataFrame with incident data
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"Loading incidents from CSV: {file_path}")

    try:
        df = pd.read_csv(file_path, encoding=encoding, **read_csv_kwargs)
        logger.info(f"Loaded {len(df)} incidents from CSV")
        return df
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        raise


def generate_sample_data(
    num_records: int = 10,
    template: str = 'network',
    include_resolved: bool = True
) -> pd.DataFrame:
    """
    Generate sample ServiceNow incident data for testing.

    Args:
        num_records: Number of sample records to generate
        template: Data template ('network', 'general')
        include_resolved: Whether to include resolved incidents

    Returns:
        DataFrame with sample incident data
    """
    logger.info(f"Generating {num_records} sample incident records (template: {template})")

    if template == 'network':
        return _generate_network_incidents(num_records, include_resolved)
    elif template == 'general':
        return _generate_general_incidents(num_records, include_resolved)
    else:
        raise ValueError(f"Unknown template: {template}")


def _generate_network_incidents(num_records: int, include_resolved: bool) -> pd.DataFrame:
    """Generate sample network incident data."""
    import numpy as np

    base_time = datetime.now() - timedelta(days=7)

    categories = ['WiFi/Wireless', 'VPN/Remote Access', 'Network Printing', 'DNS/Resolution', 'Server/Performance']
    priorities = ['1 - Critical', '2 - High', '3 - Moderate', '4 - Low']
    states = ['New', 'In Progress', 'Resolved', 'On Hold']
    ci_types = ['Access Point', 'VPN Gateway', 'Router', 'Switch', 'Firewall', 'DNS Server']
    locations = ['London Office', 'New York Office', 'Berlin Office', 'Tokyo Office', 'Sydney Office']
    assignment_groups = ['Global Network Services', 'EMEA Network Team', 'APAC Network Team', 'Local IT Support']

    records = []

    for i in range(num_records):
        opened_time = base_time - timedelta(hours=np.random.randint(1, 168))  # Last week
        is_resolved = include_resolved and np.random.random() > 0.3

        resolved_time = None
        if is_resolved:
            resolution_hours = np.random.randint(1, 72)
            resolved_time = opened_time + timedelta(hours=resolution_hours)

        priority = np.random.choice(priorities, p=[0.1, 0.3, 0.4, 0.2])
        state = 'Resolved' if is_resolved else np.random.choice(['New', 'In Progress', 'On Hold'], p=[0.2, 0.6, 0.2])

        record = {
            'number': f'INC{7560000 + i:07d}',
            'short_description': f"{np.random.choice(categories)} issue affecting users",
            'description': f"Detailed description of {np.random.choice(categories).lower()} incident affecting multiple users in {np.random.choice(locations)}.",
            'priority': priority,
            'state': state,
            'incident_state': state,
            'assignment_group': np.random.choice(assignment_groups),
            'opened_at': opened_time.strftime('%Y-%m-%d %H:%M:%S'),
            'opened': opened_time.strftime('%Y-%m-%d %H:%M:%S'),
            'resolved_at': resolved_time.strftime('%Y-%m-%d %H:%M:%S') if resolved_time else '',
            'resolved': resolved_time.strftime('%Y-%m-%d %H:%M:%S') if resolved_time else '',
            'u_resolved': resolved_time.strftime('%Y-%m-%d %H:%M:%S') if resolved_time else '',
            'caller_id': f"user{i}@company.com",
            'location': np.random.choice(locations),
            'ci_type': np.random.choice(ci_types),
            'u_ci_type': np.random.choice(ci_types),
            'cmdb_ci': f"{np.random.choice(ci_types).replace(' ', '_').upper()}_{np.random.randint(1, 20):03d}",
            'category': 'Network',
            'subcategory': np.random.choice(['Connectivity', 'Performance', 'Configuration', 'Availability']),
            'contact_type': np.random.choice(['Email', 'Phone', 'Self-service', 'Chat']),
            'reassignment_count': np.random.choice([0, 0, 0, 1, 1, 2, 3], p=[0.4, 0.2, 0.1, 0.15, 0.1, 0.04, 0.01]),
            'assigned_to': f"Admin {i % 5}",
            'work_notes': f"Initial investigation notes for incident {i}",
        }

        records.append(record)

    df = pd.DataFrame(records)
    logger.info(f"Generated {len(df)} sample network incidents")
    return df


def _generate_general_incidents(num_records: int, include_resolved: bool) -> pd.DataFrame:
    """Generate sample general incident data."""
    # Similar to network incidents but with broader categories
    return _generate_network_incidents(num_records, include_resolved)


def _normalize_api_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names from ServiceNow API response to standard format.

    Args:
        df: DataFrame with API response data

    Returns:
        DataFrame with normalized column names
    """
    column_mapping = {
        'state': 'incident_state',
        'opened_at': 'opened_at',
        'resolved_at': 'resolved_at',
        # Add more mappings as needed
    }

    # Only rename columns that exist
    existing_mappings = {k: v for k, v in column_mapping.items() if k in df.columns}
    if existing_mappings:
        df = df.rename(columns=existing_mappings)

    # Add missing columns with default values
    if 'u_ci_type' not in df.columns and 'cmdb_ci' in df.columns:
        df['u_ci_type'] = 'Unknown'

    if 'assigned_to' not in df.columns:
        df['assigned_to'] = 'Unassigned'

    if 'reassignment_count' not in df.columns:
        df['reassignment_count'] = 0

    return df
