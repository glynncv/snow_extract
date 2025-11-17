"""
Debug script to test the ETL transformation
"""
import sys
from pathlib import Path

# Add src directory to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import pandas as pd
from network_incident_etl import transform_incident_frame

# Create sample data
sample_data = {
    'number': ['INC0010001', 'INC0010002'],
    'short_description': ['WiFi issue', 'VPN problem'],
    'priority': ['2 - High', '1 - Critical'],
    'incident_state': ['New', 'In Progress'],
    'opened': ['2025-07-15 09:30:00', '2025-07-15 14:20:00'],
    'resolved': ['', '2025-07-15 16:45:00']
}

df_raw = pd.DataFrame(sample_data)
print("Raw data columns:", list(df_raw.columns))
print("Raw data:")
print(df_raw)

# Transform data
df_processed = transform_incident_frame(df_raw)
print("\nProcessed data columns:", list(df_processed.columns))
print("Processed data:")
print(df_processed)

# Check specific columns
if 'isActive' in df_processed.columns:
    print(f"\nActive incidents: {df_processed['isActive'].sum()}")
if 'isHighImpact' in df_processed.columns:
    print(f"High impact incidents: {df_processed['isHighImpact'].sum()}")
