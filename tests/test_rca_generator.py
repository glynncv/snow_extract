"""
Unit Tests for RCA Generator
============================
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src directory to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from rca_generator import ServiceNowRCAGenerator
from rca_report_formatter import RCAReportFormatter


class TestRCAGenerator(unittest.TestCase):
    """Test cases for RCA Generator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_incident_data = {
            'incident': {
                'sys_id': 'test_sys_id_123',
                'number': 'INC0012345',
                'short_description': 'Test Incident',
                'description': 'Test incident description',
                'priority': '2 - High',
                'impact': '2 - High',
                'urgency': '1 - Critical',
                'state': '6 - Resolved',
                'category': 'Network',
                'assignment_group': {'display_value': 'Network Team'},
                'opened_at': '2025-01-15 10:00:00',
                'resolved_at': '2025-01-15 14:30:00',
                'resolution_notes': 'Configuration error fixed',
                'reassignment_count': 1
            },
            'timeline': [
                {
                    'timestamp': '2025-01-15 10:00:00',
                    'event_type': 'Incident Created',
                    'actor': 'Test User',
                    'description': 'Incident created',
                    'details': 'Test incident'
                },
                {
                    'timestamp': '2025-01-15 14:30:00',
                    'event_type': 'Incident Resolved',
                    'actor': 'Network Admin',
                    'description': 'Incident resolved',
                    'details': 'Configuration fixed'
                }
            ],
            'work_notes': [
                {
                    'timestamp': '2025-01-15 11:00:00',
                    'author': 'Network Admin',
                    'note': 'Investigating configuration issue'
                }
            ],
            'comments': [],
            'related_incidents': [],
            'related_problems': [],
            'related_changes': []
        }
    
    @patch('rca_generator.requests.Session')
    @patch('rca_generator.HTTPBasicAuth')
    def test_init_with_credentials(self, mock_auth, mock_session):
        """Test initialization with credentials"""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.get.return_value.status_code = 200
        mock_session_instance.get.return_value.raise_for_status = Mock()
        
        generator = ServiceNowRCAGenerator(
            instance_url='https://test.service-now.com',
            username='test_user',
            password='test_pass'
        )
        
        self.assertIsNotNone(generator.instance_url)
        self.assertEqual(generator.instance_url, 'https://test.service-now.com')
    
    def test_identify_root_cause_from_resolution_notes(self):
        """Test root cause identification from resolution notes"""
        generator = ServiceNowRCAGenerator()
        
        incident = {
            'resolution_notes': 'The root cause was a misconfigured firewall rule',
            'close_notes': '',
            'description': 'Network connectivity issue'
        }
        
        analysis = generator._identify_root_cause(incident, [], [], [])
        
        self.assertIn('Configuration', analysis)
        self.assertIn('misconfigured', analysis.lower())
    
    def test_identify_root_cause_from_description(self):
        """Test root cause identification from description when notes are empty"""
        generator = ServiceNowRCAGenerator()
        
        incident = {
            'resolution_notes': '',
            'close_notes': '',
            'description': 'Hardware failure on router',
            'short_description': 'Router down'
        }
        
        analysis = generator._identify_root_cause(incident, [], [], [])
        
        self.assertIn('Hardware', analysis)
    
    def test_assess_impact_critical(self):
        """Test impact assessment for critical priority"""
        generator = ServiceNowRCAGenerator()
        
        incident = {
            'priority': '1 - Critical',
            'impact': '1 - Critical',
            'urgency': '1 - Critical',
            'cmdb_ci': {'display_value': 'Core Router'},
            'category': 'Network',
            'description': 'Critical network outage affecting 500 users'
        }
        
        incident_data = {'incident': incident}
        impact = generator._assess_impact(incident, incident_data)
        
        self.assertIn('Critical', impact['business_impact'])
        self.assertGreaterEqual(impact['affected_users_estimate'], 500)
    
    def test_analyze_duration(self):
        """Test duration analysis"""
        generator = ServiceNowRCAGenerator()
        
        incident = {
            'opened_at': '2025-01-15 10:00:00',
            'resolved_at': '2025-01-15 14:30:00'
        }
        
        timeline = [
            {
                'timestamp': '2025-01-15 10:00:00',
                'event_type': 'Incident Created',
                'actor': 'User',
                'description': 'Created',
                'details': ''
            },
            {
                'timestamp': '2025-01-15 10:15:00',
                'event_type': 'Assignment',
                'actor': 'Admin',
                'description': 'Assigned',
                'details': ''
            }
        ]
        
        duration = generator._analyze_duration(incident, timeline)
        
        self.assertIsNotNone(duration.get('time_to_resolution'))
        self.assertIn('hours', duration['time_to_resolution'])
    
    def test_justify_priority(self):
        """Test priority justification"""
        generator = ServiceNowRCAGenerator()
        
        incident = {
            'priority': '1 - Critical',
            'impact': '1 - Critical',
            'urgency': '1 - Critical'
        }
        
        justification = generator._justify_priority(incident)
        
        self.assertIn('Critical', justification)
        self.assertIn('justified', justification.lower())


class TestRCAReportFormatter(unittest.TestCase):
    """Test cases for RCA Report Formatter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.formatter = RCAReportFormatter()
        
        self.sample_incident_data = {
            'incident': {
                'number': 'INC0012345',
                'short_description': 'Test Incident',
                'priority': '2 - High',
                'impact': '2 - High',
                'urgency': '1 - Critical',
                'state': '6 - Resolved',
                'category': 'Network',
                'assignment_group': {'display_value': 'Network Team'},
                'opened_at': '2025-01-15 10:00:00',
                'resolved_at': '2025-01-15 14:30:00'
            },
            'timeline': [],
            'related_incidents': [],
            'related_problems': [],
            'related_changes': []
        }
        
        self.sample_analysis = {
            'root_cause': 'Configuration error in firewall rules',
            'contributing_factors': ['Multiple reassignments occurred'],
            'impact_assessment': {
                'business_impact': 'High business impact',
                'technical_impact': 'Firewall configuration issue',
                'user_impact': 'Estimated 200 users affected',
                'affected_users_estimate': 200
            },
            'duration_analysis': {
                'time_to_resolution': '4.5 hours',
                'total_downtime': '4.5 hours',
                'resolution_efficiency': 'Good - Resolved within 24 hours'
            },
            'priority_justification': 'High priority due to significant service impact'
        }
    
    def test_generate_markdown_report(self):
        """Test Markdown report generation"""
        report = self.formatter.generate_report(
            self.sample_incident_data,
            self.sample_analysis,
            format='markdown'
        )
        
        self.assertIn('# Root Cause Analysis Report', report)
        self.assertIn('INC0012345', report)
        self.assertIn('Executive Summary', report)
        self.assertIn('Root Cause Analysis', report)
        self.assertIn('Configuration error', report)
    
    def test_generate_json_report(self):
        """Test JSON report generation"""
        report = self.formatter.generate_report(
            self.sample_incident_data,
            self.sample_analysis,
            format='json'
        )
        
        import json
        report_dict = json.loads(report)
        
        self.assertIn('metadata', report_dict)
        self.assertIn('incident', report_dict)
        self.assertIn('analysis', report_dict)
        self.assertEqual(report_dict['incident']['number'], 'INC0012345')
    
    def test_generate_executive_summary(self):
        """Test executive summary generation"""
        summary = self.formatter._generate_executive_summary(
            self.sample_incident_data['incident'],
            self.sample_analysis
        )
        
        self.assertIn('INC0012345', summary)
        self.assertIn('root cause', summary.lower())
        self.assertGreater(len(summary), 100)  # Should be substantial
    
    def test_generate_recommendations_configuration(self):
        """Test recommendation generation for configuration issues"""
        incident = {'description': 'Configuration error'}
        analysis = {
            'root_cause': 'Configuration error in firewall',
            'duration_analysis': {}
        }
        
        recommendations = self.formatter._generate_recommendations(incident, analysis)
        
        self.assertIn('Configuration', recommendations)
        self.assertIn('Change Control', recommendations)
    
    def test_get_display_value_dict(self):
        """Test display value extraction from dict"""
        value = {'display_value': 'Test Value'}
        result = self.formatter._get_display_value(value)
        self.assertEqual(result, 'Test Value')
    
    def test_get_display_value_string(self):
        """Test display value extraction from string"""
        value = 'Test String'
        result = self.formatter._get_display_value(value)
        self.assertEqual(result, 'Test String')
    
    def test_get_display_value_none(self):
        """Test display value extraction from None"""
        result = self.formatter._get_display_value(None)
        self.assertEqual(result, 'N/A')


if __name__ == '__main__':
    unittest.main()

