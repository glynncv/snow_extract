"""
ServiceNow API Client
====================

REST API client for ServiceNow with connection management and error handling.
"""

import requests
from requests.auth import HTTPBasicAuth
import logging
from typing import List, Dict, Any, Optional
import time

from snow_analytics.connectors.exceptions import (
    ConnectionError,
    AuthenticationError,
    APIError,
    RateLimitError
)

logger = logging.getLogger(__name__)

# Disable SSL warnings (can be overridden by verify_ssl parameter)
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass


class ServiceNowAPI:
    """
    ServiceNow REST API client.

    Handles connection, authentication, and API requests with retry logic.

    Examples:
        >>> api = ServiceNowAPI(
        ...     instance_url='https://instance.service-now.com',
        ...     username='admin',
        ...     password='password'
        ... )
        >>> if api.connect():
        ...     incidents = api.get_incidents(limit=100)
    """

    def __init__(
        self,
        instance_url: str,
        username: str,
        password: str,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3
    ):
        """
        Initialize ServiceNow API client.

        Args:
            instance_url: ServiceNow instance URL
            username: ServiceNow username
            password: ServiceNow password
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts
        """
        self.instance_url = instance_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries

        self.session = None
        self.auth = None

        if not verify_ssl:
            logger.warning("SSL certificate verification is disabled")

    def connect(self) -> bool:
        """
        Establish connection to ServiceNow API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.auth = HTTPBasicAuth(self.username, self.password)
            self.session = requests.Session()
            self.session.auth = self.auth
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })

            # Test connection
            test_url = f"{self.instance_url}/api/now/table/incident"
            response = self.session.get(
                test_url,
                params={'sysparm_limit': 1},
                timeout=self.timeout,
                verify=self.verify_ssl
            )

            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check credentials.")

            response.raise_for_status()

            logger.info("Successfully connected to ServiceNow API")
            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Authentication failed. Check username and password.")
            else:
                logger.error(f"HTTP error during connection: {e}")
            return False

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return False

        except Exception as e:
            logger.error(f"Failed to connect to ServiceNow: {e}")
            self.session = None
            self.auth = None
            return False

    def get_incidents(
        self,
        query: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get incidents from ServiceNow.

        Args:
            query: ServiceNow query string (e.g., 'assignment_groupLIKEnetwork')
            limit: Maximum number of records to fetch
            offset: Record offset for pagination
            fields: List of fields to return (None = all fields)

        Returns:
            List of incident dictionaries
        """
        if not self.session:
            raise ConnectionError("Not connected to ServiceNow. Call connect() first.")

        url = f"{self.instance_url}/api/now/table/incident"

        params = {
            'sysparm_limit': limit,
            'sysparm_offset': offset
        }

        if query:
            params['sysparm_query'] = query

        if fields:
            params['sysparm_fields'] = ','.join(fields)

        logger.info(f"Fetching incidents (limit={limit}, offset={offset})")

        try:
            response = self._make_request('GET', url, params=params)
            incidents = response.get('result', [])

            logger.info(f"Retrieved {len(incidents)} incidents")
            return incidents

        except Exception as e:
            logger.error(f"Error fetching incidents: {e}")
            raise

    def get_incident(self, incident_number: str) -> Dict[str, Any]:
        """
        Get a single incident by number.

        Args:
            incident_number: Incident ticket number (e.g., 'INC0012345')

        Returns:
            Incident dictionary
        """
        if not self.session:
            raise ConnectionError("Not connected to ServiceNow. Call connect() first.")

        url = f"{self.instance_url}/api/now/table/incident"

        params = {
            'sysparm_query': f'number={incident_number}',
            'sysparm_limit': 1
        }

        logger.debug(f"Fetching incident: {incident_number}")

        try:
            response = self._make_request('GET', url, params=params)
            incidents = response.get('result', [])

            if not incidents:
                raise ValueError(f"Incident {incident_number} not found")

            return incidents[0]

        except Exception as e:
            logger.error(f"Error fetching incident {incident_number}: {e}")
            raise

    def get_timeline(self, sys_id: str) -> List[Dict[str, Any]]:
        """
        Get timeline/journal entries for an incident.

        Args:
            sys_id: Incident sys_id

        Returns:
            List of journal entries
        """
        if not self.session:
            raise ConnectionError("Not connected to ServiceNow. Call connect() first.")

        url = f"{self.instance_url}/api/now/table/sys_journal_field"

        params = {
            'sysparm_query': f'name=incident^element_id={sys_id}',
            'sysparm_fields': 'sys_created_on,name,value,element_id,element',
            'sysparm_order_by': 'sys_created_on'
        }

        logger.debug(f"Fetching timeline for sys_id: {sys_id}")

        try:
            response = self._make_request('GET', url, params=params)
            entries = response.get('result', [])

            logger.debug(f"Retrieved {len(entries)} timeline entries")
            return entries

        except Exception as e:
            logger.warning(f"Could not retrieve timeline: {e}")
            return []

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            data: Request body data
            retry_count: Current retry attempt

        Returns:
            Response JSON as dictionary
        """
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )

            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.warning(f"Rate limited. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_request(method, url, params, data, retry_count + 1)
                else:
                    raise RateLimitError("API rate limit exceeded")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if retry_count < self.max_retries and e.response.status_code >= 500:
                # Retry on server errors
                wait_time = 2 ** retry_count
                logger.warning(f"Server error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._make_request(method, url, params, data, retry_count + 1)
            else:
                raise APIError(f"API request failed: {e}")

        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}")

    def close(self):
        """Close the API session."""
        if self.session:
            self.session.close()
            self.session = None
            self.auth = None
            logger.debug("API session closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
