"""
Data Pipeline Analysis Utility
=============================

This script analyzes the data flow between the original, redacted, and processed files
to understand the complete ServiceNow data processing pipeline.
"""

import pandas as pd
import logging
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_data_pipeline():
    """
    Analyze the complete data pipeline from original to processed files
    """
    
    # File paths (you may need to adjust these based on your actual file locations)
    files = {
        'original': r"C:\Users\cglynn\myPython\pii-redaction-utility\data\archive\IM_Network_EMEA_2025.csv",
        'redacted': r"C:\Users\cglynn\myPython\pii-redaction-utility\data\processed\IM_Network_EMEA_2025_redacted_clean.csv",
        'processed': r"C:\Users\cglynn\myPython\Networks_IM_2025\data\processed\IM_Network_EMEA_2025_redacted_clean_analysed.csv"
    }
    
    print("ServiceNow Data Pipeline Analysis")
    print("=" * 50)
    
    results = {}
    
    for stage, file_path in files.items():
        try:
            if Path(file_path).exists():
                # Read just the header and a few rows to analyze structure
                df = pd.read_csv(file_path, nrows=5)
                results[stage] = {
                    'path': file_path,
                    'columns': list(df.columns),
                    'shape': df.shape,
                    'sample_data': df.head(2).to_dict('records') if len(df) > 0 else []
                }
                logger.info(f"Successfully loaded {stage} file: {len(df.columns)} columns")
            else:
                logger.warning(f"{stage} file not found: {file_path}")
                results[stage] = {'path': file_path, 'status': 'NOT_FOUND'}
                
        except Exception as e:
            logger.error(f"Error reading {stage} file: {e}")
            results[stage] = {'path': file_path, 'status': 'ERROR', 'error': str(e)}
    
    # Analyze the pipeline transformations
    print("\nPipeline Analysis:")
    print("-" * 30)
    
    if 'original' in results and 'columns' in results['original']:
        print(f"\n1. ORIGINAL DATA:")
        print(f"   File: {Path(results['original']['path']).name}")
        print(f"   Columns: {len(results['original']['columns'])}")
        print(f"   Key columns: {results['original']['columns'][:10]}...")  # Show first 10
        
        # Check for PII columns
        pii_columns = []
        for col in results['original']['columns']:
            if any(term in col.lower() for term in ['caller', 'email', 'phone', 'user', 'assigned_to']):
                pii_columns.append(col)
        if pii_columns:
            print(f"   PII columns detected: {pii_columns}")
    
    if 'redacted' in results and 'columns' in results['redacted']:
        print(f"\n2. REDACTED DATA:")
        print(f"   File: {Path(results['redacted']['path']).name}")
        print(f"   Columns: {len(results['redacted']['columns'])}")
        
        # Compare with original
        if 'original' in results and 'columns' in results['original']:
            original_cols = set(results['original']['columns'])
            redacted_cols = set(results['redacted']['columns'])
            
            removed_cols = original_cols - redacted_cols
            added_cols = redacted_cols - original_cols
            
            if removed_cols:
                print(f"   Columns removed: {list(removed_cols)}")
            if added_cols:
                print(f"   Columns added: {list(added_cols)}")
    
    if 'processed' in results and 'columns' in results['processed']:
        print(f"\n3. PROCESSED DATA (ETL Output):")
        print(f"   File: {Path(results['processed']['path']).name}")
        print(f"   Columns: {len(results['processed']['columns'])}")
        
        # Check for ETL-added columns
        etl_columns = []
        for col in results['processed']['columns']:
            if any(term in col.lower() for term in ['active', 'impact', 'pattern', 'resolution', 'sla', 'week']):
                etl_columns.append(col)
        if etl_columns:
            print(f"   ETL-added columns: {etl_columns}")
        
        # Compare with redacted
        if 'redacted' in results and 'columns' in results['redacted']:
            redacted_cols = set(results['redacted']['columns'])
            processed_cols = set(results['processed']['columns'])
            
            new_cols = processed_cols - redacted_cols
            if new_cols:
                print(f"   New analysis columns: {list(new_cols)}")
    
    return results

def create_sample_data_for_testing():
    """
    Create sample data that matches the structure of the real pipeline files
    for testing purposes
    """
    
    # Based on typical ServiceNow structure, create realistic sample data
    sample_data = {
        'number': ['INC7559964', 'INC7559965', 'INC7559966'],
        'reassignment_count': [1, 0, 2],
        'location': ['00269 - Izmir - Turkey', '00123 - London - UK', '00456 - Berlin - Germany'],
        'assignment_group': ['Global Network Services', 'Local IT Support', 'Global Network Services'],
        'opened_at': ['2025-07-16 03:33:52', '2025-07-16 10:15:30', '2025-07-15 14:22:18'],
        'priority': ['3 - Moderate', '2 - High', '1 - Critical'],
        'u_ci_type': ['Wireless', 'Firewall', 'Router'],
        'assigned_to': ['Sasmal, Ashish', 'Smith, John', 'Jones, Sarah'],
        'short_description': [
            'AP Down in Izmir site',
            'Firewall blocking legitimate traffic',
            'Router connectivity issues'
        ],
        'description': [
            'The AP 269-TR-WAP008 with MAC address 70:e4:22:ac:b1:ea is down.',
            'Users unable to access external websites due to firewall rules.',
            'Router experiencing intermittent connectivity drops affecting multiple users.'
        ],
        'incident_state': ['In Progress', 'New', 'Resolved'],
        'caller_id': ['user1@company.com', 'user2@company.com', 'user3@company.com'],
        'u_resolved': ['', '', '2025-07-16 08:30:00'],
        'category': ['Network', 'Security', 'Infrastructure'],
        'cmdb_ci': ['WAP008', 'FW001', 'RTR001']
    }
    
    return pd.DataFrame(sample_data)

def update_extraction_script_for_real_data():
    """
    Update the extraction script to work with the real data structure
    """
    print("\nRecommendations for updating extraction script:")
    print("-" * 50)
    
    print("1. Update column mapping in network_incident_etl.py:")
    print("   - 'opened_at' -> 'openedDate'")
    print("   - 'u_resolved' -> 'resolvedDate'")
    print("   - 'u_ci_type' -> 'ci_type'")
    
    print("\n2. Update PII redaction for real columns:")
    print("   - Remove 'caller_id', 'assigned_to'")
    print("   - Hash 'number' column")
    print("   - Truncate detailed location info")
    
    print("\n3. Update sample data in servicenow_extraction.py:")
    print("   - Use real column names from original data")
    print("   - Match priority format ('1 - Critical', '2 - High', etc.)")
    print("   - Use realistic incident descriptions")

def main():
    """
    Main function to run the data pipeline analysis
    """
    try:
        results = analyze_data_pipeline()
        
        print("\n" + "="*60)
        print("CREATING SAMPLE DATA FOR TESTING")
        print("="*60)
        
        # Create sample data that matches real structure
        sample_df = create_sample_data_for_testing()
        
        # Save sample data to current project
        output_path = Path("data/raw/sample_servicenow_data.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sample_df.to_csv(output_path, index=False)
        
        print(f"Sample data created: {output_path}")
        print(f"Columns: {list(sample_df.columns)}")
        print(f"Shape: {sample_df.shape}")
        
        update_extraction_script_for_real_data()
        
    except Exception as e:
        logger.error(f"Error in pipeline analysis: {e}")

if __name__ == "__main__":
    main()
