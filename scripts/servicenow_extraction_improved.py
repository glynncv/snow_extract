"""
Improved ServiceNow Extraction Script
===================================

Enhanced version with better error handling, configuration management,
and modular design.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone
import os
import sys
from pathlib import Path
import requests
from typing import Optional, Dict, Any
import argparse

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

# Add src directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from config_manager import config
from network_incident_etl import transform_incident_frame, log_pipeline_metrics
from redact5 import redact_dataframe_columns, validate_redaction

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.get('logging.level', 'INFO')),
    format=config.get('logging.format', '%(asctime)s - %(levelname)s - %(message)s')
)
logger = logging.getLogger(__name__)

class ServiceNowExtractor:
    """Main class for ServiceNow data extraction and processing"""
    
    def __init__(self, config_path: Optional[str] = None, verify_ssl: bool = True):
        """
        Initialize the extractor
        
        Args:
            config_path: Optional path to configuration file
            verify_ssl: If False, disable SSL certificate verification (not recommended for production)
        """
        self.config = config
        self.verify_ssl = verify_ssl
        self.session = None
        self.auth = None
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        if not verify_ssl:
            logger.warning("SSL certificate verification is disabled. This is not recommended for production use.")
    
    def connect_to_servicenow(self) -> bool:
        """
        Establish connection to ServiceNow
        
        Returns:
            True if connection successful
        """
        instance_url = self.config.get('servicenow.instance_url')
        username = self.config.get('servicenow.username')
        password = self.config.get('servicenow.password')
        
        if not all([instance_url, username, password]):
            logger.error("ServiceNow credentials not configured")
            return False
        
        try:
            from requests.auth import HTTPBasicAuth
            self.auth = HTTPBasicAuth(username, password)
            self.session = requests.Session()
            self.session.auth = self.auth
            self.session.headers.update(self.headers)
            
            # Test connection
            test_url = f"{instance_url}/api/now/table/incident"
            response = self.session.get(test_url, params={'sysparm_limit': 1}, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            
            logger.info("Successfully connected to ServiceNow")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ServiceNow: {e}")
            return False
    
    def extract_sample_data(self) -> pd.DataFrame:
        """
        Extract sample ServiceNow incident data for demonstration
        
        Returns:
            DataFrame with sample incident data
        """
        logger.info("Generating sample ServiceNow data...")
        
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
        logger.info(f"Generated {len(df)} sample incident records")
        return df
    
    def extract_from_api(self) -> pd.DataFrame:
        """
        Extract real data from ServiceNow API
        
        Returns:
            DataFrame with incident data from API
        """
        if not self.session:
            logger.error("Not connected to ServiceNow. Call connect_to_servicenow() first.")
            return pd.DataFrame()
        
        instance_url = self.config.get('servicenow.instance_url')
        batch_size = self.config.get('extraction.batch_size', 1000)
        query_filter = self.config.get('extraction.query_filter', '')
        
        url = f"{instance_url}/api/now/table/incident"
        params = {
            'sysparm_limit': batch_size,
            'sysparm_offset': 0,
            'sysparm_query': query_filter,
            'sysparm_fields': 'number,short_description,description,priority,state,assignment_group,opened_at,resolved_at,caller_id,location,cmdb_ci'
        }
        
        try:
            response = self.session.get(url, params=params, verify=self.verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            incidents = data.get('result', [])
            
            df = pd.DataFrame(incidents)
            logger.info(f"Extracted {len(df)} incidents from ServiceNow API")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting from API: {e}")
            return pd.DataFrame()
    
    def process_data(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Process raw data through ETL pipeline
        
        Args:
            df_raw: Raw incident data
            
        Returns:
            Processed DataFrame
        """
        if df_raw.empty:
            logger.warning("No data to process")
            return df_raw
        
        try:
            logger.info("Starting ETL processing...")
            df_processed = transform_incident_frame(df_raw)
            
            # Log metrics
            logs_dir = project_root / self.config.get('paths.logs_dir', 'logs')
            logs_dir.mkdir(exist_ok=True)
            
            log_pipeline_metrics(
                df_raw, 
                df_processed, 
                engine=None,
                csv_fallback=str(logs_dir / "processing_metrics.csv")
            )
            
            logger.info(f"ETL processing complete. {len(df_processed)} records processed.")
            return df_processed
            
        except Exception as e:
            logger.error(f"Error in ETL processing: {e}")
            return df_raw
    
    def apply_redaction(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply PII redaction to processed data
        
        Args:
            df: DataFrame to redact
            
        Returns:
            Redacted DataFrame
        """
        if not self.config.get('redaction.enabled', True):
            logger.info("PII redaction disabled in configuration")
            return df.copy()
        
        try:
            logger.info("Applying PII redaction...")
            
            # Use the comprehensive redaction function
            df_redacted = redact_dataframe_columns(
                df,
                text_columns=['short_description', 'description'],
                id_columns=['number'],
                drop_columns=['caller_id']
            )
            
            # Validate redaction
            validation = validate_redaction(df, df_redacted)
            if validation['redaction_successful']:
                logger.info("PII redaction validation passed")
            else:
                logger.warning("PII redaction validation failed - some PII may remain")
            
            return df_redacted
            
        except Exception as e:
            logger.error(f"Error in PII redaction: {e}")
            return df.copy()
    
    def analyze_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze processed data and generate insights
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Dictionary with analysis results
        """
        if df.empty:
            return {}
        
        logger.info("Analyzing incident data...")
        
        analysis = {
            'total_incidents': len(df),
            'active_incidents': int(df.get('isActive', pd.Series(dtype=bool)).sum()),
            'high_impact_incidents': int(df.get('isHighImpact', pd.Series(dtype=bool)).sum()),
            'timestamp': datetime.now().isoformat()
        }
        
        # Pattern analysis
        if 'patternCategory' in df.columns:
            analysis['pattern_distribution'] = df['patternCategory'].value_counts().to_dict()
        
        # SLA analysis
        if 'slaBreach' in df.columns:
            resolved = df[df['resolutionTimeHrs'].notna()]
            if not resolved.empty:
                analysis['sla_breach_rate'] = (resolved['slaBreach'].sum() / len(resolved)) * 100
        
        # Resolution time analysis
        if 'resolutionTimeHrs' in df.columns:
            resolved = df[df['resolutionTimeHrs'].notna()]
            if not resolved.empty:
                analysis['avg_resolution_hours'] = resolved['resolutionTimeHrs'].mean()
                analysis['median_resolution_hours'] = resolved['resolutionTimeHrs'].median()
        
        self._print_analysis_report(analysis)
        return analysis
    
    def _print_analysis_report(self, analysis: Dict[str, Any]) -> None:
        """Print formatted analysis report"""
        print("\n" + "="*60)
        print("SERVICENOW INCIDENT ANALYSIS REPORT")
        print("="*60)
        
        print(f"\nBasic Statistics:")
        print(f"  Total Incidents: {analysis.get('total_incidents', 0)}")
        print(f"  Active Incidents: {analysis.get('active_incidents', 0)}")
        print(f"  High Impact Incidents: {analysis.get('high_impact_incidents', 0)}")
        
        if 'pattern_distribution' in analysis:
            print(f"\nIncident Categories:")
            for category, count in analysis['pattern_distribution'].items():
                percentage = (count / analysis['total_incidents']) * 100
                print(f"  {category}: {count} ({percentage:.1f}%)")
        
        if 'sla_breach_rate' in analysis:
            print(f"\nSLA Performance:")
            print(f"  SLA Breach Rate: {analysis['sla_breach_rate']:.1f}%")
        
        if 'avg_resolution_hours' in analysis:
            print(f"\nResolution Time Analysis:")
            print(f"  Average Resolution Time: {analysis['avg_resolution_hours']:.1f} hours")
            print(f"  Median Resolution Time: {analysis['median_resolution_hours']:.1f} hours")
    
    def save_results(self, df_processed: pd.DataFrame, df_redacted: pd.DataFrame, analysis: Dict[str, Any]) -> None:
        """
        Save all results to files
        
        Args:
            df_processed: Processed data with PII
            df_redacted: Redacted data safe for sharing
            analysis: Analysis results
        """
        output_dir = project_root / self.config.get('paths.output_dir', 'output')
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save processed data
            processed_file = output_dir / f"incidents_processed_{timestamp}.csv"
            df_processed.to_csv(processed_file, index=False)
            logger.info(f"Saved processed data to: {processed_file}")
            
            # Save redacted data
            redacted_file = output_dir / f"incidents_redacted_{timestamp}.csv"
            df_redacted.to_csv(redacted_file, index=False)
            logger.info(f"Saved redacted data to: {redacted_file}")
            
            # Save analysis results
            analysis_file = output_dir / f"analysis_{timestamp}.json"
            import json
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            logger.info(f"Saved analysis to: {analysis_file}")
            
            print(f"\nOutput Files:")
            print(f"  Processed data: {processed_file}")
            print(f"  Redacted data: {redacted_file}")
            print(f"  Analysis results: {analysis_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def run_extraction(self, use_api: bool = False) -> bool:
        """
        Run the complete extraction workflow
        
        Args:
            use_api: Whether to use real API or sample data
            
        Returns:
            True if extraction completed successfully
        """
        try:
            print("ServiceNow Incident Data Extraction")
            print("=" * 50)
            
            # Step 1: Extract data
            if use_api:
                if not self.connect_to_servicenow():
                    logger.error("Failed to connect to ServiceNow API")
                    return False
                df_raw = self.extract_from_api()
            else:
                df_raw = self.extract_sample_data()
            
            if df_raw.empty:
                logger.error("No data extracted")
                return False
            
            # Step 2: Process data
            df_processed = self.process_data(df_raw)
            
            # Step 3: Apply redaction
            df_redacted = self.apply_redaction(df_processed)
            
            # Step 4: Analyze data
            analysis = self.analyze_data(df_processed)
            
            # Step 5: Save results
            self.save_results(df_processed, df_redacted, analysis)
            
            print("\n" + "="*60)
            print("EXTRACTION AND PROCESSING COMPLETE!")
            print("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in extraction workflow: {e}")
            return False

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='ServiceNow Data Extraction')
    parser.add_argument('--use-api', action='store_true', 
                       help='Use ServiceNow API instead of sample data')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification (use for corporate environments with certificate issues)')
    args = parser.parse_args()
    
    extractor = ServiceNowExtractor(verify_ssl=not args.no_verify_ssl)
    
    # Run with API or sample data
    success = extractor.run_extraction(use_api=args.use_api)
    
    if success:
        print("\nExtraction completed successfully!")
    else:
        print("\nExtraction failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
