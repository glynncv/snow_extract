"""
Simple ServiceNow Connection Test with Microsoft SSO
===================================================

A minimal script to test ServiceNow REST API connection using Microsoft SSO/OAuth 2.0
and pull incident data. Supports both OAuth flows and API key authentication.
"""

import requests
import pandas as pd
import json
from datetime import datetime
import os
import base64
import urllib.parse
from requests_oauthlib import OAuth2Session
import webbrowser
import argparse

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

class ServiceNowSSOConnector:
    """ServiceNow API connector with Microsoft SSO support"""
    
    def __init__(self, instance_url, auth_method='oauth', verify_ssl=True, **auth_params):
        """
        Initialize ServiceNow connection with SSO
        
        Args:
            instance_url: Your ServiceNow instance URL
            auth_method: 'oauth', 'api_key', or 'basic'
            verify_ssl: If False, disable SSL certificate verification (not recommended for production)
            **auth_params: Authentication parameters based on method
        """
        self.instance_url = instance_url.rstrip('/')
        self.auth_method = auth_method
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.access_token = None
        
        if not verify_ssl:
            print("WARNING: SSL certificate verification is disabled. This is not recommended for production use.")
        
        # Common headers
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Set up authentication based on method
        if auth_method == 'oauth':
            self._setup_oauth(**auth_params)
        elif auth_method == 'api_key':
            self._setup_api_key(**auth_params)
        elif auth_method == 'basic':
            self._setup_basic_auth(**auth_params)
        else:
            raise ValueError("auth_method must be 'oauth', 'api_key', or 'basic'")
    
    def _setup_oauth(self, client_id, client_secret, redirect_uri='http://localhost:8080/callback', **kwargs):
        """Set up OAuth 2.0 authentication"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_base_url = f"{self.instance_url}/oauth_auth.do"
        self.token_url = f"{self.instance_url}/oauth_token.do"
        
    def _setup_api_key(self, api_key, **kwargs):
        """Set up API key authentication"""
        self.headers['Authorization'] = f'Bearer {api_key}'
        
    def _setup_basic_auth(self, username, password, **kwargs):
        """Set up basic authentication (fallback)"""
        from requests.auth import HTTPBasicAuth
        self.session.auth = HTTPBasicAuth(username, password)
    
    def authenticate_oauth(self):
        """Perform OAuth 2.0 authentication flow"""
        print("Starting OAuth authentication...")
        
        try:
            # Create OAuth session
            oauth = OAuth2Session(
                self.client_id, 
                redirect_uri=self.redirect_uri,
                scope=['useraccount']
            )
            
            # Get authorization URL
            authorization_url, state = oauth.authorization_url(
                self.authorization_base_url,
                access_type="offline",
                prompt="select_account"
            )
            
            print(f"Please go to this URL and authorize the application:")
            print(f"{authorization_url}")
            print("\nOpening browser automatically...")
            
            try:
                webbrowser.open(authorization_url)
            except:
                print("Could not open browser automatically. Please copy the URL above.")
            
            # Get the authorization response
            authorization_response = input("\nPaste the full redirect URL here: ").strip()
            
            # Fetch token
            token = oauth.fetch_token(
                self.token_url,
                authorization_response=authorization_response,
                client_secret=self.client_secret
            )
            
            self.access_token = token['access_token']
            self.headers['Authorization'] = f'Bearer {self.access_token}'
            
            print("✅ OAuth authentication successful!")
            return True
            
        except Exception as e:
            print(f"❌ OAuth authentication failed: {e}")
            return False
    
    def authenticate_with_device_code(self, client_id, tenant_id=None):
        """
        Alternative: Device code flow for Microsoft SSO
        Better for automated/headless environments
        """
        print("Starting device code authentication...")
        
        # Microsoft device code endpoint
        tenant = tenant_id or 'common'
        device_code_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        
        # Request device code
        device_code_data = {
            'client_id': client_id,
            'scope': 'https://graph.microsoft.com/.default offline_access'
        }
        
        try:
            response = requests.post(device_code_url, data=device_code_data, verify=self.verify_ssl)
            response.raise_for_status()
            
            device_info = response.json()
            
            print(f"\nTo sign in, use a web browser to open the page:")
            print(f"{device_info['verification_uri']}")
            print(f"\nAnd enter the code: {device_info['user_code']}")
            print(f"\nWaiting for authentication... (expires in {device_info['expires_in']} seconds)")
            
            # Poll for token
            token_data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'client_id': client_id,
                'device_code': device_info['device_code']
            }
            
            import time
            interval = device_info.get('interval', 5)
            
            for _ in range(device_info['expires_in'] // interval):
                time.sleep(interval)
                
                token_response = requests.post(token_url, data=token_data, verify=self.verify_ssl)
                token_result = token_response.json()
                
                if 'access_token' in token_result:
                    print("✅ Device code authentication successful!")
                    # Note: This gets Microsoft Graph token, you'd need to exchange it for ServiceNow token
                    return token_result['access_token']
                elif token_result.get('error') == 'authorization_pending':
                    continue
                else:
                    print(f"❌ Authentication error: {token_result.get('error_description')}")
                    return None
            
            print("❌ Authentication timed out")
            return None
            
        except Exception as e:
            print(f"❌ Device code authentication failed: {e}")
            return None
    
    def test_connection(self):
        """Test the connection to ServiceNow"""
        print("Testing ServiceNow connection...")
        
        # If using OAuth and no token, authenticate first
        if self.auth_method == 'oauth' and not self.access_token:
            if not self.authenticate_oauth():
                return False
        
        try:
            # Simple test - get one incident record
            url = f"{self.instance_url}/api/now/table/incident"
            params = {'sysparm_limit': 1}
            
            response = self.session.get(
                url, 
                headers=self.headers, 
                params=params,
                timeout=30,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                print("✅ Connection successful!")
                data = response.json()
                result_count = len(data.get('result', []))
                print(f"   Test query returned {result_count} record(s)")
                return True
            elif response.status_code == 401:
                print("❌ Authentication failed!")
                print("   Check your credentials or OAuth setup")
                return False
            else:
                print(f"❌ Connection failed!")
                print(f"   Status code: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def get_incidents(self, limit=100, filters=None):
        """Pull incident data from ServiceNow"""
        print(f"Pulling {limit} incidents from ServiceNow...")
        
        url = f"{self.instance_url}/api/now/table/incident"
        
        params = {
            'sysparm_limit': limit,
            'sysparm_fields': 'number,short_description,description,priority,state,assignment_group,opened_at,resolved_at,caller_id,location'
        }
        
        if filters:
            params['sysparm_query'] = filters
        
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=60,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                data = response.json()
                incidents = data.get('result', [])
                
                if incidents:
                    df = pd.DataFrame(incidents)
                    print(f"✅ Successfully retrieved {len(df)} incidents")
                    return df
                else:
                    print("⚠️  No incidents found matching criteria")
                    return pd.DataFrame()
            else:
                print(f"❌ Failed to retrieve incidents")
                print(f"   Status code: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return pd.DataFrame()
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error retrieving incidents: {e}")
            return pd.DataFrame()
    
    def get_recent_incidents(self, days=7):
        """Get incidents from the last N days"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        date_filter = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        
        filters = f"opened_at>={date_filter}"
        print(f"Getting incidents from last {days} days (since {date_filter})")
        
        return self.get_incidents(limit=500, filters=filters)
    
    def get_network_incidents(self, limit=100):
        """Get incidents assigned to network-related groups"""
        filters = "assignment_groupLIKEnetwork"
        print("Getting network-related incidents...")
        
        return self.get_incidents(limit=limit, filters=filters)

def display_incident_summary(df):
    """Display a summary of the incident data"""
    if df.empty:
        print("No data to summarize")
        return
    
    print("\n" + "="*50)
    print("INCIDENT DATA SUMMARY")
    print("="*50)
    
    print(f"Total Records: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Show sample data
    print(f"\nSample Records (first 3):")
    if len(df) > 0:
        for i, row in df.head(3).iterrows():
            print(f"\nRecord {i+1}:")
            print(f"  Number: {row.get('number', 'N/A')}")
            print(f"  Description: {str(row.get('short_description', 'N/A'))[:50]}...")
            print(f"  Priority: {row.get('priority', 'N/A')}")
            print(f"  State: {row.get('state', 'N/A')}")

def save_to_csv(df, filename=None):
    """Save DataFrame to CSV file"""
    if df.empty:
        print("No data to save")
        return
    
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"servicenow_incidents_{timestamp}.csv"
    
    try:
        df.to_csv(filename, index=False)
        print(f"✅ Data saved to: {filename}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

def main():
    """Main test function with multiple authentication options"""
    print("ServiceNow SSO Connection Test")
    print("=" * 35)
    
    # Configuration - Choose your authentication method
    INSTANCE_URL = "https://yourinstance.service-now.com"  # Replace with your instance
    
    print("\nAuthentication Options:")
    print("1. OAuth 2.0 (recommended for SSO)")
    print("2. API Key")
    print("3. Basic Auth (fallback)")
    print("4. Use environment variables")
    
    choice = input("\nSelect authentication method (1-4): ").strip()
    
    try:
        if choice == "1":
            # OAuth 2.0 setup
            print("\nOAuth 2.0 Setup:")
            print("You need to register an OAuth application in ServiceNow first.")
            print("Go to: System OAuth > Application Registry > New > Create an OAuth API endpoint")
            
            client_id = input("Enter Client ID: ").strip()
            client_secret = input("Enter Client Secret: ").strip()
            
            if not client_id or not client_secret:
                print("❌ Client ID and Secret are required for OAuth")
                return
            
            snow = ServiceNowSSOConnector(
                INSTANCE_URL, 
                auth_method='oauth',
                verify_ssl=not args.no_verify_ssl,
                client_id=client_id,
                client_secret=client_secret
            )
            
        elif choice == "2":
            # API Key setup
            api_key = input("Enter API Key: ").strip()
            
            if not api_key:
                print("❌ API Key is required")
                return
            
            snow = ServiceNowSSOConnector(
                INSTANCE_URL, 
                auth_method='api_key',
                verify_ssl=not args.no_verify_ssl,
                api_key=api_key
            )
            
        elif choice == "3":
            # Basic auth fallback
            username = input("Enter Username: ").strip()
            password = input("Enter Password: ").strip()
            
            if not username or not password:
                print("❌ Username and Password are required")
                return
            
            snow = ServiceNowSSOConnector(
                INSTANCE_URL, 
                auth_method='basic',
                verify_ssl=not args.no_verify_ssl,
                username=username,
                password=password
            )
            
        elif choice == "4":
            # Environment variables
            instance_url = os.getenv('SNOW_INSTANCE_URL')
            auth_method = os.getenv('SNOW_AUTH_METHOD', 'oauth')
            
            if auth_method == 'oauth':
                client_id = os.getenv('SNOW_CLIENT_ID')
                client_secret = os.getenv('SNOW_CLIENT_SECRET')
                snow = ServiceNowSSOConnector(
                    instance_url, 
                    auth_method='oauth',
                    verify_ssl=not args.no_verify_ssl,
                    client_id=client_id,
                    client_secret=client_secret
                )
            elif auth_method == 'api_key':
                api_key = os.getenv('SNOW_API_KEY')
                snow = ServiceNowSSOConnector(
                    instance_url, 
                    auth_method='api_key',
                    verify_ssl=not args.no_verify_ssl,
                    api_key=api_key
                )
            else:
                print("❌ Environment variables not properly configured")
                return
        else:
            print("❌ Invalid choice")
            return
    
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return
    
    # Test connection
    if not snow.test_connection():
        print("Cannot proceed without valid connection")
        return
    
    print("\n" + "-" * 50)
    print("Testing data retrieval...")
    
    # Test data pulls
    print("\n1. Recent incidents (last 7 days):")
    df_recent = snow.get_recent_incidents(days=7)
    if not df_recent.empty:
        display_incident_summary(df_recent)
        save_to_csv(df_recent, "recent_incidents.csv")
    
    print("\n2. Network-related incidents:")
    df_network = snow.get_network_incidents(limit=50)
    if not df_network.empty:
        display_incident_summary(df_network)
        save_to_csv(df_network, "network_incidents.csv")
    
    print("\n" + "="*50)
    print("TEST COMPLETE!")
    print("="*50)
    
    if not df_recent.empty or not df_network.empty:
        print("✅ Successfully connected and retrieved data")
        print("📁 Check the generated CSV files for detailed data")
    else:
        print("⚠️  Connected but no data retrieved - check your filters and permissions")

def setup_oauth_app_instructions():
    """Print instructions for setting up OAuth in ServiceNow"""
    print("""
    OAuth Application Setup in ServiceNow:
    =====================================
    
    1. Log into your ServiceNow instance as an admin
    2. Navigate to: System OAuth > Application Registry
    3. Click "New" and select "Create an OAuth API endpoint for external clients"
    4. Fill out the form:
       - Name: "Python API Client" (or any descriptive name)
       - Client ID: (will be auto-generated, copy this)
       - Client Secret: (will be auto-generated, copy this)
       - Redirect URL: http://localhost:8080/callback
       - Accessible from: All application scopes
    5. Save the record
    6. Copy the Client ID and Client Secret for use in this script
    
    For Microsoft SSO integration, you may also need to:
    - Configure SAML/OAuth integration between ServiceNow and Microsoft
    - Set up proper user provisioning
    - Configure the appropriate scopes and permissions
    """)

if __name__ == "__main__":
    print("Need help setting up OAuth? Run:")
    print("python script.py --setup-help")
    
    if len(os.sys.argv) > 1 and '--setup-help' in os.sys.argv:
        setup_oauth_app_instructions()
    else:
        main()