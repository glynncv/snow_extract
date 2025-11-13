"""
ServiceNow Incident Data Extraction and Processing Example
========================================================

This example demonstrates how to extract, clean, and analyze ServiceNow incident data
using the network_incident_etl pipeline with PII redaction capabilities.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone
import os
import sys
from pathlib import Path
import requests

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_servicenow_data():
    """
    Example of extracting ServiceNow incident data.
    In practice, this would connect to ServiceNow REST API or read from export files.
    """
    
    # Sample ServiceNow incident data structure
    sample_data = {
        'number': ['INC0010001', 'INC0010002', 'INC0010003', 'INC0010004', 'INC0010005'],
        'short_description': [
            'WiFi connectivity issue in Building A',
            'VPN connection failing for remote users',
            'Network printer not responding',
            'Slow performance on ClearCase server',
            'DNS resolution problems'
        ],
        'description': [
            'Users in Building A unable to connect to WiFi network. WAP03 appears to be down.',
            'Multiple users reporting VPN connection failures through Zscaler client.',
            'Network printer HP_PRINTER_01 not responding to print jobs from workstations.',
            'ClearCase server experiencing slow response times affecting development team.',
            'DNS resolution failing for external websites causing browser timeouts.'
        ],
        'priority': ['2 - High', '1 - Critical', '3 - Moderate', '2 - High', '3 - Moderate'],
        'incident_state': ['New', 'In Progress', 'Resolved', 'In Progress', 'Resolved'],
        'assignment_group': [
            'IT Network Support', 'IT Network Support', 'IT Network Support', 
            'IT Network Support', 'IT Network Support'
        ],
        'opened': [
            '2025-07-15 09:30:00', '2025-07-15 14:20:00', '2025-07-14 11:15:00',
            '2025-07-16 08:45:00', '2025-07-13 16:30:00'
        ],
        'resolved': [
            '', '2025-07-15 16:45:00', '2025-07-14 13:30:00', 
            '', '2025-07-14 09:15:00'
        ],
        'caller_id': ['john.doe@company.com', 'jane.smith@company.com', 'bob.wilson@company.com',
                     'alice.johnson@company.com', 'mike.brown@company.com'],
        'location': ['Building-A-Floor-2', 'Remote-Office-NYC', 'Building-B-Floor-1',
                    'Building-A-Floor-3', 'Building-C-Floor-1'],
        'ci_type': ['Access Point', 'VPN Gateway', 'Network Printer', 'Server', 'DNS Server']
    }
    
    df = pd.DataFrame(sample_data)
    logger.info(f"Extracted {len(df)} ServiceNow incident records")
    return df

def process_with_network_etl(df_raw):
    """
    Process the raw ServiceNow data using the network incident ETL pipeline
    """
    # Add the src directory to the path for imports
    src_path = Path(__file__).parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from network_incident_etl import transform_incident_frame, log_pipeline_metrics
    
    logger.info("Starting network incident ETL transformation...")
    
    # Transform the data
    df_processed = transform_incident_frame(df_raw)
    
    # Log pipeline metrics (to CSV since no DB engine provided)
    log_pipeline_metrics(
        df_raw, 
        df_processed, 
        engine=None,  # No database connection
        csv_fallback="servicenow_metrics.csv"
    )
    
    logger.info(f"ETL transformation complete. Processed {len(df_processed)} records.")
    return df_processed

def apply_pii_redaction(df):
    """
    Apply PII redaction using the redaction utility
    """
    # Add the src directory to the path for imports
    src_path = Path(__file__).parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from redact5 import redact_text, hash_id
    
    logger.info("Applying PII redaction...")
    
    # Create a copy for redaction
    df_redacted = df.copy()
    
    # Hash sensitive IDs
    if 'number' in df_redacted.columns:
        df_redacted['id_hash'] = df_redacted['number'].apply(hash_id)
        df_redacted.drop('number', axis=1, inplace=True)
    
    # Redact PII from text fields
    text_fields = ['short_description', 'description']
    for field in text_fields:
        if field in df_redacted.columns:
            df_redacted[field] = redact_text(df_redacted[field])
    
    # Remove or redact PII columns
    pii_columns = ['caller_id']
    for col in pii_columns:
        if col in df_redacted.columns:
            df_redacted.drop(col, axis=1, inplace=True)
    
    # Truncate location to remove detailed floor information
    if 'location' in df_redacted.columns:
        df_redacted['location'] = df_redacted['location'].str.split('-').str[0]
    
    logger.info("PII redaction complete")
    return df_redacted

def analyze_incident_patterns(df):
    """
    Analyze incident patterns and generate insights
    """
    logger.info("Analyzing incident patterns...")
    
    print("\n" + "="*60)
    print("SERVICENOW INCIDENT ANALYSIS REPORT")
    print("="*60)
    
    # Basic statistics
    print(f"\nBasic Statistics:")
    print(f"Total Incidents: {len(df)}")
    print(f"Active Incidents: {df['isActive'].sum()}")
    print(f"Resolved Incidents: {(~df['isActive']).sum()}")
    print(f"High Impact Incidents: {df['isHighImpact'].sum()}")
    
    # Pattern category analysis
    print(f"\nIncident Categories:")
    category_counts = df['patternCategory'].value_counts()
    for category, count in category_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")
    
    # SLA breach analysis
    if 'slaBreach' in df.columns:
        resolved_incidents = df[df['resolvedDate'].notna()]
        if len(resolved_incidents) > 0:
            breach_rate = (resolved_incidents['slaBreach'].sum() / len(resolved_incidents)) * 100
            print(f"\nSLA Performance:")
            print(f"  SLA Breach Rate: {breach_rate:.1f}%")
            print(f"  Breached Incidents: {resolved_incidents['slaBreach'].sum()}")
            print(f"  Within SLA: {(~resolved_incidents['slaBreach']).sum()}")
    
    # Resolution time analysis
    if 'resolutionTimeHrs' in df.columns:
        resolved = df[df['resolutionTimeHrs'].notna()]
        if len(resolved) > 0:
            print(f"\nResolution Time Analysis:")
            print(f"  Average Resolution Time: {resolved['resolutionTimeHrs'].mean():.1f} hours")
            print(f"  Median Resolution Time: {resolved['resolutionTimeHrs'].median():.1f} hours")
            print(f"  Fastest Resolution: {resolved['resolutionTimeHrs'].min():.1f} hours")
            print(f"  Longest Resolution: {resolved['resolutionTimeHrs'].max():.1f} hours")
    
    # User impact analysis
    if 'userImpactEstimate' in df.columns:
        total_impact = df['userImpactEstimate'].sum()
        avg_impact = df['userImpactEstimate'].mean()
        print(f"\nUser Impact Analysis:")
        print(f"  Total Estimated Users Affected: {total_impact}")
        print(f"  Average Users per Incident: {avg_impact:.1f}")
    
    # Weekly trend analysis
    if 'week' in df.columns:
        print(f"\nWeekly Incident Trends:")
        weekly_counts = df['week'].value_counts().sort_index()
        for week, count in weekly_counts.head().items():
            print(f"  Week {week}: {count} incidents")
    
    return df

def save_results(df_processed, df_redacted):
    """
    Save processed results to files
    """
    # Use absolute path for output directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save processed data (with PII)
    processed_file = output_dir / "servicenow_incidents_processed.csv"
    df_processed.to_csv(processed_file, index=False)
    logger.info(f"Saved processed data to: {processed_file}")
    
    # Save redacted data (safe for sharing)
    redacted_file = output_dir / "servicenow_incidents_redacted.csv"
    df_redacted.to_csv(redacted_file, index=False)
    logger.info(f"Saved redacted data to: {redacted_file}")
    
    print(f"\nOutput Files:")
    print(f"  Processed (internal use): {processed_file}")
    print(f"  Redacted (safe for sharing): {redacted_file}")

def main():
    """
    Main execution function demonstrating the complete ServiceNow data extraction workflow
    """
    print("ServiceNow Incident Data Extraction Example")
    print("=" * 50)
    
    try:
        # Step 1: Extract raw ServiceNow data
        print("\nStep 1: Extracting ServiceNow incident data...")
        df_raw = extract_servicenow_data()
        
        # Step 2: Process with network ETL pipeline
        print("\nStep 2: Processing with network incident ETL...")
        df_processed = process_with_network_etl(df_raw)
        
        # Step 3: Apply PII redaction
        print("\nStep 3: Applying PII redaction...")
        df_redacted = apply_pii_redaction(df_processed)
        
        # Step 4: Analyze patterns and generate insights
        print("\nStep 4: Analyzing incident patterns...")
        analyze_incident_patterns(df_processed)
        
        # Step 5: Save results
        print("\nStep 5: Saving results...")
        save_results(df_processed, df_redacted)
        
        print("\n" + "="*60)
        print("EXTRACTION AND PROCESSING COMPLETE!")
        print("="*60)
        print("\nNext Steps:")
        print("1. Review the analysis report above")
        print("2. Check output files for detailed data")
        print("3. Use redacted data for external sharing")
        print("4. Set up automated scheduling for regular extracts")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

# Additional utility functions for real ServiceNow API integration

def connect_to_servicenow_api(instance_url, username, password, verify_ssl=True):
    """
    Example function for connecting to ServiceNow REST API
    Note: In production, use OAuth or other secure authentication methods
    
    Args:
        instance_url: ServiceNow instance URL
        username: ServiceNow username
        password: ServiceNow password
        verify_ssl: If False, disable SSL certificate verification (not recommended for production)
    """
    import requests
    from requests.auth import HTTPBasicAuth
    
    # Set up authentication
    auth = HTTPBasicAuth(username, password)
    
    # Headers for JSON response
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Test connection
    test_url = f"{instance_url}/api/now/table/incident"
    params = {'sysparm_limit': 1}
    
    try:
        response = requests.get(test_url, auth=auth, headers=headers, params=params, verify=verify_ssl)
        response.raise_for_status()
        logger.info("Successfully connected to ServiceNow API")
        return auth, headers
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to ServiceNow API: {e}")
        return None, None

def extract_incidents_from_api(instance_url, auth, headers, query_params=None, verify_ssl=True):
    """
    Extract incident data from ServiceNow REST API
    
    Args:
        instance_url: ServiceNow instance URL
        auth: Authentication object
        headers: Request headers
        query_params: Optional query parameters
        verify_ssl: If False, disable SSL certificate verification (not recommended for production)
    """
    url = f"{instance_url}/api/now/table/incident"
    
    # Default query parameters
    default_params = {
        'sysparm_limit': 1000,
        'sysparm_offset': 0,
        'sysparm_query': 'assignment_groupLIKEnetwork^state!=6',  # Network incidents, not closed
        'sysparm_fields': 'number,short_description,description,priority,state,assignment_group,opened_at,resolved_at,caller_id,location,cmdb_ci'
    }
    
    if query_params:
        default_params.update(query_params)
    
    try:
        response = requests.get(url, auth=auth, headers=headers, params=default_params, verify=verify_ssl)
        response.raise_for_status()
        
        data = response.json()
        incidents = data.get('result', [])
        
        # Convert to DataFrame
        df = pd.DataFrame(incidents)
        logger.info(f"Extracted {len(df)} incidents from ServiceNow API")
        
        return df
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error extracting incidents from API: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    main()