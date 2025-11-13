"""
Quick SSL Test for ServiceNow Scripts
=====================================
Tests which scripts need SSL verification bypass
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path

# Load .env file if available
try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_files = [
        project_root / ".env",
        project_root.parent / "snow_extract" / ".env",
        Path(r"C:\Users\cglynn\myPython\snow_extract\.env")
    ]
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=False)
            break
except ImportError:
    pass

def test_ssl_connection(verify_ssl=True):
    """Test ServiceNow connection with/without SSL verification"""
    
    instance_url = os.getenv('SNOW_INSTANCE_URL', '')
    username = os.getenv('SNOW_USERNAME', '')
    password = os.getenv('SNOW_PASSWORD', '')
    
    if not all([instance_url, username, password]):
        print("ERROR: ServiceNow credentials not found in environment")
        print("Set SNOW_INSTANCE_URL, SNOW_USERNAME, and SNOW_PASSWORD")
        return False
    
    print(f"Testing connection to: {instance_url}")
    print(f"SSL Verification: {'ENABLED' if verify_ssl else 'DISABLED'}")
    print("-" * 60)
    
    try:
        auth = HTTPBasicAuth(username, password)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        test_url = f"{instance_url}/api/now/table/incident"
        params = {'sysparm_limit': 1}
        
        response = requests.get(test_url, auth=auth, headers=headers, 
                               params=params, timeout=30, verify=verify_ssl)
        response.raise_for_status()
        
        print("SUCCESS: Connection successful!")
        return True
        
    except requests.exceptions.SSLError as e:
        print(f"SSL ERROR: {str(e)[:100]}")
        print("\nThis script needs --no-verify-ssl flag or SSL fix")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)[:100]}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test SSL connection to ServiceNow')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification')
    args = parser.parse_args()
    
    print("=" * 60)
    print("ServiceNow SSL Connection Test")
    print("=" * 60)
    print()
    
    # Test with SSL verification
    print("Test 1: With SSL verification (default)")
    result1 = test_ssl_connection(verify_ssl=True)
    print()
    
    # Test without SSL verification
    print("Test 2: Without SSL verification")
    result2 = test_ssl_connection(verify_ssl=False)
    print()
    
    print("=" * 60)
    print("Summary:")
    print(f"  With SSL verification: {'PASS' if result1 else 'FAIL'}")
    print(f"  Without SSL verification: {'PASS' if result2 else 'FAIL'}")
    
    if not result1 and result2:
        print("\nRECOMMENDATION: Use --no-verify-ssl flag for all scripts")
    elif result1:
        print("\nSSL verification works - no changes needed")
    else:
        print("\nBoth tests failed - check credentials and network connectivity")

