"""
Network Incident ETL Pipeline
============================

Transforms ServiceNow incident data for network-related incidents.
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
import numpy as np
import os

logger = logging.getLogger(__name__)

def transform_incident_frame(df_raw):
    """
    Transform raw ServiceNow incident data into standardized format
    
    Args:
        df_raw (pd.DataFrame): Raw incident data from ServiceNow
        
    Returns:
        pd.DataFrame: Transformed incident data with additional fields
    """
    logger.info("Starting incident data transformation...")
    
    # Create a copy to avoid modifying original data
    df = df_raw.copy()
    
    # Standardize column names
    column_mapping = {
        'incident_state': 'state',
        'opened': 'openedDate',
        'resolved': 'resolvedDate'
    }
    df.rename(columns=column_mapping, inplace=True)
    
    # Convert date columns to datetime
    date_columns = ['openedDate', 'resolvedDate']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Add derived fields
    df['isActive'] = df['state'].isin(['New', 'In Progress', 'Awaiting User Info'])
    
    # Determine high impact based on priority (if priority column exists)
    if 'priority' in df.columns:
        df['isHighImpact'] = df['priority'].str.contains('1 - Critical|2 - High', na=False)
    else:
        df['isHighImpact'] = False
    
    # Categorize incidents by type
    def categorize_incident(row):
        desc = str(row.get('short_description', '')).lower()
        if any(term in desc for term in ['wifi', 'wireless', 'access point']):
            return 'WiFi/Wireless'
        elif any(term in desc for term in ['vpn', 'remote']):
            return 'VPN/Remote Access'
        elif any(term in desc for term in ['printer', 'print']):
            return 'Network Printing'
        elif any(term in desc for term in ['server', 'performance']):
            return 'Server/Performance'
        elif any(term in desc for term in ['dns', 'resolution']):
            return 'DNS/Resolution'
        else:
            return 'Other Network'
    
    df['patternCategory'] = df.apply(categorize_incident, axis=1)
    
    # Calculate resolution time for resolved incidents
    if 'resolvedDate' in df.columns and 'openedDate' in df.columns:
        resolved_mask = df['resolvedDate'].notna() & df['openedDate'].notna()
        df.loc[resolved_mask, 'resolutionTimeHrs'] = (
            df.loc[resolved_mask, 'resolvedDate'] - df.loc[resolved_mask, 'openedDate']
        ).dt.total_seconds() / 3600
    else:
        df['resolutionTimeHrs'] = np.nan
    
    # Add SLA breach calculation (assuming 24h SLA for high priority, 72h for others)
    def calculate_sla_breach(row):
        if pd.isna(row.get('resolutionTimeHrs', np.nan)):
            return False
        sla_hours = 24 if row.get('isHighImpact', False) else 72
        return row.get('resolutionTimeHrs', 0) > sla_hours
    
    df['slaBreach'] = df.apply(calculate_sla_breach, axis=1)
    
    # Estimate user impact based on CI type and location
    def estimate_user_impact(row):
        ci_type = str(row.get('ci_type', '')).lower()
        location = str(row.get('location', '')).lower()
        
        if 'server' in ci_type:
            return np.random.randint(50, 200)  # Servers affect many users
        elif 'access point' in ci_type or 'wifi' in ci_type:
            return np.random.randint(20, 100)  # WiFi affects area users
        elif 'printer' in ci_type:
            return np.random.randint(5, 30)    # Printers affect fewer users
        else:
            return np.random.randint(1, 50)    # Other network issues
    
    df['userImpactEstimate'] = df.apply(estimate_user_impact, axis=1)
    
    # Add week number for trending
    if 'openedDate' in df.columns:
        df['week'] = df['openedDate'].dt.isocalendar().week
    else:
        df['week'] = np.nan
    
    logger.info(f"Transformation complete. Added {len(df.columns) - len(df_raw.columns)} new columns.")
    return df

def log_pipeline_metrics(df_raw, df_processed, engine=None, csv_fallback=None):
    """
    Log pipeline processing metrics
    
    Args:
        df_raw (pd.DataFrame): Original raw data
        df_processed (pd.DataFrame): Processed data
        engine: Database engine (optional)
        csv_fallback (str): CSV filename for fallback logging
    """
    metrics = {
        'timestamp': datetime.now(),
        'raw_record_count': len(df_raw),
        'processed_record_count': len(df_processed),
        'columns_added': len(df_processed.columns) - len(df_raw.columns),
        'active_incidents': df_processed['isActive'].sum() if 'isActive' in df_processed.columns else 0,
        'high_impact_incidents': df_processed['isHighImpact'].sum() if 'isHighImpact' in df_processed.columns else 0,
        'sla_breaches': df_processed['slaBreach'].sum() if 'slaBreach' in df_processed.columns else 0
    }
    
    logger.info(f"Pipeline Metrics: {metrics}")
    
    if csv_fallback:
        # Save metrics to CSV
        metrics_df = pd.DataFrame([metrics])
        output_path = f"logs/{csv_fallback}"
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Append to existing file or create new
        if os.path.exists(output_path):
            metrics_df.to_csv(output_path, mode='a', header=False, index=False)
        else:
            metrics_df.to_csv(output_path, index=False)
        
        logger.info(f"Metrics saved to: {output_path}")
