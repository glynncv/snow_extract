"""
Updated ServiceNow Extraction Script for Real Data Pipeline
=========================================================

This script is designed to work with the actual ServiceNow data pipeline:
1. Original data with PII
2. Redacted data (PII removed)
3. Processed data (with ETL transformations)
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import os
import sys
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

class RealDataServiceNowExtractor:
    """
    ServiceNow extractor designed to work with your real data pipeline
    """
    
    def __init__(self, use_api=False, config_path=None):
        self.original_file = r"C:\Users\cglynn\myPython\pii-redaction-utility\data\archive\IM_Network_EMEA_2025.csv"
        self.redacted_file = r"C:\Users\cglynn\myPython\pii-redaction-utility\data\processed\IM_Network_EMEA_2025_redacted_clean.csv"
        self.processed_file = r"C:\Users\cglynn\myPython\Networks_IM_2025\data\processed\IM_Network_EMEA_2025_redacted_clean_analysed.csv"
        
        # ServiceNow API connection settings
        self.use_api = use_api
        self.session = None
        self.auth = None
        
        # Load configuration for API connections
        if config_path:
            self.config = self.load_config(config_path)
        else:
            # Load from default config file in project
            config_file = project_root / "config" / "config.json"
            self.config = self.load_config(config_file) if config_file.exists() else {}
    
    def load_config(self, config_path):
        """Load configuration from JSON file"""
        try:
            import json
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
            return {}
    
    def connect_to_servicenow(self):
        """
        Establish connection to ServiceNow API
        
        Returns:
            bool: True if connection successful
        """
        if not self.use_api:
            logger.info("API connection disabled, using local files")
            return False
            
        # Get connection details from config
        instance_url = self.config.get('servicenow', {}).get('instance_url', '')
        username = self.config.get('servicenow', {}).get('username', '')
        password = self.config.get('servicenow', {}).get('password', '')
        
        # Also check environment variables
        if not instance_url:
            instance_url = os.getenv('SNOW_INSTANCE_URL', '')
        if not username:
            username = os.getenv('SNOW_USERNAME', '')
        if not password:
            password = os.getenv('SNOW_PASSWORD', '')
        
        if not all([instance_url, username, password]):
            logger.error("ServiceNow credentials not configured. Set in config.json or environment variables:")
            logger.error("- SNOW_INSTANCE_URL")
            logger.error("- SNOW_USERNAME") 
            logger.error("- SNOW_PASSWORD")
            return False
        
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            
            self.auth = HTTPBasicAuth(username, password)
            self.session = requests.Session()
            self.session.auth = self.auth
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            
            # Test connection
            test_url = f"{instance_url}/api/now/table/incident"
            timeout = self.config.get('servicenow', {}).get('timeout', 30)
            
            logger.info(f"Testing connection to: {instance_url}")
            response = self.session.get(test_url, params={'sysparm_limit': 1}, timeout=timeout)
            response.raise_for_status()
            
            logger.info("Successfully connected to ServiceNow API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ServiceNow: {e}")
            self.session = None
            self.auth = None
            return False
    
    def extract_from_servicenow_api(self, sample_size=1000):
        """
        Extract data directly from ServiceNow API
        
        Args:
            sample_size: Number of records to extract
            
        Returns:
            pd.DataFrame: Data from ServiceNow
        """
        if not self.session:
            logger.error("Not connected to ServiceNow. Call connect_to_servicenow() first.")
            return pd.DataFrame()
        
        try:
            instance_url = self.config.get('servicenow', {}).get('instance_url', '')
            query_filter = self.config.get('extraction', {}).get('query_filter', 'assignment_groupLIKEnetwork')
            
            url = f"{instance_url}/api/now/table/incident"
            
            # Parameters for the API call
            params = {
                'sysparm_limit': sample_size,
                'sysparm_offset': 0,
                'sysparm_query': query_filter,
                'sysparm_fields': 'number,short_description,description,priority,state,assignment_group,opened_at,resolved_at,caller_id,location,cmdb_ci,sys_created_on,work_notes,comments,category,contact_type,reassignment_count'
            }
            
            logger.info(f"Extracting {sample_size} incidents from ServiceNow API...")
            logger.info(f"Query filter: {query_filter}")
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            incidents = data.get('result', [])
            
            if not incidents:
                logger.warning("No incidents returned from API")
                return pd.DataFrame()
            
            df = pd.DataFrame(incidents)
            
            # Rename columns to match expected format
            column_mapping = {
                'state': 'incident_state',
                'opened_at': 'opened_at',
                'resolved_at': 'u_resolved',
                'cmdb_ci': 'cmdb_ci'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)
            
            # Add missing columns with default values
            if 'u_ci_type' not in df.columns:
                df['u_ci_type'] = 'Unknown'
            if 'assigned_to' not in df.columns:
                df['assigned_to'] = 'Unassigned'
            if 'reassignment_count' not in df.columns:
                df['reassignment_count'] = 0
            
            logger.info(f"Successfully extracted {len(df)} incidents from ServiceNow API")
            logger.info(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error extracting from ServiceNow API: {e}")
            return pd.DataFrame()
    
    def load_original_data(self, sample_size=1000):
        """
        Load original ServiceNow data with PII
        
        Args:
            sample_size: Number of records to load for testing
            
        Returns:
            pd.DataFrame: Original data
        """
        try:
            if Path(self.original_file).exists():
                logger.info(f"Loading original data from: {self.original_file}")
                df = pd.read_csv(self.original_file, nrows=sample_size)
                logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
                return df
            else:
                logger.warning("Original file not found, creating sample data")
                return self.create_realistic_sample_data()
        except Exception as e:
            logger.error(f"Error loading original data: {e}")
            return self.create_realistic_sample_data()
    
    def load_redacted_data(self, sample_size=1000):
        """
        Load redacted ServiceNow data (PII removed)
        
        Args:
            sample_size: Number of records to load for testing
            
        Returns:
            pd.DataFrame: Redacted data
        """
        try:
            if Path(self.redacted_file).exists():
                logger.info(f"Loading redacted data from: {self.redacted_file}")
                df = pd.read_csv(self.redacted_file, nrows=sample_size)
                logger.info(f"Loaded {len(df)} redacted records")
                return df
            else:
                logger.warning("Redacted file not found")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading redacted data: {e}")
            return pd.DataFrame()
    
    def load_processed_data(self, sample_size=1000):
        """
        Load processed ServiceNow data (with ETL transformations)
        
        Args:
            sample_size: Number of records to load for testing
            
        Returns:
            pd.DataFrame: Processed data
        """
        try:
            if Path(self.processed_file).exists():
                logger.info(f"Loading processed data from: {self.processed_file}")
                df = pd.read_csv(self.processed_file, nrows=sample_size)
                logger.info(f"Loaded {len(df)} processed records")
                return df
            else:
                logger.warning("Processed file not found")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading processed data: {e}")
            return pd.DataFrame()
    
    def create_realistic_sample_data(self):
        """
        Create sample data that matches the real ServiceNow structure
        
        Returns:
            pd.DataFrame: Sample data with realistic columns
        """
        logger.info("Creating realistic sample data based on real ServiceNow structure")
        
        sample_data = {
            'number': ['INC7559964', 'INC7559965', 'INC7559966', 'INC7559967', 'INC7559968'],
            'reassignment_count': [1, 0, 2, 1, 0],
            'location': [
                '00269 - Izmir - Turkey / ESBAS 2 (PT Phase 1)',
                '00123 - London - UK / Office Building A',
                '00456 - Berlin - Germany / Data Center 1',
                '00789 - Paris - France / Regional Office',
                '00321 - Madrid - Spain / Branch Office'
            ],
            'assignment_group': [
                'Global Network Services', 
                'Local IT Support', 
                'Global Network Services',
                'EMEA Network Team',
                'Global Network Services'
            ],
            'opened_at': [
                '2025-07-16 03:33:52', 
                '2025-07-16 10:15:30', 
                '2025-07-15 14:22:18',
                '2025-07-14 09:45:12',
                '2025-07-13 16:30:45'
            ],
            'priority': ['3 - Moderate', '2 - High', '1 - Critical', '2 - High', '4 - Low'],
            'u_ci_type': ['Wireless', 'Firewall', 'Router', 'Switch', 'Access Point'],
            'assigned_to': [
                'Sasmal, Ashish', 
                'Smith, John', 
                'Jones, Sarah',
                'Mueller, Hans',
                'Garcia, Maria'
            ],
            'short_description': [
                'AP Down in Izmir site',
                'Firewall blocking legitimate traffic',
                'Router connectivity issues',
                'Switch port failures',
                'Wireless authentication problems'
            ],
            'description': [
                'The AP 269-TR-WAP008 with MAC address 70:e4:22:ac:b1:ea is down. Less than 50 users affected.',
                'Users unable to access external websites due to misconfigured firewall rules blocking HTTPS traffic.',
                'Router experiencing intermittent connectivity drops affecting multiple users in building.',
                'Multiple switch ports showing errors, affecting workstation connectivity in floor 3.',
                'Users unable to authenticate to wireless network, RADIUS server issues suspected.'
            ],
            'work_notes': [
                '2025-07-16 03:39:46 - Initial investigation shows power issue',
                '2025-07-16 10:20:00 - Firewall rules reviewed',
                '2025-07-15 14:30:00 - Router logs showing interface errors',
                '2025-07-14 10:00:00 - Switch replacement scheduled',
                '2025-07-13 17:00:00 - RADIUS server connectivity checked'
            ],
            'incident_state': ['In Progress', 'New', 'Resolved', 'In Progress', 'Resolved'],
            'caller_id': [
                'user1@company.com', 
                'user2@company.com', 
                'user3@company.com',
                'user4@company.com',
                'user5@company.com'
            ],
            'u_resolved': ['', '', '2025-07-16 08:30:00', '', '2025-07-14 12:15:30'],
            'category': ['Network', 'Security', 'Infrastructure', 'Network', 'Wireless'],
            'cmdb_ci': ['WAP008', 'FW001', 'RTR001', 'SW003', 'WAP015'],
            'contact_type': ['Phone', 'Email', 'Self-service', 'Phone', 'Email']
        }
        
        df = pd.DataFrame(sample_data)
        logger.info(f"Created sample data with {len(df)} records and {len(df.columns)} columns")
        return df
    
    def transform_with_real_etl(self, df_raw):
        """
        Transform data using the network ETL pipeline adapted for real data structure
        
        Args:
            df_raw: Raw ServiceNow data
            
        Returns:
            pd.DataFrame: Transformed data
        """
        from network_incident_etl import transform_incident_frame, log_pipeline_metrics
        
        logger.info("Starting ETL transformation for real data structure...")
        
        # Adapt column names to match what the ETL expects
        df_adapted = df_raw.copy()
        
        # Map real ServiceNow columns to expected ETL columns
        column_mapping = {
            'opened_at': 'opened',
            'u_resolved': 'resolved', 
            'u_ci_type': 'ci_type'
        }
        
        # Apply column mapping
        df_adapted.rename(columns=column_mapping, inplace=True)
        
        # Transform the data
        df_processed = transform_incident_frame(df_adapted)
        
        # Log metrics
        log_pipeline_metrics(
            df_raw, 
            df_processed, 
            engine=None,
            csv_fallback="real_data_metrics.csv"
        )
        
        logger.info(f"ETL transformation complete. {len(df_processed)} records processed.")
        return df_processed
    
    def apply_real_pii_redaction(self, df):
        """
        Apply PII redaction matching your real redaction process
        
        Args:
            df: DataFrame to redact
            
        Returns:
            pd.DataFrame: Redacted DataFrame
        """
        from redact5 import redact_dataframe_columns
        
        logger.info("Applying PII redaction for real data structure...")
        
        # Define columns based on real ServiceNow structure
        text_columns = ['short_description', 'description', 'work_notes']
        id_columns = ['number']
        drop_columns = ['caller_id', 'assigned_to']
        
        df_redacted = redact_dataframe_columns(
            df,
            text_columns=text_columns,
            id_columns=id_columns,
            drop_columns=drop_columns
        )
        
        # Additional location anonymization
        if 'location' in df_redacted.columns:
            # Keep country but remove specific site details
            # Extract country from location string like "00269 - Izmir - Turkey / ESBAS 2"
            df_redacted['location'] = df_redacted['location'].str.split(' - ').str[-1].str.split(' / ').str[0]
        
        logger.info("PII redaction complete")
        return df_redacted
    
    def analyze_real_data_patterns(self, df):
        """
        Analyze patterns in real ServiceNow data
        
        Args:
            df: Processed DataFrame
            
        Returns:
            dict: Analysis results
        """
        logger.info("Analyzing real data patterns...")
        
        analysis = {
            'total_incidents': len(df),
            'timestamp': datetime.now().isoformat()
        }
        
        # Basic statistics
        if 'isActive' in df.columns:
            analysis['active_incidents'] = int(df['isActive'].sum())
            analysis['resolved_incidents'] = int((~df['isActive']).sum())
        
        if 'isHighImpact' in df.columns:
            analysis['high_impact_incidents'] = int(df['isHighImpact'].sum())
        
        # Pattern analysis
        if 'patternCategory' in df.columns:
            analysis['pattern_distribution'] = df['patternCategory'].value_counts().to_dict()
        
        # Assignment group analysis
        if 'assignment_group' in df.columns:
            analysis['assignment_groups'] = df['assignment_group'].value_counts().head().to_dict()
        
        # Priority analysis
        if 'priority' in df.columns:
            analysis['priority_distribution'] = df['priority'].value_counts().to_dict()
        
        # Location analysis (if available and not redacted)
        if 'location' in df.columns:
            analysis['top_locations'] = df['location'].value_counts().head().to_dict()
        
        # SLA analysis
        if 'slaBreach' in df.columns:
            resolved = df[df['resolutionTimeHrs'].notna()]
            if not resolved.empty:
                analysis['sla_breach_rate'] = float((resolved['slaBreach'].sum() / len(resolved)) * 100)
        
        # Resolution time analysis
        if 'resolutionTimeHrs' in df.columns:
            resolved = df[df['resolutionTimeHrs'].notna()]
            if not resolved.empty:
                analysis['avg_resolution_hours'] = float(resolved['resolutionTimeHrs'].mean())
                analysis['median_resolution_hours'] = float(resolved['resolutionTimeHrs'].median())
        
        self._print_real_analysis_report(analysis)
        return analysis
    
    def _print_real_analysis_report(self, analysis):
        """Print formatted analysis report for real data"""
        print("\n" + "="*70)
        print("REAL SERVICENOW DATA ANALYSIS REPORT")
        print("="*70)
        
        print(f"\nBasic Statistics:")
        print(f"  Total Incidents: {analysis.get('total_incidents', 0)}")
        print(f"  Active Incidents: {analysis.get('active_incidents', 0)}")
        print(f"  Resolved Incidents: {analysis.get('resolved_incidents', 0)}")
        print(f"  High Impact Incidents: {analysis.get('high_impact_incidents', 0)}")
        
        if 'pattern_distribution' in analysis:
            print(f"\nIncident Categories:")
            for category, count in analysis['pattern_distribution'].items():
                percentage = (count / analysis['total_incidents']) * 100
                print(f"  {category}: {count} ({percentage:.1f}%)")
        
        if 'priority_distribution' in analysis:
            print(f"\nPriority Distribution:")
            for priority, count in analysis['priority_distribution'].items():
                percentage = (count / analysis['total_incidents']) * 100
                print(f"  {priority}: {count} ({percentage:.1f}%)")
        
        if 'assignment_groups' in analysis:
            print(f"\nTop Assignment Groups:")
            for group, count in analysis['assignment_groups'].items():
                print(f"  {group}: {count} incidents")
        
        if 'sla_breach_rate' in analysis:
            print(f"\nSLA Performance:")
            print(f"  SLA Breach Rate: {analysis['sla_breach_rate']:.1f}%")
        
        if 'avg_resolution_hours' in analysis:
            print(f"\nResolution Time Analysis:")
            print(f"  Average Resolution Time: {analysis['avg_resolution_hours']:.1f} hours")
            print(f"  Median Resolution Time: {analysis['median_resolution_hours']:.1f} hours")
    
    def save_analysis_results(self, df_processed, df_redacted, analysis):
        """
        Save all analysis results
        
        Args:
            df_processed: Processed data
            df_redacted: Redacted data  
            analysis: Analysis results
        """
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save processed data
            processed_file = output_dir / f"real_data_processed_{timestamp}.csv"
            df_processed.to_csv(processed_file, index=False)
            logger.info(f"Saved processed data: {processed_file}")
            
            # Save redacted data
            redacted_file = output_dir / f"real_data_redacted_{timestamp}.csv"
            df_redacted.to_csv(redacted_file, index=False)
            logger.info(f"Saved redacted data: {redacted_file}")
            
            # Save analysis
            analysis_file = output_dir / f"real_data_analysis_{timestamp}.json"
            import json
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            logger.info(f"Saved analysis: {analysis_file}")
            
            print(f"\nOutput Files:")
            print(f"  Processed data: {processed_file}")
            print(f"  Redacted data: {redacted_file}")
            print(f"  Analysis results: {analysis_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def run_real_data_pipeline(self, sample_size=1000, use_api=None):
        """
        Run the complete pipeline with real data or API
        
        Args:
            sample_size: Number of records to process
            use_api: Override the instance setting to use API or not
            
        Returns:
            bool: Success status
        """
        try:
            print("Real ServiceNow Data Pipeline")
            print("=" * 40)
            
            # Determine data source
            if use_api is not None:
                self.use_api = use_api
            
            # Load data
            if self.use_api:
                print(f"\nStep 1: Connecting to ServiceNow API...")
                if self.connect_to_servicenow():
                    print(f"Step 1b: Extracting data from API (sample size: {sample_size})...")
                    df_raw = self.extract_from_servicenow_api(sample_size)
                else:
                    print("API connection failed, falling back to local files...")
                    df_raw = self.load_original_data(sample_size)
            else:
                print(f"\nStep 1: Loading original data from files (sample size: {sample_size})...")
                df_raw = self.load_original_data(sample_size)
            
            if df_raw.empty:
                logger.error("No data loaded")
                return False
            
            print(f"Loaded {len(df_raw)} records with columns: {list(df_raw.columns)[:5]}...")
            
            # Transform data
            print("\nStep 2: Applying ETL transformation...")
            df_processed = self.transform_with_real_etl(df_raw)
            
            # Apply redaction
            print("\nStep 3: Applying PII redaction...")
            df_redacted = self.apply_real_pii_redaction(df_processed)
            
            # Analyze data
            print("\nStep 4: Analyzing data patterns...")
            analysis = self.analyze_real_data_patterns(df_processed)
            
            # Save results
            print("\nStep 5: Saving results...")
            self.save_analysis_results(df_processed, df_redacted, analysis)
            
            print("\n" + "="*70)
            print("REAL DATA PIPELINE COMPLETE!")
            print("="*70)
            
            # Show data source info
            data_source = "ServiceNow API" if self.use_api and self.session else "Local Files"
            print(f"Data Source: {data_source}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in real data pipeline: {e}")
            return False

def main():
    """Main execution function"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ServiceNow Data Extraction Pipeline')
    parser.add_argument('--api', action='store_true', help='Use ServiceNow API instead of local files')
    parser.add_argument('--sample-size', type=int, default=100, help='Number of records to process (default: 100)')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = RealDataServiceNowExtractor(use_api=args.api, config_path=args.config)
    
    # Show configuration
    print("Configuration:")
    print(f"  Data Source: {'ServiceNow API' if args.api else 'Local Files'}")
    print(f"  Sample Size: {args.sample_size}")
    
    if args.api:
        print("\nAPI Mode Requirements:")
        print("1. Set ServiceNow credentials in config.json OR environment variables:")
        print("   - SNOW_INSTANCE_URL=https://your-instance.service-now.com")
        print("   - SNOW_USERNAME=your_username")
        print("   - SNOW_PASSWORD=your_password")
        print("2. Ensure network connectivity to ServiceNow instance")
        print()
    
    # Run pipeline
    success = extractor.run_real_data_pipeline(sample_size=args.sample_size)
    
    if success:
        print("\nData pipeline completed successfully!")
        print("\nNext steps:")
        if args.api:
            print("1. Increase --sample-size for more data")
            print("2. Schedule regular API extractions")
            print("3. Set up monitoring for API rate limits")
        else:
            print("1. Increase --sample-size for full file processing")
            print("2. Compare results with your existing processed files")
            print("3. Consider using --api flag for live data")
    else:
        print("\nPipeline failed. Check logs for details.")
        if args.api:
            print("Try running without --api flag to use local files.")


# Alternative function for direct use without command line args
def run_with_api():
    """Run the pipeline with ServiceNow API"""
    extractor = RealDataServiceNowExtractor(use_api=True)
    return extractor.run_real_data_pipeline(sample_size=50, use_api=True)

def run_with_files():
    """Run the pipeline with local files"""
    extractor = RealDataServiceNowExtractor(use_api=False)
    return extractor.run_real_data_pipeline(sample_size=100, use_api=False)

if __name__ == "__main__":
    main()
