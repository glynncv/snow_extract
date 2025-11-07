"""
ServiceNow API Connection Test
=============================

Simple script to test ServiceNow API connectivity and data extraction.
"""

import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_servicenow_connection():
    """
    Test connection to ServiceNow API and extract sample data
    """
    print("ServiceNow API Connection Test")
    print("=" * 40)
    
    # Get credentials from environment variables or config
    instance_url = os.getenv('SNOW_INSTANCE_URL', '')
    username = os.getenv('SNOW_USERNAME', '')
    password = os.getenv('SNOW_PASSWORD', '')
    
    # Check if credentials are provided
    if not all([instance_url, username, password]):
        print("\n❌ ServiceNow credentials not found!")
        print("\nTo test API connection, set these environment variables:")
        print("  set SNOW_INSTANCE_URL=https://your-instance.service-now.com")
        print("  set SNOW_USERNAME=your_username")
        print("  set SNOW_PASSWORD=your_password")
        print("\nOr create a .env file with these values.")
        return False
    
    print(f"\n🔗 Testing connection to: {instance_url}")
    
    try:
        # Set up authentication
        auth = HTTPBasicAuth(username, password)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Test connection with a simple query
        test_url = f"{instance_url}/api/now/table/incident"
        params = {
            'sysparm_limit': 5,  # Just get 5 records for testing
            'sysparm_fields': 'number,short_description,priority,state,opened_at'
        }
        
        logger.info("Making API request...")
        response = requests.get(test_url, auth=auth, headers=headers, params=params, timeout=30)
        
        # Check response
        if response.status_code == 200:
            print("✅ Successfully connected to ServiceNow!")
            
            # Parse the response
            data = response.json()
            incidents = data.get('result', [])
            
            if incidents:
                print(f"📊 Retrieved {len(incidents)} sample incidents:")
                print()
                
                # Display sample data
                df = pd.DataFrame(incidents)
                for i, incident in enumerate(incidents, 1):
                    print(f"  {i}. {incident.get('number', 'N/A')} - {incident.get('short_description', 'No description')[:50]}...")
                    print(f"     Priority: {incident.get('priority', 'N/A')}, State: {incident.get('state', 'N/A')}")
                    print()
                
                # Show available columns
                print(f"📋 Available columns: {list(df.columns)}")
                
                return True
            else:
                print("⚠️  Connection successful but no incidents returned")
                print("   Check your query filters or data access permissions")
                return True
                
        elif response.status_code == 401:
            print("❌ Authentication failed!")
            print("   Check your username and password")
            return False
            
        elif response.status_code == 403:
            print("❌ Access denied!")
            print("   Your account may not have permission to access incident data")
            return False
            
        else:
            print(f"❌ Connection failed with status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error!")
        print("   Check your instance URL and network connectivity")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ Request timeout!")
        print("   ServiceNow instance may be slow or unavailable")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def extract_network_incidents(sample_size=10):
    """
    Extract network-related incidents from ServiceNow
    
    Args:
        sample_size: Number of incidents to extract
        
    Returns:
        pd.DataFrame: Network incidents data
    """
    instance_url = os.getenv('SNOW_INSTANCE_URL', '')
    username = os.getenv('SNOW_USERNAME', '')
    password = os.getenv('SNOW_PASSWORD', '')
    
    if not all([instance_url, username, password]):
        logger.error("ServiceNow credentials not configured")
        return pd.DataFrame()
    
    try:
        auth = HTTPBasicAuth(username, password)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        url = f"{instance_url}/api/now/table/incident"
        params = {
            'sysparm_limit': sample_size,
            'sysparm_query': 'assignment_groupLIKEnetwork',  # Filter for network incidents
            'sysparm_fields': 'number,short_description,description,priority,state,assignment_group,opened_at,resolved_at,caller_id,location,cmdb_ci'
        }
        
        logger.info(f"Extracting {sample_size} network incidents...")
        response = requests.get(url, auth=auth, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        incidents = data.get('result', [])
        
        if incidents:
            df = pd.DataFrame(incidents)
            logger.info(f"Successfully extracted {len(df)} network incidents")
            return df
        else:
            logger.warning("No network incidents found")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error extracting network incidents: {e}")
        return pd.DataFrame()

def save_sample_data():
    """
    Extract sample data and save to local file for testing
    """
    print("\n📥 Extracting sample network incidents...")
    
    df = extract_network_incidents(sample_size=20)
    
    if not df.empty:
        # Save to data directory
        output_file = "data/raw/servicenow_api_sample.csv"
        os.makedirs("data/raw", exist_ok=True)
        
        df.to_csv(output_file, index=False)
        print(f"✅ Saved {len(df)} incidents to: {output_file}")
        
        # Show summary
        print(f"\n📊 Sample Data Summary:")
        print(f"  Total Records: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        
        if 'priority' in df.columns:
            print(f"  Priority Distribution:")
            priority_counts = df['priority'].value_counts()
            for priority, count in priority_counts.items():
                print(f"    {priority}: {count}")
        
        return True
    else:
        print("❌ No data extracted")
        return False

def main():
    """Main test function"""
    # Test basic connection
    connection_success = test_servicenow_connection()
    
    if connection_success:
        # Try to extract and save sample data
        save_sample_data()
        
        print("\n🎉 ServiceNow API test completed!")
        print("\nNext steps:")
        print("1. Use the real_data_extraction.py script with --api flag")
        print("2. Increase sample sizes for production use")
        print("3. Set up scheduled extractions")
    else:
        print("\n❌ API test failed")
        print("Fix the connection issues before proceeding")

if __name__ == "__main__":
    main()
