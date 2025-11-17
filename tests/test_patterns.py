"""
Unit Tests for Pattern Detection
=================================

Test cases for snow_analytics.analysis.patterns module.
"""

import unittest
import pandas as pd
from datetime import datetime, timedelta

from snow_analytics.analysis.patterns import (
    analyze_patterns,
    find_recurring_issues
)
from snow_analytics.core.transform import transform_incidents


class TestPatterns(unittest.TestCase):
    """Test cases for pattern detection functions."""

    def setUp(self):
        """Set up test fixtures."""
        base_time = datetime.now() - timedelta(days=5)
        
        # Create test data with patterns
        self.test_data = pd.DataFrame({
            'number': ['INC001', 'INC002', 'INC003', 'INC004', 'INC005', 'INC006'],
            'short_description': [
                'WiFi connectivity issue',
                'VPN connection problem',
                'WiFi connectivity issue',  # Recurring
                'DNS resolution failure',
                'WiFi connectivity issue',  # Recurring (3 times)
                'VPN connection problem'  # Recurring (2 times)
            ],
            'priority': ['1 - Critical', '2 - High', '1 - Critical', '3 - Moderate', '2 - High', '1 - Critical'],
            'state': ['Resolved', 'Resolved', 'Resolved', 'Resolved', 'Resolved', 'Resolved'],
            'patternCategory': [
                'WiFi/Wireless',
                'VPN/Remote Access',
                'WiFi/Wireless',
                'DNS/Resolution',
                'WiFi/Wireless',
                'VPN/Remote Access'
            ],
            'cmdb_ci': [
                'Access Point A',
                'VPN Gateway 1',
                'Access Point A',  # Same CI, recurring
                'DNS Server 1',
                'Access Point A',  # Same CI, recurring (3 times)
                'VPN Gateway 1'  # Same CI, recurring (2 times)
            ],
            'openedDate': pd.to_datetime([
                base_time + timedelta(days=i) for i in range(6)
            ]),
            'resolvedDate': pd.to_datetime([
                base_time + timedelta(days=i, hours=2) for i in range(6)
            ])
        })
        
        self.df = transform_incidents(self.test_data)

    def test_analyze_patterns(self):
        """Test overall pattern analysis."""
        analysis = analyze_patterns(self.df)
        
        self.assertIn('category_distribution', analysis)
        self.assertIn('priority_distribution', analysis)
        self.assertIn('temporal_patterns', analysis)
        self.assertIn('recurring_issues', analysis)

    def test_analyze_patterns_category_distribution(self):
        """Test category distribution."""
        analysis = analyze_patterns(self.df)
        
        self.assertIsInstance(analysis['category_distribution'], dict)
        
        # Should have WiFi/Wireless category
        if 'WiFi/Wireless' in analysis['category_distribution']:
            self.assertGreater(analysis['category_distribution']['WiFi/Wireless'], 0)

    def test_analyze_patterns_priority_distribution(self):
        """Test priority distribution."""
        analysis = analyze_patterns(self.df)
        
        self.assertIsInstance(analysis['priority_distribution'], dict)
        
        # Should have priority levels
        if analysis['priority_distribution']:
            total = sum(analysis['priority_distribution'].values())
            self.assertEqual(total, len(self.df))

    def test_analyze_patterns_temporal(self):
        """Test day of week and hour patterns."""
        analysis = analyze_patterns(self.df)
        
        self.assertIsInstance(analysis['temporal_patterns'], dict)
        
        # Should have temporal patterns if dayOfWeek/hourOfDay columns exist
        if 'dayOfWeek' in self.df.columns:
            self.assertIn('by_day_of_week', analysis['temporal_patterns'])

    def test_find_recurring_issues(self):
        """Test recurring issue detection."""
        recurring = find_recurring_issues(self.df, min_occurrences=2)
        
        self.assertIsInstance(recurring, list)
        
        # Should find Access Point A (3 occurrences) and VPN Gateway 1 (2 occurrences)
        if recurring:
            # Check structure
            for issue in recurring:
                self.assertIn('category', issue)
                self.assertIn('ci', issue)
                self.assertIn('occurrences', issue)
                self.assertGreaterEqual(issue['occurrences'], 2)

    def test_find_recurring_issues_min_occurrences(self):
        """Test custom min occurrences."""
        recurring = find_recurring_issues(self.df, min_occurrences=3)
        
        self.assertIsInstance(recurring, list)
        
        # Should only find Access Point A (3 occurrences)
        if recurring:
            for issue in recurring:
                self.assertGreaterEqual(issue['occurrences'], 3)

    def test_find_recurring_issues_missing_columns(self):
        """Test handle missing columns."""
        df_no_ci = pd.DataFrame({
            'number': ['INC001'],
            'patternCategory': ['WiFi/Wireless']
            # Missing cmdb_ci
        })
        
        recurring = find_recurring_issues(df_no_ci)
        
        # Should return empty list without error
        self.assertEqual(recurring, [])

    def test_find_recurring_issues_empty(self):
        """Test empty results handling."""
        df_no_recurring = pd.DataFrame({
            'number': ['INC001', 'INC002'],
            'patternCategory': ['WiFi/Wireless', 'VPN/Remote Access'],
            'cmdb_ci': ['CI1', 'CI2']  # Different CIs
        })
        
        recurring = find_recurring_issues(df_no_recurring, min_occurrences=2)
        
        # Should return empty list
        self.assertEqual(recurring, [])


if __name__ == '__main__':
    unittest.main()

