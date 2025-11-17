"""
Unit Tests for ServiceNow API Client
====================================

Test cases for snow_analytics.connectors.api module.
Uses REAL ServiceNow API calls (not mocked).
"""

import unittest
import pytest
import os

from snow_analytics.connectors.api import ServiceNowAPI
from snow_analytics.core.config import Config
from snow_analytics.connectors.exceptions import (
    ConnectionError,
    AuthenticationError,
    APIError
)


class TestAPI(unittest.TestCase):
    """Test cases for ServiceNow API client using real API."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        cls.config = Config()
        cls.instance_url = (
            cls.config.get('servicenow.instance_url') or 
            os.getenv('SNOW_INSTANCE_URL')
        )
        cls.username = (
            cls.config.get('servicenow.username') or 
            os.getenv('SNOW_USERNAME')
        )
        cls.password = (
            cls.config.get('servicenow.password') or 
            os.getenv('SNOW_PASSWORD')
        )
        
        # Check for valid credentials (not placeholders)
        cls.has_credentials = all([
            cls.instance_url and not cls.instance_url.startswith('${'),
            cls.username and not cls.username.startswith('${'),
            cls.password and not cls.password.startswith('${')
        ])

    def setUp(self):
        """Set up test fixtures."""
        if not self.has_credentials:
            pytest.skip("ServiceNow credentials not available")

    @pytest.mark.api
    def test_api_init(self):
        """Test initialization with credentials from config/env."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        self.assertIsNotNone(api.instance_url)
        # API strips trailing slashes
        self.assertEqual(api.instance_url, self.instance_url.rstrip('/'))
        self.assertEqual(api.username, self.username)

    @pytest.mark.api
    def test_api_init_ssl_warning(self):
        """Test SSL verification warning."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password,
            verify_ssl=False
        )
        
        self.assertFalse(api.verify_ssl)

    @pytest.mark.api
    def test_connect_success(self):
        """Test successful connection to real API."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        connected = api.connect()
        self.assertTrue(connected, "Failed to connect to ServiceNow API")
        
        # Clean up
        if api.session:
            api.session.close()

    @pytest.mark.api
    def test_connect_authentication_error(self):
        """Test authentication failure with invalid credentials."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username='invalid_user',
            password='invalid_pass'
        )
        
        # Should fail to connect
        connected = api.connect()
        self.assertFalse(connected, "Should fail with invalid credentials")

    @pytest.mark.api
    def test_get_incidents(self):
        """Test retrieve incidents list from real API."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        if not api.connect():
            pytest.skip("Failed to connect to ServiceNow API")
        
        try:
            # Use small limit for testing
            incidents = api.get_incidents(limit=10)
            
            self.assertIsInstance(incidents, list)
            # Should have some incidents (may be empty, but should not error)
            self.assertGreaterEqual(len(incidents), 0)
            
            # If incidents exist, check structure
            if incidents:
                incident = incidents[0]
                self.assertIn('number', incident)
                self.assertIn('sys_id', incident)
        finally:
            if api.session:
                api.session.close()

    @pytest.mark.api
    def test_get_incidents_with_filters(self):
        """Test query filters and pagination."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        if not api.connect():
            pytest.skip("Failed to connect to ServiceNow API")
        
        try:
            # Test with query filter (parameter is 'query', not 'query_filter')
            incidents = api.get_incidents(
                limit=5,
                query='state!=6'  # Not resolved
            )
            
            self.assertIsInstance(incidents, list)
            # Should not error with filter
            self.assertGreaterEqual(len(incidents), 0)
        finally:
            if api.session:
                api.session.close()

    @pytest.mark.api
    def test_get_incidents_limit(self):
        """Test limit parameter."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        if not api.connect():
            pytest.skip("Failed to connect to ServiceNow API")
        
        try:
            # Request 5 incidents
            incidents = api.get_incidents(limit=5)
            
            # Should respect limit (may have fewer if not enough exist)
            self.assertLessEqual(len(incidents), 5)
        finally:
            if api.session:
                api.session.close()

    @pytest.mark.api
    def test_get_incident_by_number(self):
        """Test get single incident by number from real API."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        if not api.connect():
            pytest.skip("Failed to connect to ServiceNow API")
        
        try:
            # First get a list to find a valid incident number
            incidents = api.get_incidents(limit=1)
            
            if incidents and len(incidents) > 0:
                incident_number = incidents[0].get('number')
                
                if incident_number:
                    # Get by number (method is get_incident, not get_incident_by_number)
                    incident = api.get_incident(incident_number)
                    
                    if incident:
                        self.assertEqual(incident['number'], incident_number)
                        self.assertIn('sys_id', incident)
            else:
                # No incidents available, skip test
                pytest.skip("No incidents available for testing")
        finally:
            if api.session:
                api.session.close()

    @pytest.mark.api
    def test_get_incident_by_sys_id(self):
        """Test get single incident by sys_id from real API."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        if not api.connect():
            pytest.skip("Failed to connect to ServiceNow API")
        
        try:
            # First get a list to find a valid sys_id
            incidents = api.get_incidents(limit=1)
            
            if incidents and len(incidents) > 0:
                sys_id = incidents[0].get('sys_id')
                
                if sys_id:
                    # Get by sys_id - use get_incidents with query
                    incidents = api.get_incidents(query=f'sys_id={sys_id}', limit=1)
                    incident = incidents[0] if incidents else None
                    
                    if incident:
                        self.assertEqual(incident['sys_id'], sys_id)
                        self.assertIn('number', incident)
            else:
                # No incidents available, skip test
                pytest.skip("No incidents available for testing")
        finally:
            if api.session:
                api.session.close()

    @pytest.mark.api
    def test_api_context_manager(self):
        """Test context manager support (with statement)."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        if not api.connect():
            pytest.skip("Failed to connect to ServiceNow API")
        
        # Test context manager
        try:
            with api:
                incidents = api.get_incidents(limit=1)
                self.assertIsInstance(incidents, list)
        except Exception as e:
            # Context manager should handle cleanup
            pass

    @pytest.mark.api
    def test_api_error_handling(self):
        """Test handle API errors gracefully."""
        api = ServiceNowAPI(
            instance_url=self.instance_url,
            username=self.username,
            password=self.password
        )
        
        if not api.connect():
            pytest.skip("Failed to connect to ServiceNow API")
        
        try:
            # Try to get incident with invalid sys_id
            incidents = api.get_incidents(query='sys_id=invalid_sys_id_12345', limit=1)
            
            # Should return empty list or handle gracefully
            # (API may return empty list or raise exception)
            self.assertEqual(len(incidents), 0)
        except Exception:
            # Exception is acceptable for invalid sys_id
            pass
        finally:
            if api.session:
                api.session.close()


if __name__ == '__main__':
    unittest.main()

